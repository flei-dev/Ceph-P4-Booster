"""标定版服务端（2026-07-30 修订三）

把「服务时间」与「等待时间」分开：
  - 服务时间代表主机 CPU 上的处理开销，决定容量 ≈ 1/服务时间；
  - 等待时间从实测逐样本分布采样，只加延迟不占容量，
    对应真实 OSD 等待副本落盘不占 CPU 的异步行为。

修订记录：

修订一（256 线程 + 两次 sleep）在虚拟机上出现约 3.5 ms 的固定偏移。
修订二把线程降到 32、设 sys.setswitchinterval(0.0005)，本底降到 1.37 ms，
但每请求仍多出约 2.3 ms——来自每请求两次 time.sleep 的超时累加。
修订三做两件事消除它：

  1. 服务阶段只记账不睡眠。用 free_time 推进，等价于 M/D/1 单服务台：
     start = max(到达时刻, free_time)，free_time = start + 服务时间。
     容量仍是 1/服务时间，但不再消耗一次 sleep。
  2. 每个请求只睡一次，睡「应答时刻 − 当前时刻」，并扣掉启动时实测的
     睡眠偏差（measure_sleep_bias，200 次 4 ms 睡眠取中位数）。

本地实测：baseline p50 17.78–18.28 ms（目标 17.336），
booster p50 3.39–3.48 ms（目标 3.204），均在 ±10% 内。

环境变量：LP_PORT 端口，SVC_B 基线服务时间(s)，SVC_O Booster 服务时间(s)。
--mode floor 为纯回显，用于量测 veth + BMv2 + 解释器的环境本底。
"""
import argparse
import os
import random
import socket
import sys
import threading
import time
from queue import Queue, Full

sys.setswitchinterval(0.0005)

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get('LP_PORT', '9997'))
SVC = {'baseline': float(os.environ.get('SVC_B', '0.002')),
       'booster':  float(os.environ.get('SVC_O', '0.0005')),
       'floor':    0.0}
SAMPLES = {'baseline': 'ceph-latency-us.txt',
           'booster':  'p4-latency-us.txt',
           'floor':    None}
WORKERS = 64


def load(path):
    with open(os.path.join(HERE, path)) as f:
        return [int(l) / 1e6 for l in f if l.strip()]


BIAS_CAP = 0.0005      # 上限 0.5 ms，见下方说明


def measure_sleep_bias(n=400, d=0.002, settle=0.5):
    """实测 time.sleep 的系统性超时。

    修订四（2026-07-31）：改用低分位并加上限。

    原来取中位数，且在进程刚启动时测量。Mininet 与 BMv2 刚起来时机器很忙，
    中位超时会被瞬时负载抬高到毫秒量级；而运行期间的实际超时只有 0.2 ms 左右。
    每个请求都按这个被高估的值提前发出应答，延迟就整体下移。

    2026-07-30 的时序组正是这样被污染的：booster 的 P50 降到 2.693 ms，
    低于采样等待分布本身的最小值 1.873 ms，物理上不可能。已用 FORCE_BIAS=2.5ms
    复现该现象（P50 由 3.537 降至 1.252 ms）。

    三处改动：先静置 settle 秒让机器安定；取第 20 百分位而不是中位数，
    也就是取"最好情况下的超时"，不受瞬时负载污染；再以 BIAS_CAP 封顶。
    残余误差是一个常数，会被各组自测的环境本底吸收掉。
    """
    time.sleep(settle)
    b = []
    for _ in range(n):
        t = time.perf_counter()
        time.sleep(d)
        b.append(time.perf_counter() - t - d)
    b.sort()
    return min(BIAS_CAP, max(0.0, b[int(0.20 * (len(b) - 1))]))


def run(mode):
    service = SVC[mode]
    samples = load(SAMPLES[mode]) if SAMPLES[mode] else None

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 << 20)
    sock.bind(('0.0.0.0', PORT))

    if mode == 'floor':
        print(f">>> mode=floor port={PORT} 纯回显，量测环境本底", flush=True)
        while True:
            try:
                d, a = sock.recvfrom(64)
                sock.sendto(d, a)
            except OSError:
                continue

    bias = measure_sleep_bias()
    srt = sorted(samples)
    print(f">>> mode={mode} port={PORT} service={service*1000:.2f}ms "
          f"cap={1/service:.0f}rps wait_p50={srt[len(srt)//2]*1000:.2f}ms "
          f"wait_min={srt[0]*1000:.3f}ms sleep_bias={bias*1000:.3f}ms"
          f"{'  [已封顶]' if bias >= BIAS_CAP else ''}", flush=True)

    q = Queue(maxsize=20000)
    lock = threading.Lock()
    free = [0.0]

    def worker():
        while True:
            data, addr, arrival = q.get()
            with lock:                                  # 服务阶段：只记账
                start = max(arrival, free[0])
                free[0] = start + service
            target = start + random.choice(samples)     # 总延迟 = 排队 + 采样等待
            dt = target - time.perf_counter() - bias
            if dt > 0:
                time.sleep(dt)                          # 每请求只睡这一次
            try:
                sock.sendto(data, addr)
            except OSError:
                pass

    for _ in range(WORKERS):
        threading.Thread(target=worker, daemon=True).start()

    while True:
        try:
            data, addr = sock.recvfrom(64)
        except OSError:
            continue
        try:
            q.put_nowait((data, addr, time.perf_counter()))
        except Full:
            pass                                        # 队列溢出即丢弃


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('--mode', required=True,
                   choices=['baseline', 'booster', 'floor'])
    run(p.parse_args().mode)
