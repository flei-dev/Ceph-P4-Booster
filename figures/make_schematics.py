#!/usr/bin/env python3
"""统一生成全文的示意图（2026-07-31）

与 make_figures.py 并列：数据图在那边，示意图在这边，共用 figstyle 与 figkit。

    python3 make_schematics.py           # 全部
    python3 make_schematics.py fig2_1    # 单张

已实现：
    fig2_1  Ceph 强一致写路径：主 OSD 同步等待全部副本落盘
    fig3_1  Ceph-P4-Booster 总体架构：热路径与冷路径

待实现（样式确认后按同一模式补齐）：
    fig2_2 PISA 流水线、fig2_3 单点测量、fig2_4 延迟去向、
    fig3_2 状态机（现有独立脚本，将并入）、fig4_1 测试床上的实现
"""
import os
import sys
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figstyle as S
import figkit as K


# ==================================================== 图 2-1 Ceph 强一致写路径
# 图内文字压到最少，机制细节由图注承担（图注文本见 05_文档 各章重写稿）。
T21 = dict(
    en=dict(client='Client', primary='Primary\nOSD', local='BlueStore',
            rep='Replica OSD %d', write='write', repop='REPOP',
            reply='REPOPREPLY', ret='return',
            wait=r'$W=\max(B_0,B_1,B_2)$', slow='slowest',
            eqt='write latency',
            lg=[('data', 'data / replication'), ('ctrl', 'commit ack / return')]),
    cn=dict(client='客户端', primary='主 OSD', local='BlueStore',
            rep='副本 OSD %d', write='写请求', repop='REPOP',
            reply='REPOPREPLY', ret='返回',
            wait=r'$W=\max(B_0,B_1,B_2)$', slow='最慢',
            eqt='写延迟分解',
            lg=[('data', '数据 / 复制请求'), ('ctrl', '落盘确认 / 返回')]),
)


def fig2_1(lang):
    t = T21[lang]
    S.use(lang)
    fig, ax = K.canvas(w=S.W2, h=4.0, xlim=(0, 100), ylim=(4, 96))

    K.host(ax, 1, 61, 15, 15, t['client'], kind='client')
    K.host(ax, 29, 61, 18, 15, t['primary'], kind='compute')
    K.disk(ax, 31.5, 46, 13, 11, t['local'], fs=S.FS['note'],
           fill=S.F_L1)
    K.arrow(ax, (38, 61), (38, 57.4), 'data', lw=1.4)
    ry = [81, 66, 51]
    for i, y in enumerate(ry):
        K.disk(ax, 74, y, 19, 12, t['rep'] % (i + 1), fs=S.FS['note'])
        K.arrow(ax, (47, 70), (74, y + 7), 'data', rad=0.03)
        K.arrow(ax, (74, y + 3), (47, 66), 'ctrl', rad=0.03)
    K.note(ax, 60, 90, t['repop'], color=S.BLUE, ha='center')
    K.note(ax, 60, 45, t['reply'], color=S.ORANGE, ha='center')
    K.arrow(ax, (16, 72), (29, 72), 'data')
    K.note(ax, 22.5, 76.5, t['write'], color=S.BLUE, ha='center')
    K.arrow(ax, (29, 64), (16, 64), 'ctrl')
    K.note(ax, 22.5, 59, t['ret'], color=S.ORANGE, ha='center')

    x0, unit = 38, 4.2
    lens = [2.8, 4.0, 8.2]
    for i, (L, y) in enumerate(zip(lens, [31, 23, 15])):
        K.bar(ax, x0, y, L * unit, 5.8, S.F_L3 if i < 2 else S.RED)
        K.note(ax, x0 - 1.8, y + 2.9, f'$B_{i}$', ha='right',
               color=S.SLATE, fs=S.FS['base'])
    K.note(ax, x0 + lens[2] * unit + 2, 17.9, t['slow'], color=S.RED)
    K.brace(ax, x0, x0 + lens[2] * unit, 13.5, t['wait'], up=False, color=S.RED)
    K.eqbox(ax, 0.5, 44, [
        r'$L = 2t_c + T_p + W + \varepsilon$',
        r'$F_W(t) = \prod_j\, F_{B_j}(t)$',
        r'$P(W>t) \approx n\,P(S>t)$',
    ], title=t['eqt'], fs=9.6, lh=8.0)

    K.legend(ax, t['lg'], loc='upper center', ncol=2, y=0.02)
    S.save(fig, 'fig2-1_ceph_write_path', lang)


# ============================================= 图 3-1 Ceph-P4-Booster 总体架构
T31 = dict(
    en=dict(client='Client', gate='Gate', gsub='real TCP endpoint',
            a='A', b='B', c='C',
            asub='staging pool\nnode 1', bsub='replica record\nnode 2',
            csub='replica record\nnode 3',
            sw='P4 switch', stages=['parse', 'source\ncheck', 'tag', 'bitmap', 'deparse'],
            ptitle='match-action pipeline', pool='size = 3', cloud='unmodified Ceph',
            w='write', ack='early ack', ev='completion events', bg='write-back',
            bnd='Ceph-P4-Booster', ready='ready', eqt='in-switch aggregation',
            lg=[('data', 'data'), ('ctrl', 'completion event / ack'),
                ('fill:store', 'persisted at ack time')]),
    cn=dict(client='客户端', gate='Gate', gsub='真实 TCP 端点',
            a='A', b='B', c='C',
            asub='暂存池\nnode 1', bsub='临时副本\nnode 2', csub='临时副本\nnode 3',
            sw='P4 交换机', stages=['解析', '来源\n校验', '标签', '位图', '组包'],
            ptitle='匹配-动作流水线', pool='size = 3', cloud='未改造的 Ceph',
            w='写请求', ack='提前确认', ev='完成事件', bg='后台回写',
            bnd='Ceph-P4-Booster', ready='ready', eqt='网内聚合判定',
            lg=[('data', '数据'), ('ctrl', '完成事件 / 确认'),
                ('fill:store', '确认时已持久')]),
)


def fig3_1(lang):
    t = T31[lang]
    S.use(lang)
    fig, ax = K.canvas(w=S.W2, h=4.6, xlim=(0, 100), ylim=(2, 98))

    K.boundary(ax, 17, 12, 57, 82, t['bnd'])

    K.host(ax, 0.5, 58, 14, 16, t['client'], kind='client')
    K.host(ax, 21, 56, 19, 20, t['gate'], sub=t['gsub'], kind='compute')

    sy = [78, 62, 46]
    for y, a, b in zip(sy, [t['a'], t['b'], t['c']], [t['asub'], t['bsub'], t['csub']]):
        K.disk(ax, 49, y, 20, 14, a, sub=b)
        K.note(ax, 70.5, y + 6.5, t['ready'], color=S.MUTE, fs=8.2)

    # 交换机：通用画法 + 内部 PISA 流水线，位图那一级高亮
    K.switch(ax, 27, 17, 19, 11, t['sw'])
    K.pipeline(ax, 49, 17, 25, 8, t['stages'], t['ptitle'], fs=7.6, hi=3)

    K.cloud(ax, 76, 40, 24, 36, '')
    K.disk(ax, 79, 51, 18, 11, t['pool'], fs=S.FS['note'],
           fill=S.F_L1, n=3, gap=2.0)
    K.note(ax, 88, 35, t['cloud'], color=S.MUTE, ha='center')

    K.arrow(ax, (14.5, 69), (21, 69), 'data')
    K.note(ax, 17.8, 78.5, t['w'], color=S.BLUE, ha='center')
    K.step(ax, 17.8, 69, 1)
    K.arrow(ax, (21, 61), (14.5, 61), 'ctrl')
    K.note(ax, 17.8, 52.5, t['ack'], color=S.ORANGE, ha='center')
    K.step(ax, 17.8, 61, 4, color=S.ORANGE)

    for y in sy:
        K.arrow(ax, (40, 66), (49, y + 6.5), 'data', rad=0.05)
        K.arrow(ax, (49, y + 2.5), (44.5, 26), 'ctrl', rad=-0.10)
    K.step(ax, 44.5, 72.5, 2)
    K.note(ax, 30, 44, t['ev'], color=S.ORANGE, ha='center')
    K.step(ax, 47, 31, 3, color=S.ORANGE)
    K.arrow(ax, (33, 28), (33, 56), 'ctrl')

    K.arrow(ax, (69, 84), (80, 64), 'data', rad=0.14)
    K.note(ax, 81, 82, t['bg'], color=S.BLUE, ha='center')
    K.step(ax, 74.5, 77.5, 5)

    

    K.eqbox(ax, 0.5, 40, [
        r'$\mathrm{tag}[s] \leftarrow \tau$',
        r'$\mathrm{bmp}[s]\ \cup\!=\ \{\mathrm{src}\}$',
        r'$|\mathrm{bmp}[s]| = 3$',
        r'$\Rightarrow \mathrm{ack} \Leftarrow A \wedge B \wedge C$',
    ], title=t['eqt'], fs=8.4, lh=5.8)

    K.legend(ax, t['lg'], loc='upper center', ncol=3, y=0.005)
    S.save(fig, 'fig3-1_overall_architecture', lang)


# ==================================================== 图 2-2 PISA 匹配-动作流水线
T22 = dict(
    en=dict(ing='Ingress', egr='Egress', parser='parser', deparser='deparser',
            tm='traffic\nmanager', stages=['stage 1', 'stage 2', '…', 'stage N'],
            zoom='inside one stage', key='match key', tbl='match table\n(TCAM / SRAM)',
            act='action ALU', reg='stateful\nregister',
            inp='packet in', outp='packet out',
            n1='fixed per-stage latency, line rate',
            n2='table entries and register memory are limited',
            lg=[('data', 'packet path')]),
    cn=dict(ing='Ingress', egr='Egress', parser='解析器', deparser='逆解析器',
            tm='流量\n管理', stages=['第 1 级', '第 2 级', '…', '第 N 级'],
            zoom='单级内部', key='匹配键', tbl='匹配表\n（TCAM / SRAM）',
            act='动作单元', reg='有状态\n寄存器',
            inp='报文入', outp='报文出',
            n1='每级时延固定，线速处理',
            n2='表项与寄存器容量有限',
            lg=[('data', '报文路径')]),
)


def fig2_2(lang):
    t = T22[lang]
    S.use(lang)
    fig, ax = K.canvas(w=S.W2, h=4.4, xlim=(0, 100), ylim=(-2, 98))

    # 上排：Ingress → TM → Egress
    K.boundary(ax, 4, 62, 42, 28, '')
    K.boundary(ax, 58, 62, 38, 28, '')
    K.note(ax, 6, 64.5, t['ing'], color=S.MUTE, fs=9.0, ha='left')
    K.note(ax, 60, 64.5, t['egr'], color=S.MUTE, fs=9.0, ha='left')
    K.box(ax, 7, 68, 8, 14, t['parser'], 'client', fs=8.0)
    K.pipeline(ax, 17, 69, 27, 12, t['stages'], '', fs=8.2, hi=1)
    K.box(ax, 48, 68, 8, 14, t['tm'], 'neutral', fs=8.0)
    K.pipeline(ax, 61, 69, 22, 12, t['stages'][:3], '', fs=8.2)
    K.box(ax, 86, 68, 8, 14, t['deparser'], 'client', fs=8.0)

    K.arrow(ax, (0.5, 75), (7, 75), 'data')
    K.note(ax, 1.0, 85, t['inp'], color=S.BLUE, ha='left', fs=8.4)
    K.arrow(ax, (15, 75), (17, 75), 'data')
    K.arrow(ax, (44, 75), (48, 75), 'data')
    K.arrow(ax, (56, 75), (61, 75), 'data')
    K.arrow(ax, (83, 75), (86, 75), 'data')
    K.arrow(ax, (94, 75), (99.5, 75), 'data')
    K.note(ax, 99, 85, t['outp'], color=S.BLUE, ha='right', fs=8.4)

    # 下排：把第 2 级放大，展示匹配-动作的内部构成
    K.arrow(ax, (24, 69), (24, 55.2), 'thin', lw=1.2)
    K.note(ax, 27, 61, t['zoom'], color=S.MUTE, fs=8.6)
    K.boundary(ax, 18, 16, 64, 38, '')
    K.box(ax, 23, 36, 16, 11, t['key'], 'client', fs=8.6)
    K.box(ax, 44, 33, 18, 16, t['tbl'], 'compute', fs=8.6)
    K.box(ax, 67, 36, 12, 11, t['act'], 'client', fs=8.6)
    K.box(ax, 44, 20, 18, 10, t['reg'], 'store', fs=8.6)
    K.arrow(ax, (39, 41), (44, 41), 'data')
    K.arrow(ax, (62, 41), (67, 41), 'data')
    K.arrow(ax, (53, 33), (53, 30), 'ctrl', lw=1.6)
    K.arrow(ax, (56, 30), (56, 33), 'ctrl', lw=1.6)

    K.note(ax, 18, 9, '· ' + t['n1'], color=S.SLATE, fs=8.8, ha='left')
    K.note(ax, 18, 3, '· ' + t['n2'], color=S.MUTE, fs=8.8, ha='left')

    S.save(fig, 'fig2-2_pisa_pipeline', lang)


# ======================================== 图 2-3 副本提交延迟的单点测量
T23 = dict(
    en=dict(n1='node 1', n1s='primary OSD', n2='node 2', n2s='replica OSD',
            cap='single capture point\n(node 1 cluster NIC)',
            t1='$t_1$  REPOP sent', t2='$t_2$  REPOPREPLY received',
            dt=r'$\Delta t=t_2-t_1$', commit='commit to device',
            note='both timestamps come from the same kernel clock on node 1,\n'
                 'so no cross-node clock synchronization is needed',
            n=r'$N=33199$ paired samples',
            eqt='pairing rule',
            key1=r'key $=(\mathrm{5tuple}^{-1},\ \mathrm{tid})$',
            key2=r'$\Delta t = t_2 - t_1$  measured on one clock',
            lg=[('data', 'REPOP'), ('ctrl', 'REPOPREPLY')]),
    cn=dict(n1='node 1', n1s='主 OSD', n2='node 2', n2s='副本 OSD',
            cap='单点采集\n（node 1 的 cluster 网卡）',
            t1='$t_1$ 发出 REPOP', t2='$t_2$ 收到 REPOPREPLY',
            dt=r'$\Delta t=t_2-t_1$', commit='落盘提交',
            note='两个时间戳都来自 node 1 的同一内核时钟，\n因此无需跨节点对时',
            n=r'有效配对 $N=33\,199$',
            eqt='配对规则',
            key1=r'联合键 $=($反向五元组$,\ \mathrm{tid})$',
            key2=r'$\Delta t = t_2 - t_1$，同一时钟测得',
            lg=[('data', 'REPOP'), ('ctrl', 'REPOPREPLY')]),
)


def fig2_3(lang):
    t = T23[lang]
    S.use(lang)
    fig, ax = K.canvas(w=S.W2, h=4.3, xlim=(0, 100), ylim=(-14, 94))

    K.lifeline(ax, 18, 96, 68, t['n1'], t['n1s'])
    K.lifeline(ax, 18, 96, 34, t['n2'], t['n2s'])

    x1, x2 = 30, 78
    K.arrow(ax, (x1, 66), (x1 + 16, 36), 'data')
    K.arrow(ax, (x2 - 16, 36), (x2, 66), 'ctrl')
    K.tick(ax, x1, 68, t['t1'])
    K.tick(ax, x2, 68, t['t2'])
    K.bar(ax, x1 + 16, 30, 32, 4.4, S.F_L3)
    K.note(ax, x1 + 32, 32.2, t['commit'], color=S.SLATE, ha='center', fs=8.4)

    K.brace(ax, x1, x2, 61, t['dt'], up=False, color=S.RED)
    K.bar(ax, x1, 78.5, x2 - x1, 3.0, S.F_ACC)

    # 采集点
    K.step(ax, 18, 68, 0, color=S.RED, ms=0)
    ax.plot([18], [68], marker='D', ms=8, mfc=S.RED, mec='white', mew=1.2, zorder=9)
    K.note(ax, 18, 86, t['cap'], color=S.RED, ha='center', fs=8.4)
    K.arrow(ax, (18, 82), (18, 69.6), 'thin', lw=1.2)

    K.eqbox(ax, 3, 18, [t['key1'], t['key2']], title=t['eqt'], fs=9.0)
    K.note(ax, 97, 4, t['note'], color=S.SLATE, ha='right', fs=8.8)
    K.note(ax, 97, -8, t['n'], color=S.MUTE, ha='right', fs=8.8)

    K.legend(ax, t['lg'], loc='lower right', ncol=2, y=-0.02)
    S.save(fig, 'fig2-3_single_point_measurement', lang)


# ============================================== 图 2-4 延迟去向
T24 = dict(
    en=dict(cli='client-visible 4 KiB write', wait='replica commit wait',
            other='everything else', dp='programmable data plane',
            v1='24.5 ms', v2='16.5 ms  (67%)', v3='8.0 ms', v4='87 µs',
            ratio=r'$1/281$ of the client-visible latency',
            eq1=r'$16.5\,/\,24.5 \approx 67\%$',
            eq2=r'$24.5\ \mathrm{ms}\,/\,87\ \mathrm{\mu s} \approx 281$',
            lg=[]),
    cn=dict(cli='客户端可见的 4 KiB 写延迟', wait='副本确认等待',
            other='其余各段', dp='经可编程数据面的一次往返',
            v1='24.5 ms', v2='16.5 ms（67%）', v3='8.0 ms', v4='87 µs',
            ratio=r'约为客户端可见写延迟的 $1/281$',
            eq1=r'$16.5\,/\,24.5 \approx 67\%$',
            eq2=r'$24.5\ \mathrm{ms}\,/\,87\ \mathrm{\mu s} \approx 281$',
            lg=[]),
)


def fig2_4(lang):
    t = T24[lang]
    S.use(lang)
    fig, ax = K.canvas(w=S.W2, h=3.2, xlim=(0, 100), ylim=(2, 94))

    K.note(ax, 2, 84, t['cli'], color=S.SLATE, fs=S.FS['base'])
    K.note(ax, 96, 84, t['v1'], color=S.SLATE, ha='right', fs=S.FS['base'])
    K.stackbar(ax, 2, 60, 94, 16,
               [(0.673, S.RED, t['wait']), (0.327, S.F_L3, t['other'])])
    K.note(ax, 2 + 94 * 0.673 / 2, 53, t['v2'], color=S.RED, ha='center')
    K.note(ax, 2 + 94 * (0.673 + 0.327 / 2), 53, t['v3'], color=S.MUTE, ha='center')

    K.note(ax, 2, 36, t['dp'], color=S.SLATE, fs=S.FS['base'])
    w4 = 94 * (0.087 / 24.5)
    K.bar(ax, 2, 20, max(w4, 0.6), 12, S.BLUE)
    K.arrow(ax, (2 + max(w4, 0.6), 26), (11, 26), 'thin', lw=1.2)
    K.note(ax, 12, 26, t['v4'], color=S.BLUE, fs=S.FS['base'])
    K.note(ax, 24, 26, t['ratio'], color=S.MUTE)
    K.eqbox(ax, 60, 44, [t['eq1'], t['eq2']], fs=9.4, face=S.F_L1)

    S.save(fig, 'fig2-4_where_latency_goes', lang)


# ============================================== 图 3-2 临时副本的状态机
T32 = dict(
    en=dict(s0='payload persisted\n(no state)', s1='ready', s2='backend_safe',
            s3='removed',
            e1='persist state\nmarker (atomic)',
            e2='write to size = 3 pool,\nread back and verify',
            e3='verify once more,\nthen delete',
            n0='ignored by the background worker', n1='deletion refused',
            g='state advances in one direction only; every transition is idempotent',
            eqt='transition guards',
            g1=r'$\mathrm{ready} \Leftarrow \mathrm{payload} \wedge \mathrm{marker\ persisted}$',
            g2=r'$\mathrm{backend\_safe} \Leftarrow \mathrm{read\ back} = \mathrm{payload}$',
            g3=r'$\mathrm{delete} \Leftarrow \mathrm{backend\_safe} \wedge\ $re-verified'),
    cn=dict(s0='载荷已落盘\n（无状态）', s1='ready', s2='backend_safe',
            s3='已删除',
            e1='原子写入\n状态标记',
            e2='写入 size = 3 池，\n读回并校验',
            e3='再次校验后\n删除',
            n0='后台忽略，不会被提升', n1='拒绝删除',
            g='状态只能单向前进；每一步转换都是幂等的',
            eqt='转换的前置条件',
            g1=r'$\mathrm{ready} \Leftarrow$ 载荷已落盘 $\wedge$ 状态标记已持久',
            g2=r'$\mathrm{backend\_safe} \Leftarrow$ 读回内容 $=$ 载荷',
            g3=r'删除 $\Leftarrow \mathrm{backend\_safe} \wedge$ 再次校验通过'),
)


def fig3_2(lang):
    t = T32[lang]
    S.use(lang)
    fig, ax = K.canvas(w=S.W2, h=3.8, xlim=(0, 100), ylim=(-14, 100))

    X, W, H, Y = [1, 27, 53, 80], 19, 22, 52
    kinds = ['neutral', 'compute', 'store', 'client']
    for x, txt, kd in zip(X, [t['s0'], t['s1'], t['s2'], t['s3']], kinds):
        mono = txt in ('ready', 'backend_safe')
        K.box(ax, x, Y, W, H, txt, kd, mono=mono,
              fs=S.FS['base'] if mono else 9.4)
    for i, e in enumerate([t['e1'], t['e2'], t['e3']]):
        x0, x1 = X[i] + W, X[i + 1]
        K.arrow(ax, (x0 + 0.5, Y + H / 2), (x1 - 0.5, Y + H / 2), 'ctrl')
        K.note(ax, (x0 + x1) / 2, Y + H + 7.5, e, color=S.ORANGE,
               ha='center', fs=8.4)
    for i, n in enumerate([t['n0'], t['n1']]):
        cx = X[i] + W / 2 if i else X[i] + W / 2 + 4
        ax.plot([cx, cx], [Y - 1.5, Y - 8], color=S.EDGE, lw=0.9, ls=':', zorder=2)
        K.note(ax, cx, Y - 12, n, color=S.MUTE, ha='center', fs=8.4)
    K.eqbox(ax, 1, 33, [t['g1'], t['g2'], t['g3']], fs=9.2, title=t['eqt'])
    K.note(ax, 50, -9, t['g'], color=S.SLATE, ha='center', fs=8.8)

    S.save(fig, 'fig3-2_replica_state_machine', lang)


# ==================================== 图 4-1 Ceph-P4-Booster 在测试床上的实现
T41 = dict(
    en=dict(cli='client write', gate='Gate', gsub='real TCP endpoint',
            gst=['recv', 'verify', 'fan-out', 'await\nverdict'],
            n1='node 1', n2='node 2', n3='node 3',
            a='A', asub='staging pool\n(single replica)',
            b='B', bsub='NVMe / XFS', c='C', csub='NVMe / XFS',
            sw='Tofino  ·  BF-SDE 9.2.0',
            r1='tag register  ·  16384 slots',
            r2='bitmap register  ·  3 bits per slot',
            stages=['parse', 'source\ncheck', 'tag', 'bitmap', 'deparse'],
            ptitle='match-action pipeline',
            evt='EtherType 0x88B5  ·  24 B header',
            rule='bitmap full  ⇒  rewrite result to COMPLETE, forward to Gate',
            bg='background worker', bgsub='write back, verify, release',
            cloud='unmodified Ceph', pool='size = 3',
            fb='timeout  ⇒  Gate aggregates locally',
            lg=[('data', 'payload'), ('ctrl', 'completion event / verdict')]),
    cn=dict(cli='客户端写请求', gate='Gate', gsub='真实 TCP 端点',
            gst=['接收', '校验', '分派', '等待\n判定'],
            n1='node 1', n2='node 2', n3='node 3',
            a='A', asub='暂存池\n（单副本）',
            b='B', bsub='NVMe / XFS', c='C', csub='NVMe / XFS',
            sw='Tofino  ·  BF-SDE 9.2.0',
            r1='标签寄存器  ·  16 384 槽位',
            r2='位图寄存器  ·  3 位 / 槽位',
            stages=['解析', '来源\n校验', '标签', '位图', '组包'],
            ptitle='匹配-动作流水线',
            evt='以太类型 0x88B5  ·  24 字节头',
            rule='位图集齐  ⇒  结果改写为 COMPLETE，转发给 Gate',
            bg='后台进程', bgsub='回写、校验、回收',
            cloud='未改造的 Ceph', pool='size = 3',
            fb='超时  ⇒  Gate 自行归约',
            lg=[('data', '数据'), ('ctrl', '完成事件 / 判定')]),
)


def fig4_1(lang):
    """实现的组成：三个节点上的部件、交换机内部、以及独立于写路径的后台进程。"""
    t = T41[lang]
    S.use(lang)
    fig, ax = K.canvas(w=S.W2, h=5.2, xlim=(-15, 100), ylim=(2, 102))

    # ---- 三个节点 ----
    K.boundary(ax, 1, 52, 24, 47, t['n1'])
    K.boundary(ax, 27, 52, 21, 47, t['n2'])
    K.boundary(ax, 50, 52, 21, 47, t['n3'])

    K.host(ax, 3, 81, 20, 13, t['gate'], sub=t['gsub'], kind='compute')
    K.pipeline(ax, 2, 71, 22, 8, t['gst'], '', fs=7.2)
    K.disk(ax, 3, 55, 19, 11, t['a'], sub=t['asub'], fs=S.FS['base'])
    K.disk(ax, 29, 65, 16, 11, t['b'], sub=t['bsub'], fs=S.FS['base'])
    K.disk(ax, 52, 65, 16, 11, t['c'], sub=t['csub'], fs=S.FS['base'])

    # ---- 未改造的集群与后台进程 ----
    K.cloud(ax, 73, 48, 26, 28, '')
    K.disk(ax, 78, 58, 16, 10, t['pool'], fs=S.FS['note'], fill=S.F_L1, n=3, gap=1.8)
    K.note(ax, 86, 50, t['cloud'], color=S.MUTE, ha='center', fs=8.6)
    K.box(ax, 70, 30, 29, 9, t['bg'], 'client', sub=t['bgsub'], fs=9.4, sub_fs=8.0)

    # ---- 交换机及其内部 ----
    K.switch(ax, 34, 27, 30, 13, t['sw'], fs=9.4)
    K.pipeline(ax, 34, 14, 30, 8, t['stages'], t['ptitle'], fs=7.2, hi=3)
    K.box(ax, -14, 31, 30, 8, t['r1'], 'store', fs=8.4)
    K.box(ax, -14, 20, 30, 8, t['r2'], 'store', fs=8.4)
    K.note(ax, -14.5, 50, t['rule'], color=S.SLATE, fs=8.4)
    K.note(ax, -14.5, 7.5, t['evt'], color=S.MUTE, fs=8.4)

    # ---- 载荷：客户端 → Gate → 三处 ----
    K.arrow(ax, (-15, 88), (3, 88), 'data')
    K.note(ax, -14.5, 92, t['cli'], color=S.BLUE, fs=8.4)
    K.arrow(ax, (12, 81), (12, 79.5), 'data')
    K.arrow(ax, (12, 71), (12, 66.5), 'data')
    K.arrow(ax, (23, 87), (29, 77), 'data', rad=-0.10)
    K.arrow(ax, (23, 84), (52, 77), 'data', rad=-0.16)

    # ---- 完成事件：三处 → 交换机；判定 → Gate ----
    K.arrow(ax, (12, 55), (39, 40.5), 'ctrl', rad=0.12)
    K.arrow(ax, (37, 65), (46, 40.5), 'ctrl')
    K.arrow(ax, (60, 65), (56, 40.5), 'ctrl', rad=-0.08)
    K.arrow(ax, (36, 40), (22, 70.5), 'ctrl', rad=-0.20)
    K.note(ax, -14.5, 44, t['fb'], color=S.ORANGE, fs=8.2)

    # ---- 冷路径：三处 → 后台 → 标准池 ----
    K.arrow(ax, (68, 70), (73, 39.5), 'thin', lw=1.3, rad=0.14)
    K.arrow(ax, (86, 39), (86, 56.8), 'data')

    K.legend(ax, t['lg'], loc='lower right', ncol=2, y=-0.02)
    S.save(fig, 'fig4-1_implementation', lang)


ALL = {'fig2_1': fig2_1, 'fig2_2': fig2_2, 'fig2_3': fig2_3, 'fig2_4': fig2_4,
       'fig3_1': fig3_1, 'fig3_2': fig3_2, 'fig4_1': fig4_1}


# ================================ 图 3-3 一次写的时序与确认时刻的保证
T33 = dict(
    en=dict(cli='client', gate='Gate', gsub='real endpoint',
            a='staging A', asub='node 1', b='staging B', bsub='node 2',
            c='staging C', csub='node 3', sw='P4 switch', swsub='in-network verdict',
            bg='background', bgsub='separate process',
            e1='write', e2='fan-out', e3='persist', e4='completion event',
            e5='COMPLETE', e6='early ack', e7='write to size = 3 pool',
            e8='verify, then release',
            ackt='acknowledgment issued here',
            win='staging window',
            gt='guarantees that already hold at this instant',
            g1='payload persisted on 3 NVMe devices across 3 distinct nodes',
            g2='node-level redundancy = 3, same as a standard three-replica write',
            g3='any single node may fail — the other two still hold the payload',
            g4='the switch holds no unique state; losing it costs the verdict, not the data',
            lg=[('data', 'payload'), ('ctrl', 'completion event / ack')]),
    cn=dict(cli='客户端', gate='Gate', gsub='真实端点',
            a='暂存 A', asub='node 1', b='暂存 B', bsub='node 2',
            c='暂存 C', csub='node 3', sw='P4 交换机', swsub='网内判定',
            bg='后台进程', bgsub='独立于写路径',
            e1='写请求', e2='并发分发', e3='本地持久化', e4='完成事件',
            e5='判定完成', e6='提前确认', e7='写入 size = 3 池',
            e8='校验后回收',
            ackt='确认在此刻发出',
            win='暂存窗口',
            gt='此刻已经成立的保证',
            g1='载荷已在 3 个不同节点的 3 块 NVMe 上完成持久化',
            g2='节点级冗余度 = 3，与标准三副本写相同',
            g3='任一节点失效，其余两处仍持有完整载荷',
            g4='交换机不持有唯一状态，失去它损失的是判定、不是数据',
            lg=[('data', '数据'), ('ctrl', '完成事件 / 确认')]),
)


def fig3_3(lang):
    t = T33[lang]
    S.use(lang)
    fig, ax = K.canvas(w=S.W2, h=5.6, xlim=(0, 100), ylim=(-52, 100))

    X0, X1 = 18, 97
    lanes = [(92, t['cli'], None), (80, t['gate'], t['gsub']),
             (70, t['a'], t['asub']), (58, t['b'], t['bsub']),
             (46, t['c'], t['csub']), (32, t['sw'], t['swsub']),
             (18, t['bg'], t['bgsub'])]
    for y, lab, sub in lanes:
        K.lifeline(ax, X0, X1, y, lab, sub)

    ACK = 74                                    # 确认发出的时刻

    # 客户端 → Gate
    K.arrow(ax, (21, 92), (21, 81), 'data')
    K.note(ax, 22.5, 87, t['e1'], color=S.BLUE, fs=8.4)

    # Gate 并发分发到三处
    for y in (70, 58, 46):
        K.arrow(ax, (25, 79), (30, y + 1.2), 'data', rad=-0.06)
    K.note(ax, 23.5, 68, t['e2'], color=S.BLUE, ha='right', fs=8.4)

    # 三处各自落盘：色条长短不同，C 最慢
    ends = {70: 44, 58: 50, 46: 58}
    for y, xe in ends.items():
        K.bar(ax, 30, y - 1.6, xe - 30, 3.2, S.F_L4 if y != 46 else S.F_ACC)
    K.note(ax, 31, 73.5, t['e3'], color=S.MUTE, fs=8.2)

    # 完成事件汇入交换机
    for y, xe in ends.items():
        K.arrow(ax, (xe, y - 1.8), (xe + 5, 33), 'ctrl', rad=0.08)
    K.note(ax, 45, 39, t['e4'], color=S.ORANGE, fs=8.4)

    # 交换机判定 → Gate → 客户端
    K.arrow(ax, (63, 33), (ACK - 4, 79), 'ctrl', rad=-0.10)
    K.note(ax, 64.5, 50, t['e5'], color=S.ORANGE, fs=8.4)
    K.arrow(ax, (ACK, 81), (ACK, 91), 'ctrl')
    K.note(ax, ACK + 1.5, 86, t['e6'], color=S.ORANGE, fs=8.4)

    # 后台：写入标准池并校验
    K.arrow(ax, (76, 79), (79, 19), 'data', rad=0.10)
    K.bar(ax, 79, 16.4, 12, 3.2, S.F_L2)
    K.note(ax, 79, 12, t['e7'], color=S.MUTE, fs=8.2)
    K.bar(ax, 92, 16.4, 4, 3.2, S.F_L3)
    K.note(ax, 96, 22.5, t['e8'], color=S.MUTE, fs=8.2, ha='right')

    # 确认时刻：一条竖线贯穿全图
    ax.plot([ACK, ACK], [-6, 96], color=S.RED, lw=1.4, ls=(0, (5, 3)), zorder=7)
    K.note(ax, ACK, 98, t['ackt'], color=S.RED, ha='center', fs=8.8)
    K.brace(ax, ACK, 96, 6, t['win'], up=False, color=S.MUTE, fs=8.4)

    # 此刻已经成立的保证
    K.eqbox(ax, 1, -8, ['✓  ' + t['g1'], '✓  ' + t['g2'],
                         '✓  ' + t['g3'], '✓  ' + t['g4']],
            title=t['gt'], fs=8.6, face=S.F_L1, lh=6.6)

    K.legend(ax, t['lg'], loc='lower right', ncol=2, y=-0.015)
    S.save(fig, 'fig3-3_ack_moment_guarantees', lang)


ALL['fig3_3'] = fig3_3

if __name__ == '__main__':
    want = sys.argv[1:] or list(ALL)
    for name in want:
        print(name)
        for lang in ('en', 'cn'):
            ALL[name](lang)
    print(f'\n输出在 {S.OUT}')
