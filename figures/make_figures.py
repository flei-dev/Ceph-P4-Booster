#!/usr/bin/env python3
"""统一生成全文的全部数据图（2026-07-31）

一个脚本、一套样式、一个数据目录。数据全部在 ./data/，输出全部在 ./out/，
每张图同时给出 PDF（矢量，投稿用）与 PNG（预览用），中英两版。

    python3 make_figures.py            # 全部
    python3 make_figures.py fig5_1     # 单张

图号对应 v3 定稿：

    fig5_1  真机 4 KiB 写确认延迟 CDF（Ceph-P4-Booster vs Ceph size=3）
    fig5_2  仿真：中位延迟随负载的变化
    fig5_3  仿真：两个负载下的延迟分布
    fig5_4  仿真：阶梯负载下的中位延迟
    fig5_5  仿真：达成吞吐随并发客户端数的变化

示意图（图 2-1、2-2、2-3、2-4、3-1、3-2、4-1）不在本脚本内，见 ../README.md。
"""
import csv
import os
import sys
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figstyle as S

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def col(path, name, cast=float):
    with open(os.path.join(D, path)) as f:
        return [cast(r[name]) for r in csv.DictReader(f)]


def rows(path):
    with open(os.path.join(D, path)) as f:
        return list(csv.DictReader(f))


def vec(path, scale=1.0):
    with open(os.path.join(D, path)) as f:
        return np.array([float(x) * scale for x in f if x.strip()])


def scalar(path):
    return float(open(os.path.join(D, path)).read().strip())


# ============================================================ 图 5-1 真机 CDF
T51 = dict(
    en=dict(xl='Client-visible 4 KiB write acknowledgment latency (ms, log scale)',
            yl='Cumulative probability',
            l1='Ceph-P4-Booster', l2='Ceph size = 3 synchronous write'),
    cn=dict(xl='客户端可见的 4 KiB 写确认延迟（ms，对数横轴）',
            yl='累积概率',
            l1='Ceph-P4-Booster', l2='Ceph size = 3 同步写'),
)


def fig5_1(lang):
    t = T51[lang]
    S.use(lang)
    p4 = np.sort(vec('hw_p4_latency_us.txt', 1e-3))
    ce = np.sort(vec('hw_ceph_latency_us.txt', 1e-3))
    y = np.arange(1, len(p4) + 1) / len(p4)
    fig, ax = plt.subplots(figsize=(S.W2, 4.3))
    ax.step(ce, y, where='post', color=S.BLUE, lw=2.0, label=t['l2'])
    ax.step(p4, y, where='post', color=S.RED, lw=2.0, label=t['l1'])
    for a, c in ((p4, S.RED), (ce, S.BLUE)):
        for p, ls in ((0.5, ':'), (0.99, '--')):
            v = S.q(a, p)
            ax.plot([v, v], [0, p], ls=ls, color=c, lw=1.0, alpha=.75)
    for a, c, dy in ((p4, S.RED, -46), (ce, S.BLUE, -46)):
        ax.annotate(f'P50 {S.q(a, .5):.2f} ms', (S.q(a, .5), 0.5),
                    xytext=(6 if c == S.BLUE else -6, dy), textcoords='offset points',
                    ha='left' if c == S.BLUE else 'right',
                    fontsize=S.FS['ann'], color=c)
        ax.annotate(f'P99 {S.q(a, .99):.2f} ms', (S.q(a, .99), 0.99),
                    xytext=(6, -3 if c == S.RED else -16), textcoords='offset points',
                    fontsize=S.FS['ann'], color=c)
    ax.set_xscale('log')
    ax.set_xlim(1.5, 130)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel(t['xl'])
    ax.set_ylabel(t['yl'])
    ax.set_xticks([2, 3, 5, 10, 20, 50, 100])
    ax.set_xticklabels(['2', '3', '5', '10', '20', '50', '100'])
    S.frame(ax, legend_loc='lower right')
    S.save(fig, 'fig5-1_hw_latency_cdf', lang, 'data')


# ==================================================== 图 5-2 仿真 负载-中位延迟
T52 = dict(
    en=dict(xl='Achieved load (requests/s)', yl='Median latency (ms, log scale)',
            b='Baseline', o='Ceph-P4-Booster',
            cap='modeled capacity 500 req/s', fl='emulation floor %.2f ms'),
    cn=dict(xl='达成负载（请求/秒）', yl='中位延迟（ms，对数纵轴）',
            b='基线', o='Ceph-P4-Booster',
            cap='模型容量 500 请求/秒', fl='仿真环境本底 %.2f ms'),
)


def fig5_2(lang):
    t = T52[lang]
    S.use(lang)
    r = rows('sim_load_sweep.csv')
    fl = scalar('floor_sweep_ms.txt')
    fig, ax = plt.subplots(figsize=(S.W2, 4.4))
    for mode, c, mk, lab in (('baseline', S.BLUE, 's', t['b']),
                             ('booster', S.RED, 'o', t['o'])):
        d = [x for x in r if x['mode'] == mode]
        ax.plot([float(x['achieved_rps']) for x in d], [float(x['p50']) for x in d],
                mk + '-', color=c, lw=2.0, ms=5, label=lab)
    ax.axvspan(500, 640, color=S.BAND, zorder=0)
    ax.axvline(500, color=S.SAND, lw=1.0, ls='--')
    ax.annotate(t['cap'], xy=(500, 3.0), xytext=(494, 2.7),
                fontsize=S.FS['ann'], color='#8A7A5E', ha='right')
    ax.set_yscale('log')
    ax.set_xlim(0, 640)
    ax.set_ylim(1, 3000)
    ax.set_xlabel(t['xl'])
    ax.set_ylabel(t['yl'])
    ax.set_yticks([1, 2, 5, 10, 20, 50, 100, 300, 1000, 3000])
    ax.set_yticklabels(['1', '2', '5', '10', '20', '50', '100', '300', '1000', '3000'])
    S.floor_line(ax, fl, t['fl'] % fl, x=14)
    S.frame(ax)
    S.save(fig, 'fig5-2_sim_load_sweep', lang, 'data')


# ============================================================ 图 5-3 仿真 CDF
T53 = dict(
    en=dict(xl='Response latency (ms, log scale)', yl='Cumulative probability',
            lab={('baseline', 100): 'Baseline, 100 req/s',
                 ('baseline', 450): 'Baseline, 450 req/s  (90% utilization)',
                 ('booster', 100): 'Ceph-P4-Booster, 100 req/s',
                 ('booster', 450): 'Ceph-P4-Booster, 450 req/s  (22% utilization)'},
            fl='emulation floor %.2f ms'),
    cn=dict(xl='响应延迟（ms，对数横轴）', yl='累积概率',
            lab={('baseline', 100): '基线，100 请求/秒',
                 ('baseline', 450): '基线，450 请求/秒（利用率 90%）',
                 ('booster', 100): 'Ceph-P4-Booster，100 请求/秒',
                 ('booster', 450): 'Ceph-P4-Booster，450 请求/秒（利用率 22%）'},
            fl='仿真环境本底 %.2f ms'),
)
STY53 = {('baseline', 100): (S.BLUE, '-', 2.0), ('baseline', 450): (S.BLUE, '--', 1.7),
         ('booster', 100): (S.RED, '-', 2.0), ('booster', 450): (S.RED, '--', 1.7)}


def fig5_3(lang):
    t = T53[lang]
    S.use(lang)
    fl = scalar('floor_cdf_ms.txt')
    fig, ax = plt.subplots(figsize=(S.W2, 4.5))
    for key in (('baseline', 100), ('baseline', 450), ('booster', 100), ('booster', 450)):
        v = np.sort(vec(f'sim_cdf_{key[0]}_{key[1]}rps_ms.txt'))
        y = np.arange(1, len(v) + 1) / len(v)
        c, ls, lw = STY53[key]
        ax.step(v, y, where='post', color=c, ls=ls, lw=lw, label=t['lab'][key])
    ax.set_xscale('log')
    ax.set_xlim(2, 150)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel(t['xl'])
    ax.set_ylabel(t['yl'])
    ax.set_xticks([2, 3, 5, 10, 20, 30, 50, 100])
    ax.set_xticklabels(['2', '3', '5', '10', '20', '30', '50', '100'])
    ax.axvline(fl, color='#B9C2C9', lw=1.0, ls=':')
    ax.text(fl * 1.06, 0.03, t['fl'] % fl, fontsize=S.FS['note'], color=S.MUTE)
    S.frame(ax, legend_loc='lower right')
    S.save(fig, 'fig5-3_sim_cdf', lang, 'data')


# ============================================================= 图 5-4 仿真 时序
T54 = dict(
    en=dict(xl='Time (s)', yl='Median latency (ms, log scale)',
            b='Baseline', o='Ceph-P4-Booster',
            rate='offered\nreq/s', fl='emulation floor %.2f ms'),
    cn=dict(xl='时间（秒）', yl='中位延迟（ms，对数纵轴）',
            b='基线', o='Ceph-P4-Booster',
            rate='提供负载\n请求/秒', fl='仿真环境本底 %.2f ms'),
)
PHASES = [(0, 20, 150), (20, 40, 300), (40, 60, 450),
          (60, 80, 550), (80, 100, 300), (100, 120, 150)]


def fig5_4(lang):
    t = T54[lang]
    S.use(lang)
    fl = scalar('floor_timeline_ms.txt')
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for a, b, rt in PHASES:
        if rt > 500:
            ax.axvspan(a, b, color=S.BAND, zorder=0)
        ax.text((a + b) / 2, 4600, f'{rt}', ha='center', va='center',
                fontsize=S.FS['note'], color='#8A7A5E')
    ax.text(-5.4, 4600, t['rate'], ha='left', va='center',
            fontsize=S.FS['note'], color='#8A7A5E')
    for mode, c, lab in (('baseline', S.BLUE, t['b']), ('booster', S.RED, t['o'])):
        bins = {}
        for x in rows(f'sim_timeline_{mode}.csv'):
            bins.setdefault(int(float(x['t_s'])), []).append(float(x['latency_ms']))
        xs = sorted(bins)
        ax.plot(xs, [S.q(bins[k], .5) for k in xs], '-', color=c, lw=1.7, label=lab)
    ax.set_yscale('log')
    ax.set_xlim(-6, 121)
    ax.set_ylim(1.5, 11000)
    ax.set_xlabel(t['xl'])
    ax.set_ylabel(t['yl'])
    ax.set_xticks(range(0, 121, 20))
    ax.set_yticks([2, 5, 10, 20, 50, 100, 300, 1000, 3000])
    ax.set_yticklabels(['2', '5', '10', '20', '50', '100', '300', '1000', '3000'])
    S.floor_line(ax, fl, t['fl'] % fl, x=1)
    S.frame(ax, legend_loc='center left')
    S.save(fig, 'fig5-4_sim_timeline', lang, 'data')


# =========================================================== 图 5-5 仿真 扩展性
T55 = dict(
    en=dict(xl='Concurrent clients', yl='Achieved throughput (ops/s)',
            b='Baseline', o='Ceph-P4-Booster', cap='  modeled\n  capacity %d'),
    cn=dict(xl='并发客户端数', yl='达成吞吐（ops/s）',
            b='基线', o='Ceph-P4-Booster', cap='  模型容量 %d'),
)


def fig5_5(lang):
    t = T55[lang]
    S.use(lang)
    r = rows('sim_scalability.csv')
    fig, ax = plt.subplots(figsize=(S.W2, 4.4))
    for mode, c, mk, cap, lab in (('baseline', S.BLUE, 's', 500, t['b']),
                                  ('booster', S.RED, 'o', 2000, t['o'])):
        d = [x for x in r if x['mode'] == mode]
        ax.plot([int(x['clients']) for x in d], [float(x['iops']) for x in d],
                mk + '-', color=c, lw=2.0, ms=5, label=lab)
        ax.axhline(cap, color=c, lw=1.0, ls='--', alpha=.55)
        ax.text(16.4, cap, t['cap'] % cap, fontsize=S.FS['note'],
                color=c, va='center', ha='left')
    ax.set_xlim(0, 20.5)
    ax.set_ylim(0, 2350)
    ax.set_xlabel(t['xl'])
    ax.set_ylabel(t['yl'])
    ax.set_xticks([1, 2, 3, 4, 6, 8, 10, 12, 16])
    S.frame(ax)
    S.save(fig, 'fig5-5_sim_scalability', lang, 'data')


ALL = {'fig5_1': fig5_1, 'fig5_2': fig5_2, 'fig5_3': fig5_3,
       'fig5_4': fig5_4, 'fig5_5': fig5_5}

if __name__ == '__main__':
    want = sys.argv[1:] or list(ALL)
    for name in want:
        print(name)
        for lang in ('en', 'cn'):
            ALL[name](lang)
    print(f'\n全部输出在 {S.OUT}')
