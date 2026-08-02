#!/usr/bin/env python3
"""补充三组实验的客户端（2026-07-30）

与已跑通的 `h1_client.py` 同源，只增加三种输出形态。服务端仍用标定版
`h2_server.py`，未作任何改动。

  closed    N 个闭环线程，各自发一个、等一个，报告总达成吞吐（扩展性用）
  dump      开环定速，导出全部逐样本延迟（CDF 用）
  timeline  开环阶梯变速，导出 (相对时刻, 延迟, 当前负载)（时序用）

闭环用于扩展性是正确的：每个并发客户端本来就是一个闭环，横轴是客户端数、
纵轴是达成吞吐，两者都不是设定值。开环用于 CDF 与时序，避免响应延迟反过来
压低发送速率——这正是原 `h1_client.py` 的问题所在。
"""
import argparse
import os
import random
import socket
import statistics
import threading
import time

PORT = int(os.environ.get('LP_PORT', '9997'))


def _sock(timeout=0.5, rcvbuf=8 << 20):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, rcvbuf)
    s.settimeout(timeout)
    return s


# --------------------------------------------------------------- closed loop
def run_closed(target, nclients, dur, warmup=3.0):
    """N 个闭环线程。每线程独占 socket，收发严格配对，无需序号匹配。"""
    dst = (target, PORT)
    lat, done = [], []
    lock = threading.Lock()
    t_meas = time.time() + warmup
    t_end = t_meas + dur

    def one(tid):
        s = _sock(timeout=2.0)
        mine, n, seq = [], 0, 0
        while time.time() < t_end:
            seq += 1
            payload = f"{tid:03d}{seq:09d}".encode()
            t0 = time.perf_counter()
            try:
                s.sendto(payload, dst)
                s.recvfrom(64)
            except (socket.timeout, OSError):
                continue
            t1 = time.perf_counter()
            if time.time() >= t_meas:            # 预热期不计
                mine.append((t1 - t0) * 1000.0)
                n += 1
        s.close()
        with lock:
            lat.extend(mine)
            done.append(n)

    ts = [threading.Thread(target=one, args=(i,)) for i in range(nclients)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()

    total = sum(done)
    if not lat:
        print(f"RESULT:{nclients},0.00,nan,nan,nan,0")
        return
    s_ = sorted(lat)
    print(f"RESULT:{nclients},{total / dur:.2f},{statistics.mean(s_):.3f},"
          f"{s_[len(s_) // 2]:.3f},{s_[int(0.99 * (len(s_) - 1))]:.3f},{total}")


# ----------------------------------------------------------------- open loop
def _open_loop(target, phases, warmup, on_sample, drain=3.0, arrival='poisson'):
    """phases: [(rate, seconds), ...]；on_sample(t_rel, lat_ms, rate) 逐样本回调。

    预热期发出的报文不登记到 sent，其回包因此被忽略，不进入统计。

    t_rel 用**发出时刻**而非回包时刻计，这样每个样本落在它实际所属的负载段里；
    否则基线在超容量段的高延迟样本会被记到下一段去。
    """
    s = _sock()
    dst = (target, PORT)
    sent, stop = {}, threading.Event()
    t_ref = [0.0]

    def receiver():
        while not stop.is_set():
            try:
                data, _ = s.recvfrom(64)
            except (socket.timeout, OSError):
                continue
            rec = sent.pop(int(data), None)
            if rec is None:
                continue
            t0, rate = rec
            on_sample(t0 - t_ref[0], (time.perf_counter() - t0) * 1000.0, rate)

    rt = threading.Thread(target=receiver, daemon=True)
    rt.start()

    seq = 0

    def _next_gap(rate):
        # poisson：指数间隔，对应泊松到达，与第二章 M/G/1 的假设一致
        # fixed  ：等间隔，到达完全不随机
        return random.expovariate(rate) if arrival == 'poisson' else 1.0 / rate

    # 预热段：按第一段速率发，不登记
    t_phase, tt = time.time(), time.time()
    while time.time() - t_phase < warmup:
        tt += _next_gap(phases[0][0])
        now = time.time()
        if tt > now:
            time.sleep(tt - now)
        seq += 1
        try:
            s.sendto(str(seq).encode(), dst)
        except OSError:
            pass

    # 测量段
    t_ref[0] = time.perf_counter()
    offered = 0
    for rate, secs in phases:
        t_phase, tt = time.time(), time.time()
        while time.time() - t_phase < secs:
            tt += _next_gap(rate)
            now = time.time()
            if tt > now:
                time.sleep(tt - now)
            seq += 1
            sent[seq] = (time.perf_counter(), rate)
            offered += 1
            try:
                s.sendto(str(seq).encode(), dst)
            except OSError:
                pass

    # 排空：基线在超容量段的积压可达约 2 s，留足时间收尾包
    time.sleep(drain)
    stop.set()
    rt.join(timeout=1.5)
    s.close()
    return offered


def run_dump(target, rate, dur, out, warmup=3.0, arrival='poisson'):
    lat = []
    offered = _open_loop(target, [(rate, dur)], warmup,
                         lambda t, v, r: lat.append(v), arrival=arrival)
    with open(out, 'w') as f:
        for v in lat:
            f.write(f"{v:.4f}\n")
    if not lat:
        print(f"RESULT:{rate:.0f},nan,nan,nan,0,{offered}")
        return
    s_ = sorted(lat)
    print(f"RESULT:{rate:.0f},{statistics.mean(s_):.3f},{s_[len(s_) // 2]:.3f},"
          f"{s_[int(0.99 * (len(s_) - 1))]:.3f},{len(s_)},{offered}")


def run_timeline(target, phases, out, warmup=3.0, arrival='poisson'):
    rows = []
    offered = _open_loop(target, phases, warmup,
                         lambda t, v, r: rows.append((t, v, r)), arrival=arrival)
    rows.sort(key=lambda x: x[0])
    with open(out, 'w') as f:
        f.write("t_s,latency_ms,offered_rps\n")
        for t, v, r in rows:
            f.write(f"{t:.4f},{v:.4f},{r:.0f}\n")
    if not rows:
        print(f"RESULT:timeline,nan,nan,0,{offered}")
        return
    v = sorted(x[1] for x in rows)
    print(f"RESULT:timeline,{statistics.mean(v):.3f},{v[len(v) // 2]:.3f},"
          f"{len(v)},{offered}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('--mode', required=True, choices=['closed', 'dump', 'timeline'])
    p.add_argument('-t', '--target', default='127.0.0.1')
    p.add_argument('-c', '--clients', type=int, default=1)
    p.add_argument('-r', '--rate', type=float, default=100.0)
    p.add_argument('-d', '--dur', type=float, default=12.0)
    p.add_argument('-o', '--out', default='out.txt')
    p.add_argument('--profile', default='150:20,300:20,450:20,550:20,300:20,150:20',
                   help='阶梯负载，形如 rate:seconds,rate:seconds,...')
    p.add_argument('--arrival', default='poisson', choices=['poisson', 'fixed'],
                   help='到达过程：poisson=指数间隔（默认，与第二章 M/G/1 假设一致）；'
                        'fixed=等间隔')
    a = p.parse_args()

    if a.mode == 'closed':
        run_closed(a.target, a.clients, a.dur)
    elif a.mode == 'dump':
        run_dump(a.target, a.rate, a.dur, a.out, arrival=a.arrival)
    else:
        ph = [(float(x.split(':')[0]), float(x.split(':')[1]))
              for x in a.profile.split(',')]
        run_timeline(a.target, ph, a.out, arrival=a.arrival)
