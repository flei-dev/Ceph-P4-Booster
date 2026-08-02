#!/usr/bin/env python3
"""补充标定实验：扩展性 / CDF / 时序 / 负载扫描重跑（2026-07-30）

拓扑、`booster.p4`、`booster.json`、转发表与已跑通的 `run_calibrated_load.py`
完全一致，未作改动。服务端仍是标定版 `h2_server.py`，参数也不变
（SVC_B=0.002、SVC_O=0.0005）。本脚本只改变客户端的施压方式与输出形态。

用法（在 Fig1-load-11 目录下）：

    sudo python3 run_calibrated_extra.py --check     # 先测客户端自身能力上限
    sudo python3 run_calibrated_extra.py scal        # 第一组：扩展性
    sudo python3 run_calibrated_extra.py cdf         # 第二组：CDF
    sudo python3 run_calibrated_extra.py timeline    # 第三组：时序
    sudo python3 run_calibrated_extra.py sweep       # 第四组：负载扫描重跑
    sudo python3 run_calibrated_extra.py all         # 四组连跑

四组互不依赖，可以分次跑、分次发回。
"""

import argparse
import csv
import os
import sys
import time

sys.path.append('/home/p4/tutorials/utils')
from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import Switch, Host
try:
    from p4_mininet import P4Switch, P4Host
except ImportError:
    P4Switch, P4Host = Switch, Host

SVC_BASELINE = 0.002       # 容量约 500 rps
SVC_BOOSTER = 0.0005       # 容量约 2000 rps
PORT = 9999
MODES = ('baseline', 'booster')

# 到达过程。poisson = 指数间隔，与第二章 M/G/1 的 Pollaczek–Khinchine 分析同假设。
# 上次那版负载扫描用的是等间隔（fixed），排队几乎不发生，拐点前曲线全平、
# 到容量处直接垂直上升——那是完美定速的产物，不是真实系统的形状。
ARRIVAL = 'poisson'

# 第一组：扩展性（闭环，不涉及到达过程）
CLIENTS = [1, 2, 3, 4, 6, 8, 10, 12, 16]
SCAL_DUR = 12.0

# 第二组：CDF。100 rps 时两条路径都远离拐点；450 rps 时基线利用率 0.9、
# Booster 仍只有 0.225——同一负载下的余量差别正是要看的东西。
CDF_RATES = [100, 450]
CDF_DUR = 20.0

# 第三组：时序。550 rps 超过基线模型容量、仍在 Booster 容量之内。
PROFILE = '150:20,300:20,450:20,550:20,300:20,150:20'

# 第四组：负载扫描重跑（改泊松到达）
SWEEP_RATES = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600]
SWEEP_DUR = 10.0

ENV = f"LP_PORT={PORT} SVC_B={SVC_BASELINE} SVC_O={SVC_BOOSTER}"


class SimpleTopo(Topo):
    def build(self):
        s1 = self.addSwitch('s1', sw_path='simple_switch',
                            json_path='booster.json', thrift_port=9090)
        h1 = self.addHost('h1', ip='10.0.0.1/24', mac='00:00:0a:00:00:01')
        h2 = self.addHost('h2', ip='10.0.0.2/24', mac='00:00:0a:00:00:02')
        h3 = self.addHost('h3', ip='10.0.0.3/24', mac='00:00:0a:00:00:03')
        self.addLink(h1, s1, port2=1)
        self.addLink(h2, s1, port2=2)
        self.addLink(h3, s1, port2=3)


def install_rules():
    cmd = ""
    for i in range(1, 4):
        cmd += (f"table_add MyIngress.ipv4_lpm MyIngress.ipv4_forward "
                f"10.0.0.{i}/32 => 00:00:0a:00:00:0{i} {i}\n")
    with open("rules.txt", "w") as f:
        f.write(cmd)
    os.system("simple_switch_CLI --thrift-port 9090 < rules.txt > /dev/null 2>&1")


def start_net(mode):
    os.system("sudo mn -c 2> /dev/null")
    if not os.path.exists("booster.json"):
        os.system("p4c -b bmv2 booster.p4")
    net = Mininet(topo=SimpleTopo(), host=P4Host, switch=P4Switch, controller=None)
    net.start()
    time.sleep(2)
    install_rules()
    for h in net.hosts:
        h.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
        for intf in h.intfList():
            h.cmd(f"ethtool --offload {intf} rx off tx off")
        for other in net.hosts:
            if h != other:
                h.cmd(f'arp -s {other.IP()} {other.MAC()}')
    h1, h2 = net.get('h1', 'h2')
    h2.popen(f"{ENV} python3 h2_server.py --mode {mode}", shell=True)
    time.sleep(2)
    return net, h1


def sample_min_ms(mode):
    """采样等待分布的最小值。任何一次测得的延迟都不可能低于它。"""
    f = {'baseline': 'ceph-latency-us.txt', 'booster': 'p4-latency-us.txt'}[mode]
    return min(int(x) / 1000.0 for x in open(f) if x.strip())


def sanity(mode, observed_min_ms, floor_ms=0.0):
    """健全性检查：实测最小延迟不得低于采样分布最小值。

    2026-07-30 的时序组因服务端睡眠偏差被高估而整体下移，P50 甚至低于分布最小值。
    这一检查能当场发现同类问题，避免把不成立的数据带进论文。
    """
    lo = sample_min_ms(mode)
    ok = observed_min_ms >= lo - 0.05
    print(f"    [健全性] {mode} 实测最小 {observed_min_ms:.3f} ms  "
          f"采样分布最小 {lo:.3f} ms  本底 {floor_ms:.3f} ms  "
          f"{'通过' if ok else '★ 不通过：数据不可用，请把本行发回 ★'}")
    return ok


def measure_floor():
    """量环境本底：纯回显服务端，低负载开环。每组各测一次，不跨组复用。"""
    net, h1 = start_net('floor')
    vals = []
    for r_ in (50, 100):
        out = h1.cmd(f"{ENV} python3 h1_client_ext.py --mode dump "
                     f"--arrival {ARRIVAL} -t 10.0.0.2 -r {r_} -d 6 -o /dev/null")
        r = parse(out, 6)
        if r:
            vals.append(r[2])
    net.stop()
    fl = min(vals) if vals else 0.0
    print(f"    环境本底 p50 = {fl:.2f} ms")
    return fl


def parse(out, n):
    for line in out.split('\n'):
        if line.startswith("RESULT:"):
            p = line[len("RESULT:"):].split(',')

            def f(x):
                try:
                    return float(x)
                except ValueError:
                    return float('nan')
            return [f(x) for x in p[:n]]
    print("  解析失败，原始输出：\n", out)
    return None


# ------------------------------------------------------------------ 自检
def check():
    """对纯回显服务端跑 16 个闭环线程，测客户端自身的吞吐上限。

    这个数必须明显高于 Booster 的模型容量 2000 rps，否则扩展性曲线的高端
    是被客户端压住的，不是被模型容量压住的。
    """
    print(">>> CHECK  纯回显服务端 + 16 闭环线程，测客户端自身能力上限")
    net, h1 = start_net('floor')
    out = h1.cmd(f"{ENV} python3 h1_client_ext.py --mode closed "
                 f"-t 10.0.0.2 -c 16 -d 10")
    r = parse(out, 6)
    net.stop()
    if r is None:
        return
    print(f"    客户端上限 ≈ {r[1]:.0f} ops/s  (p50={r[3]:.3f} ms)")
    if r[1] < 3000:
        print("    不足 3000 ops/s：扩展性高端会被客户端限制，先把这行发回，不要往下跑。")
    else:
        print("    余量充足，可以跑三组实验。")


# ------------------------------------------------------------ 第一组 扩展性
def run_scal():
    print("\n>>> SCAL  先量环境本底")
    floor = measure_floor()
    rows = []
    for mode in MODES:
        cap = 1 / (SVC_BASELINE if mode == 'baseline' else SVC_BOOSTER)
        print(f"\n>>> SCAL {mode.upper()}  modelled capacity ≈ {cap:.0f} rps")
        net, h1 = start_net(mode)
        mins = []
        for n in CLIENTS:
            print(f"    {n:>3} clients ...", end="", flush=True)
            out = h1.cmd(f"{ENV} python3 h1_client_ext.py --mode closed "
                         f"-t 10.0.0.2 -c {n} -d {SCAL_DUR}")
            r = parse(out, 6)
            if r is None:
                continue
            print(f"  iops={r[1]:8.1f}  avg={r[2]:7.3f}  "
                  f"p50={r[3]:7.3f}  p99={r[4]:8.3f} ms  n={int(r[5])}")
            mins.append(r[3])
            rows.append(dict(mode=mode, clients=n, iops=round(r[1], 2),
                             avg_ms=r[2], p50_ms=r[3], p99_ms=r[4],
                             completed=int(r[5]),
                             modelled_capacity_rps=round(cap),
                             floor_ms=round(floor, 3)))
        net.stop()
        if mins:
            sanity(mode, min(mins), floor)
    if not rows:
        print("\n!!! 没有拿到任何结果，请把上面的输出发回。")
        return
    with open("data_scalability_calibrated.csv", 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("\n>>> 已写入 data_scalability_calibrated.csv")


# ----------------------------------------------------------------- 第二组 CDF
def run_cdf():
    print("\n>>> CDF  先量环境本底")
    floor = measure_floor()
    rows = []
    for mode in MODES:
        print(f"\n>>> CDF {mode.upper()}")
        net, h1 = start_net(mode)
        mins = []
        for r_ in CDF_RATES:
            out_name = f"lat_{mode}_{r_}rps.txt"
            print(f"    {r_:>4} rps ...", end="", flush=True)
            out = h1.cmd(f"{ENV} python3 h1_client_ext.py --mode dump "
                         f"--arrival {ARRIVAL} "
                         f"-t 10.0.0.2 -r {r_} -d {CDF_DUR} -o {out_name}")
            r = parse(out, 6)
            if r is None:
                continue
            print(f"  avg={r[1]:7.3f}  p50={r[2]:7.3f}  p99={r[3]:8.3f} ms  "
                  f"recv={int(r[4])}  offered={int(r[5])}  -> {out_name}")
            mins.append(r[2])
            rows.append(dict(mode=mode, rate=r_, avg_ms=r[1], p50_ms=r[2],
                             p99_ms=r[3], recv=int(r[4]), offered=int(r[5]),
                             floor_ms=round(floor, 3), file=out_name))
        net.stop()
        if mins:
            sanity(mode, min(mins), floor)
    if not rows:
        print("\n!!! 没有拿到任何结果，请把上面的输出发回。")
        return
    with open("cdf_summary_calibrated.csv", 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("\n>>> 已写入 cdf_summary_calibrated.csv 与 4 个 lat_*.txt")


# ---------------------------------------------------------------- 第三组 时序
def run_timeline():
    print(f"\n>>> TIMELINE  阶梯负载 {PROFILE}")
    print(">>> 先量环境本底")
    floor = measure_floor()
    for mode in MODES:
        print(f"\n    {mode.upper()} ...", end="", flush=True)
        net, h1 = start_net(mode)
        out_name = f"timeline_{mode}_calibrated.csv"
        out = h1.cmd(f"{ENV} python3 h1_client_ext.py --mode timeline "
                     f"--arrival {ARRIVAL} "
                     f"-t 10.0.0.2 --profile {PROFILE} -o {out_name}")
        r = parse(out, 5)
        # 低负载段的最小延迟，用于健全性检查
        obs = h1.cmd(f"python3 -c \"import csv;v=[float(x['latency_ms']) "
                     f"for x in csv.DictReader(open('{out_name}')) "
                     f"if float(x['t_s'])<20];print(min(v) if v else 0)\"")
        net.stop()
        if r is None:
            continue
        print(f"  avg={r[1]:7.3f}  p50={r[2]:7.3f} ms  "
              f"recv={int(r[3])}  offered={int(r[4])}  -> {out_name}")
        try:
            sanity(mode, float(obs.strip().split('\n')[-1]), floor)
        except ValueError:
            print("    [健全性] 无法解析最小延迟，请手工核对")
    with open("floor_ms_timeline.txt", 'w') as f:
        f.write(f"{floor:.4f}\n")
    print("\n>>> 已写入 timeline_baseline_calibrated.csv、"
          "timeline_booster_calibrated.csv 与 floor_ms_timeline.txt")


# ------------------------------------------------ 第四组 负载扫描重跑（泊松到达）
def run_sweep():
    """与上次的 run_calibrated_load.py 同一组速率点，只把到达过程改成泊松。

    先量环境本底（纯回显），后面各点减掉它。
    """
    print("\n>>> SWEEP  先量环境本底（纯回显）")
    floor = measure_floor()

    rows = []
    for mode in MODES:
        cap = 1 / (SVC_BASELINE if mode == 'baseline' else SVC_BOOSTER)
        print(f"\n>>> SWEEP {mode.upper()}  modelled capacity ≈ {cap:.0f} rps")
        net, h1 = start_net(mode)
        mins = []
        for r_ in SWEEP_RATES:
            print(f"    {r_:>4} rps ...", end="", flush=True)
            out = h1.cmd(f"{ENV} python3 h1_client_ext.py --mode dump "
                         f"--arrival {ARRIVAL} -t 10.0.0.2 -r {r_} "
                         f"-d {SWEEP_DUR} -o /dev/null")
            r = parse(out, 6)
            if r is None:
                continue
            print(f"  offered={int(r[5])}  recv={int(r[4])}  "
                  f"achieved={r[4] / SWEEP_DUR:6.1f} rps  avg={r[1]:8.2f}  "
                  f"p50={r[2]:8.2f}  p99={r[3]:9.2f} ms")
            rows.append(dict(mode=mode, rate=r_, offered=int(r[5]),
                             recv=int(r[4]),
                             achieved_rps=round(r[4] / SWEEP_DUR, 1),
                             avg=r[1], p50=r[2], p99=r[3],
                             avg_minus_floor=round(r[1] - floor, 3),
                             p50_minus_floor=round(r[2] - floor, 3),
                             p99_minus_floor=round(r[3] - floor, 3),
                             modelled_capacity_rps=round(cap)))
            mins.append(r[2])
        net.stop()
        if mins:
            sanity(mode, min(mins), floor)
    if not rows:
        print("\n!!! 没有拿到任何结果，请把上面的输出发回。")
        return
    with open("data_sweep_poisson.csv", 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open("floor_ms_poisson.txt", 'w') as f:
        f.write(f"{floor:.4f}\n")
    print("\n>>> 已写入 data_sweep_poisson.csv 与 floor_ms_poisson.txt")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('group', nargs='?', default='all',
                    choices=['scal', 'cdf', 'timeline', 'sweep', 'all'])
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    for f_ in ('h1_client_ext.py', 'h2_server.py',
               'ceph-latency-us.txt', 'p4-latency-us.txt'):
        if not os.path.exists(f_):
            sys.exit(f"缺少文件：{f_}")

    if args.check:
        check()
        sys.exit(0)

    t0 = time.time()
    if args.group in ('scal', 'all'):
        run_scal()
    if args.group in ('cdf', 'all'):
        run_cdf()
    if args.group in ('timeline', 'all'):
        run_timeline()
    if args.group in ('sweep', 'all'):
        run_sweep()
    print(f"\n完成，用时 {(time.time() - t0) / 60:.1f} 分钟。")
