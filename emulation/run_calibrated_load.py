#!/usr/bin/env python3
"""标定后的负载扫描（2026-07-30 修订二）

与原 run_exp.py 的区别：

1. 不用 write_files() 覆盖 h1_client.py / h2_server.py，直接用本目录下的标定版。
2. 服务端用标定版：服务时间与等待时间分离，等待时间从实测逐样本分布采样。
3. 客户端用开环版：发送不受响应延迟限制，输出里同时给出达成负载。
4. 速率区间 50–600 rps，与模型容量匹配。
5. 不启动 h3_replica：副本等待已折进采样的等待时间。
6. 只输出 CSV，不画图。

拓扑、booster.p4、booster.json、转发表与原 run_exp.py 完全一致，未作改动。

用法（在 Fig1-load-11 目录下）：
    sudo python3 run_calibrated_load.py --check    # 先量本底，再做低负载自检
    sudo python3 run_calibrated_load.py            # 完整扫描
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

SVC_BASELINE = 0.002      # 容量约 500 rps
SVC_BOOSTER = 0.0005      # 容量约 2000 rps
PORT = 9999
RATES = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600]
CHECK_RATES = [50, 100]
DURATION = 10.0
TARGET_P50 = {'baseline': 17.336, 'booster': 3.204}


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


def parse_result(out):
    for line in out.split('\n'):
        if line.startswith("RESULT:"):
            p = line[len("RESULT:"):].split(',')
            def f(x):
                try:
                    return float(x)
                except ValueError:
                    return float('nan')
            return dict(rate=f(p[0]), avg=f(p[1]), p50=f(p[2]),
                        p99=f(p[3]), recv=int(float(p[4])), offered=int(float(p[5])))
    return None


def run_suite(mode, rates, quiet=False):
    svc = {'baseline': SVC_BASELINE, 'booster': SVC_BOOSTER, 'floor': 0.0}[mode]
    if mode == 'floor':
        print(f"\n>>> FLOOR  纯回显，量测 veth + BMv2 + 解释器的环境本底")
    else:
        print(f"\n>>> {mode.upper()}  service={svc*1000:.2f} ms  "
              f"modelled capacity ≈ {1/svc:.0f} rps")
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
    env = f"LP_PORT={PORT} SVC_B={SVC_BASELINE} SVC_O={SVC_BOOSTER}"
    h2.popen(f"{env} python3 h2_server.py --mode {mode}", shell=True)
    time.sleep(2)

    rows = []
    for r in rates:
        print(f"    {r:>4} rps ...", end="", flush=True)
        out = h1.cmd(f"{env} python3 h1_client.py -t 10.0.0.2 -r {r} -d {DURATION}")
        res = parse_result(out)
        if res is None:
            print("  解析失败，原始输出：\n", out)
            continue
        ach = res['recv'] / DURATION
        print(f"  offered={res['offered']}  recv={res['recv']}  "
              f"achieved={ach:6.1f} rps  avg={res['avg']:7.2f}  "
              f"p50={res['p50']:7.2f}  p99={res['p99']:8.2f} ms")
        res['achieved_rps'] = round(ach, 1)
        rows.append(res)

    net.stop()
    return rows


def write_csv(path, rows, floor):
    cols = ['rate', 'offered', 'recv', 'achieved_rps', 'avg', 'p50', 'p99',
            'avg_minus_floor', 'p50_minus_floor', 'p99_minus_floor']
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            r = dict(r)
            for k in ('avg', 'p50', 'p99'):
                r[k + '_minus_floor'] = round(r[k] - floor, 3)
            w.writerow({c: r.get(c) for c in cols})
    print(f">>> 已写入 {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='量本底并做低负载自检')
    args = ap.parse_args()

    for f in ('h1_client.py', 'h2_server.py',
              'ceph-latency-us.txt', 'p4-latency-us.txt'):
        if not os.path.exists(f):
            sys.exit(f"缺少文件：{f}")

    # 先量环境本底：纯回显，不做服务也不等待
    fl = run_suite('floor', [50, 100])
    floor = min(r['p50'] for r in fl) if fl else 0.0
    print(f"\n>>> 环境本底 p50 = {floor:.2f} ms"
          f"（veth + BMv2 往返 + 解释器；此值会叠加在后面所有延迟上）")

    rates = CHECK_RATES if args.check else RATES
    base = run_suite('baseline', rates)
    boost = run_suite('booster', rates)

    print("\n=== 扣除本底后与实测基线的对照 ===")
    print(f"本底 {floor:.2f} ms；判据为扣除本底后落在目标 ±10%")
    ok_all = True
    for tag, rows in (('baseline', base), ('booster', boost)):
        t = TARGET_P50[tag]
        for r in rows:
            adj = r['p50'] - floor
            ok = 0.9 * t <= adj <= 1.1 * t
            ok_all &= ok
            print(f"  {tag:8} {r['rate']:>4} rps  p50={r['p50']:7.2f}  "
                  f"扣本底={adj:7.2f}  目标={t:6.2f}  {'通过' if ok else '不通过'}")

    if args.check:
        print("\n" + ("自检通过，可以跑完整扫描。" if ok_all else
                      "自检未通过，把上面整段发回，先不要跑完整扫描。"))
        sys.exit(0)

    write_csv("data_baseline_calibrated.csv", base, floor)
    write_csv("data_booster_calibrated.csv", boost, floor)
    with open("floor_ms.txt", "w") as f:
        f.write(f"{floor:.4f}\n")
    print("\n完成。把两个 CSV 和 floor_ms.txt 发回即可。")
