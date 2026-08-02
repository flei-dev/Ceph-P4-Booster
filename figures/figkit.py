#!/usr/bin/env python3
"""示意图工具箱（2026-07-31）

在 matplotlib 上封装一层声明式的绘图原语，使每张示意图只需二三十行代码即可写成，
而不必逐个调用 patch。所有原语的配色、字体、线宽都取自 figstyle，因此示意图与数据图
自动保持同一套视觉语言。

为什么用 matplotlib 而不是 draw.io 或 TikZ：
  - 只依赖 matplotlib 一个包，`pip install matplotlib` 之后在任何机器上都能跑；
  - 输出矢量 PDF 且字体可嵌入，满足 IEEE 对插图的要求；
  - 与数据图共用同一个样式模块，配色字号不会走样；
  - 全部内容在代码里，改一个词不必重新排版，中英两版由同一份代码生成。

坐标系约定：每张图用 100 × 100 的画布，左下角为原点，便于心算布局。
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import (FancyBboxPatch, FancyArrowPatch, Polygon,
                                Circle, Ellipse)
from matplotlib.lines import Line2D

import figstyle as S

# 语义化的填充色：同一类实体在全文中始终用同一个颜色
FILL = {
    'client': S.F_BLUE,      # 客户端
    'compute': S.F_GREEN,    # 处理组件（主 OSD、Gate）
    'store': S.F_PURPLE,     # 持久化位置（副本、暂存、后端池）
    'switch': S.F_GREY,      # 交换机
    'neutral': S.F_NEUTRAL,  # 中性底
}


def fit(ax, t, max_w, min_fs=5.6):
    """把文字缩到能装进 max_w（数据坐标）。中英两版字宽不同，这里统一收口。"""
    fig = ax.figure
    fig.canvas.draw()
    inv = ax.transData.inverted()
    for _ in range(24):
        bb = t.get_window_extent()
        p0 = inv.transform((0, 0)); p1 = inv.transform((bb.width, 0))
        if abs(p1[0] - p0[0]) <= max_w or t.get_fontsize() <= min_fs:
            return t
        t.set_fontsize(t.get_fontsize() - 0.3)
        fig.canvas.draw()
    return t


def canvas(w=7.2, h=4.2, xlim=(0, 100), ylim=(0, 100)):
    """建立一张干净的画布。返回 (fig, ax)。"""
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect('auto')
    ax.axis('off')
    ax.set_facecolor('white')
    return fig, ax


def box(ax, x, y, w, h, text='', kind='compute', fs=None, mono=False,
        sub=None, sub_fs=None, z=3, lw=1.1, radius=1.6):
    """圆角方框。(x, y) 为左下角。sub 为框内第二行小字。"""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.0,rounding_size={radius}",
        facecolor=FILL.get(kind, kind), edgecolor=S.EDGE, lw=lw, zorder=z))
    if text:
        ty = y + h / 2 + (h * 0.13 if sub else 0)
        fit(ax, ax.text(x + w / 2, ty, text, ha='center', va='center',
                        zorder=z + 1, fontsize=fs or S.FS['base'],
                        color=S.SLATE, fontweight=S.WEIGHT,
                        family=S.MONO if mono else None, linespacing=1.45),
            w * 0.9)
    if sub:
        fit(ax, ax.text(x + w / 2, y + h / 2 - h * 0.22, sub, ha='center',
                        va='center', zorder=z + 1,
                        fontsize=sub_fs or S.FS['note'], color=S.MUTE,
                        linespacing=1.4), w * 0.92)
    return (x + w / 2, y + h / 2)


def cloud(ax, x, y, w, h, text='', fs=None, z=2):
    """云形：表示未经本文改造的外部集群。"""
    cx, cy = x + w / 2, y + h / 2
    blobs = [(0.26, 0.42, 0.26), (0.50, 0.60, 0.30), (0.74, 0.44, 0.25),
             (0.38, 0.34, 0.22), (0.62, 0.33, 0.22)]
    for fx, fy, fr in blobs:
        ax.add_patch(Circle((x + fx * w, y + fy * h), fr * min(w, h * 1.6),
                            facecolor=FILL['neutral'], edgecolor=S.EDGE,
                            lw=1.0, zorder=z))
    if text:
        ax.text(cx, cy - h * 0.02, text, ha='center', va='center', zorder=z + 2,
                fontsize=fs or S.FS['note'], color=S.MUTE, linespacing=1.4)


def boundary(ax, x, y, w, h, label='', fs=None, z=1):
    """虚线框：本文系统的边界。"""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.0,rounding_size=2.0",
        facecolor='none', edgecolor='#AEB8BF', lw=1.1, ls=(0, (5, 4)), zorder=z))
    if label:
        ax.text(x + 1.6, y + h - 2.2, label, ha='left', va='top',
                fontsize=fs or S.FS['note'], fontweight=S.WEIGHT,
                color=S.MUTE, zorder=z + 1)


def arrow(ax, p0, p1, kind='data', label='', lfs=None, loff=(0, 2.2),
          rad=0.0, z=4, lw=None, ha='center'):
    """箭头。kind='data' 为实线蓝（数据流），'ctrl' 为橙色虚线（控制流与确认），
    'thin' 为浅灰细线（辅助引线）。"""
    style = {
        'data': dict(color=S.BLUE, ls='-', lw=lw or 2.2),
        'ctrl': dict(color=S.ORANGE, ls=(0, (4.5, 2.8)), lw=lw or 2.0),
        'thin': dict(color=S.EDGE, ls=':', lw=lw or 0.9),
    }[kind]
    ax.add_patch(FancyArrowPatch(
        p0, p1, arrowstyle='-|>', mutation_scale=15,
        connectionstyle=f'arc3,rad={rad}', shrinkA=1.5, shrinkB=1.5,
        zorder=z, **style))
    if label:
        mx, my = (p0[0] + p1[0]) / 2 + loff[0], (p0[1] + p1[1]) / 2 + loff[1]
        ax.text(mx, my, label, ha=ha, va='center', zorder=z + 1,
                fontsize=lfs or S.FS['note'], fontweight=S.WEIGHT,
                color=style['color'], linespacing=1.35)


def bar(ax, x, y, w, h, color, alpha=1.0, z=3, edge=None):
    """实心条：用于时间轴一类的量化表达。"""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.0,rounding_size=0.5",
        facecolor=color, edgecolor=edge or 'none', lw=0.8, alpha=alpha, zorder=z))


def brace(ax, x0, x1, y, text='', up=False, fs=None, color=None, z=5, depth=1.6):
    """水平大括号，用于标注一段区间。"""
    c = color or S.SLATE
    s = 1 if up else -1
    xs = np.linspace(x0, x1, 100)
    mid = (x0 + x1) / 2
    ys = y + s * depth * (1 - np.abs((xs - mid) / ((x1 - x0) / 2)) ** 3)
    ax.plot(xs, ys, color=c, lw=1.0, zorder=z)
    ax.plot([mid, mid], [y + s * depth, y + s * depth * 1.9], color=c, lw=1.0, zorder=z)
    if text:
        ax.text(mid, y + s * depth * 2.3, text, ha='center',
                va='bottom' if up else 'top', fontsize=fs or S.FS['base'],
                fontweight=S.WEIGHT, color=c, zorder=z, linespacing=1.35)


def note(ax, x, y, text, fs=None, ha='left', va='center', color=None, z=6,
         bold=True):
    ax.text(x, y, text, ha=ha, va=va, zorder=z, fontsize=fs or S.FS['note'],
            fontweight=S.WEIGHT if bold else 'normal',
            color=color or S.MUTE, linespacing=1.45)


def legend(ax, items, loc='lower center', ncol=3, y=None):
    """图例。items 为 [(kind, label), ...]，kind 见 arrow 或 'fill:<key>'。"""
    handles, labels = [], []
    for kind, lab in items:
        if kind.startswith('fill:'):
            handles.append(plt.Rectangle((0, 0), 1, 1,
                                         facecolor=FILL[kind[5:]], edgecolor=S.EDGE, lw=1.0))
        elif kind == 'data':
            handles.append(Line2D([0], [0], color=S.BLUE, lw=1.9))
        elif kind == 'ctrl':
            handles.append(Line2D([0], [0], color=S.ORANGE, lw=1.7, ls=(0, (5, 3))))
        labels.append(lab)
    lg = ax.legend(handles, labels, loc=loc, ncol=ncol, frameon=False,
                   fontsize=S.FS['legend'], handlelength=1.9, columnspacing=1.8,
                   bbox_to_anchor=(0.5, y) if y is not None else None)
    for t in lg.get_texts():
        t.set_color(S.SLATE)
    return lg


# =============================================================== 图标原语
def disk(ax, x, y, w, h, text='', sub=None, fill=None, fs=None, z=3, n=1,
         gap=1.6):
    """圆柱体：表示磁盘、存储池、持久化位置。比方框形象得多。
    n>1 时叠放 n 个圆柱，用来表示"多副本"。"""
    fc = fill or FILL['store']
    eh = h * 0.22                                   # 顶/底椭圆的高度
    for k in range(n - 1, -1, -1):
        yy = y + k * gap
        body = FancyBboxPatch((x, yy + eh / 2), w, h - eh,
                              boxstyle="square,pad=0.0",
                              facecolor=fc, edgecolor='none', zorder=z)
        ax.add_patch(body)
        ax.add_patch(Ellipse((x + w / 2, yy + eh / 2), w, eh,
                             facecolor=fc, edgecolor=S.EDGE, lw=1.3, zorder=z))
        ax.add_patch(Ellipse((x + w / 2, yy + h - eh / 2), w, eh,
                             facecolor=fc, edgecolor=S.EDGE, lw=1.3, zorder=z + 1))
        ax.plot([x, x], [yy + eh / 2, yy + h - eh / 2], color=S.EDGE, lw=1.3, zorder=z + 1)
        ax.plot([x + w, x + w], [yy + eh / 2, yy + h - eh / 2],
                color=S.EDGE, lw=1.3, zorder=z + 1)
    cy = y + (n - 1) * gap + h / 2
    nl = (sub.count('\n') + 1) if sub else 1      # 小字有几行，主标题就让开几分
    if text:
        fit(ax, ax.text(x + w / 2, cy + (h * (0.14 + 0.07 * (nl - 1)) if sub else 0), text,
                        ha='center', va='center', zorder=z + 3,
                        fontsize=fs or S.FS['base'], fontweight=S.WEIGHT,
                        color=S.SLATE, linespacing=1.4), w * 0.86)
    if sub:
        fit(ax, ax.text(x + w / 2, cy - h * (0.16 + 0.06 * (nl - 1)), sub, ha='center',
                        va='center', zorder=z + 3, fontsize=S.FS['note'],
                        color=S.SLATE, alpha=.78, linespacing=1.35), w * 0.9)


def switch(ax, x, y, w, h, text='', sub=None, fs=None, z=3, depth=None):
    """交换机：网络拓扑图的通用画法——扁平立方体 + 顶面交叉双向箭头。
    这是 Cisco 以来网络图中交换机的约定表示，读者一眼可辨。"""
    d = depth if depth is not None else h * 0.42
    top = [(x, y + h), (x + d, y + h + d), (x + w + d, y + h + d), (x + w, y + h)]
    side = [(x + w, y), (x + w + d, y + d), (x + w + d, y + h + d), (x + w, y + h)]
    ax.add_patch(Polygon(side, closed=True, facecolor=S.F_L3,
                         edgecolor=S.EDGE, lw=1.3, zorder=z))
    ax.add_patch(Polygon(top, closed=True, facecolor=S.F_L1,
                         edgecolor=S.EDGE, lw=1.3, zorder=z + 1))
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.0,rounding_size=0.8",
                                facecolor=FILL['switch'], edgecolor=S.EDGE,
                                lw=1.4, zorder=z + 2))
    # 顶面两组交叉双向箭头：交换机的通用标识
    cx, cy = x + w / 2 + d / 2, y + h + d / 2
    ox, oy = w * 0.13, d * 0.20
    for sx in (-1, 1):
        ax.add_patch(FancyArrowPatch(
            (cx - sx * ox, cy - oy), (cx + sx * ox, cy + oy),
            arrowstyle='<|-|>', mutation_scale=8, color=S.BLUE_D,
            lw=1.3, zorder=z + 3))
    if text:
        fit(ax, ax.text(x + w / 2, y + h * (0.62 if sub else 0.5), text,
                        ha='center', va='center', zorder=z + 4,
                        fontsize=fs or S.FS['base'], fontweight=S.WEIGHT,
                        color=S.SLATE), w * 0.88)
    if sub:
        ax.text(x + w / 2, y + h * 0.28, sub, ha='center', va='center',
                zorder=z + 4, fontsize=S.FS['note'], color=S.MUTE)



def pipeline(ax, x, y, w, h, stages, title='', fs=None, z=3, hi=None):
    """PISA 匹配-动作流水线：一串首尾相接的级，级间用小箭头相连。
    stages 为各级名称；hi 为需要高亮的级下标。"""
    n = len(stages)
    gap = w * 0.035
    sw = (w - gap * (n - 1)) / n
    for i, name in enumerate(stages):
        xx = x + i * (sw + gap)
        acc = (hi is not None and i == hi)
        ax.add_patch(FancyBboxPatch(
            (xx, y), sw, h, boxstyle="round,pad=0.0,rounding_size=0.6",
            facecolor=S.F_ACC if acc else S.F_L2,
            edgecolor=S.RED if acc else S.EDGE,
            lw=1.6 if acc else 1.2, zorder=z))
        fit(ax, ax.text(xx + sw / 2, y + h / 2, name, ha='center', va='center',
                        zorder=z + 1, fontsize=fs or S.FS['note'],
                        fontweight=S.WEIGHT, color=S.SLATE, linespacing=1.3),
            sw * 0.88)
        if i < n - 1:
            ax.add_patch(FancyArrowPatch(
                (xx + sw, y + h / 2), (xx + sw + gap, y + h / 2),
                arrowstyle='-|>', mutation_scale=9, color=S.EDGE, lw=1.1,
                zorder=z + 1))
    if title:
        ax.text(x + w, y - 3.2, title, ha='right', va='top', zorder=z + 1,
                fontsize=8.4, fontweight=S.WEIGHT, color=S.MUTE)


def step(ax, x, y, n, color=None, ms=15, z=8):
    """步骤编号：带圈数字，把图与正文的叙述顺序对上。
    用点标记而非 Circle——坐标轴非等比时 Circle 会被拉成椭圆。"""
    c = color or S.BLUE_D
    ax.plot([x], [y], 'o', ms=ms, mfc='white', mec=c, mew=1.6, zorder=z)
    ax.text(x, y, str(n), ha='center', va='center', zorder=z + 1,
            fontsize=8.6, fontweight=S.WEIGHT, color=c)


def chip(ax, x, y, w, h, text='', sub=None, fs=None, z=3, pins=5):
    """芯片：表示可编程交换机 ASIC。两侧带引脚，一眼可辨。"""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.0,rounding_size=1.2",
        facecolor=FILL['switch'], edgecolor=S.EDGE, lw=1.4, zorder=z))
    for k in range(pins):
        py = y + h * (k + 1) / (pins + 1)
        ax.plot([x - w * 0.06, x], [py, py], color=S.EDGE, lw=1.5, zorder=z - 1)
        ax.plot([x + w, x + w * 1.06], [py, py], color=S.EDGE, lw=1.5, zorder=z - 1)
    ax.add_patch(Circle((x + w * 0.11, y + h * 0.82), min(w, h) * 0.055,
                        facecolor='white', edgecolor=S.EDGE, lw=1.0, zorder=z + 1))
    if text:
        ax.text(x + w / 2, y + h / 2 + (h * 0.13 if sub else 0), text,
                ha='center', va='center', zorder=z + 3,
                fontsize=fs or S.FS['base'], fontweight=S.WEIGHT, color=S.SLATE)
    if sub:
        ax.text(x + w / 2, y + h / 2 - h * 0.2, sub, ha='center', va='center',
                zorder=z + 3, fontsize=S.FS['note'], color=S.MUTE)


def host(ax, x, y, w, h, text='', sub=None, fs=None, z=3, kind='client'):
    """主机/节点：方框加两条机架横线，与纯方框区分。"""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.0,rounding_size=1.4",
        facecolor=FILL[kind], edgecolor=S.EDGE, lw=1.4, zorder=z))
    bw = w * 0.085
    for k in range(3):
        ax.add_patch(FancyBboxPatch(
            (x + w * 0.10 + k * bw * 1.5, y + h * 0.09), bw, h * 0.07,
            boxstyle="round,pad=0.0,rounding_size=0.3",
            facecolor='white', edgecolor=S.EDGE, lw=0.9, alpha=.85, zorder=z + 1))
    if text:
        ax.text(x + w / 2, y + h * (0.66 if sub else 0.55), text, ha='center',
                va='center', zorder=z + 2, fontsize=fs or S.FS['base'],
                fontweight=S.WEIGHT, color=S.SLATE, linespacing=1.4)
    if sub:
        ax.text(x + w / 2, y + h * 0.38, sub, ha='center', va='center',
                zorder=z + 2, fontsize=S.FS['note'], color=S.MUTE)


def lifeline(ax, x0, x1, y, label, sub=None, z=2):
    """时序图的生命线：一条水平轴 + 左侧标签。"""
    ax.plot([x0, x1], [y, y], color=S.EDGE, lw=1.2, zorder=z)
    ax.text(x0 - 1.5, y + (1.6 if sub else 0), label, ha='right', va='center',
            zorder=z + 1, fontsize=S.FS['note'], fontweight=S.WEIGHT, color=S.SLATE)
    if sub:
        ax.text(x0 - 1.5, y - 2.6, sub, ha='right', va='center', zorder=z + 1,
                fontsize=8.0, color=S.MUTE)


def tick(ax, x, y, label='', color=None, h=2.6, z=5, above=True):
    """生命线上的时刻标记。"""
    c = color or S.BLUE_D
    ax.plot([x, x], [y - h / 2, y + h / 2], color=c, lw=1.6, zorder=z)
    if label:
        ax.text(x, y + (h / 2 + 1.6) * (1 if above else -1), label, ha='center',
                va='bottom' if above else 'top', zorder=z + 1,
                fontsize=8.4, fontweight=S.WEIGHT, color=c)


def stackbar(ax, x, y, w, h, parts, z=3, lab_fs=None, inside=True):
    """堆叠横条。parts 为 [(比例, 颜色, 标签), ...]，比例之和应为 1。"""
    cx = x
    for frac, color, lab in parts:
        seg = w * frac
        ax.add_patch(FancyBboxPatch(
            (cx, y), seg, h, boxstyle="square,pad=0.0",
            facecolor=color, edgecolor='white', lw=1.4, zorder=z))
        if lab and inside:
            ax.text(cx + seg / 2, y + h / 2, lab, ha='center', va='center',
                    zorder=z + 2, fontsize=lab_fs or S.FS['note'],
                    fontweight=S.WEIGHT,
                    color='white' if color in (S.RED, S.BLUE, S.ORANGE) else S.SLATE,
                    linespacing=1.3)
        cx += seg
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="square,pad=0.0",
                                facecolor='none', edgecolor=S.EDGE, lw=1.3,
                                zorder=z + 3))


def eqbox(ax, x, y, lines, fs=None, z=6, w=None, align='left', title=None,
          face=None, pad=2.6, lh=6.4):
    """公式块：把正文的关键式子放到图上。

    宽度默认由内容量出来（渲染后取文字包围盒，再换算回数据坐标），
    因此不会出现"文字冲出框"这一类问题。传 w 可强制指定宽度。
    """
    fc = face if face is not None else S.F_L1
    fig = ax.figure
    fig.canvas.draw()                      # 需要先渲染才能量文字
    inv = ax.transData.inverted()

    def wide(txt, size, weight='normal'):
        tmp = ax.text(0, 0, txt, fontsize=size, fontweight=weight, alpha=0)
        fig.canvas.draw()
        bb = tmp.get_window_extent()
        p0 = inv.transform((0, 0)); p1 = inv.transform((bb.width, 0))
        tmp.remove()
        return abs(p1[0] - p0[0])

    fsz = fs or 9.6
    need = max([wide(ln, fsz) for ln in lines] +
               ([wide(title, 8.4, S.WEIGHT)] if title else [0]))
    ww = w if w is not None else need + pad * 2
    n = len(lines) + (1 if title else 0)
    hh = lh * n + pad * 1.6

    ax.add_patch(FancyBboxPatch(
        (x, y - hh), ww, hh, boxstyle="round,pad=0.0,rounding_size=1.2",
        facecolor=fc, edgecolor=S.EDGE, lw=1.0, zorder=z - 1))
    yy = y - pad - lh * 0.35
    if title:
        ax.text(x + pad, yy, title, ha='left', va='center', zorder=z,
                fontsize=8.4, fontweight=S.WEIGHT, color=S.MUTE)
        yy -= lh
    for ln in lines:
        cx = x + (ww / 2 if align == 'center' else pad)
        ax.text(cx, yy, ln, ha='center' if align == 'center' else 'left',
                va='center', zorder=z, fontsize=fsz, color=S.SLATE)
        yy -= lh
    return ww, hh
