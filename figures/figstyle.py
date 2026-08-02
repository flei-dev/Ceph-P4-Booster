#!/usr/bin/env python3
"""全文配图的统一样式（2026-07-31）

所有数据图都通过本模块设置样式并保存，保证配色、字体、线宽、尺寸一致。
示意图（图 3-1、3-2、4-1）如改用 draw.io 绘制，也按本模块的色值与字号执行。

投稿口径：IEEE 期刊要求矢量图或 ≥300 dpi 位图，字体需可嵌入。
`save()` 默认同时输出 PDF（矢量，投稿用）与 PNG（预览用）。
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm, ft2font
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

# ----------------------------------------------------------------- 配色
# 统一色系：结构一律用同一支蓝，靠明度分层；红与橙只留给需要强调的对象。
# 角色由形状承担（机箱／芯片／圆柱／云），不再由色相承担，因此全图色系一致。
SLATE = '#16212B'      # 正文文字

BLUE = '#0F6FC5'       # 主色：数据流、基线、结构主调
BLUE_D = '#0A4F8F'     # 主色深调：强调边框、深层结构
RED = '#D62828'        # 强调：本文系统、最慢副本、关键路径
ORANGE = '#F07300'     # 控制流：完成事件、提前确认
GOLD = '#E8B03A'       # 参考线、容量标注
TEAL = '#2A9D8F'       # 备用第三序列（数据图偶尔需要）

# 结构填充：同一支蓝的四级明度。深色文字在四级上均可读。
F_L1 = '#EAF3FA'       # 一级（最浅）：中性底、外部实体
F_L2 = '#CFE4F5'       # 二级：客户端、主机
F_L3 = '#A9CFEC'       # 三级：处理组件（Gate、主 OSD）
F_L4 = '#7FB5DF'       # 四级（最深）：持久化位置
F_ACC = '#F7C9C4'      # 强调填充：需要点出的那一个对象

# 兼容旧名
F_BLUE, F_GREEN, F_PURPLE, F_GREY, F_NEUTRAL = F_L2, F_L3, F_L4, F_L1, F_L1
MINT, SKY, LAV, GREY, SAND = F_L3, F_L2, F_L4, F_L1, GOLD
BAND = '#FDF0DC'       # 阴影区域
GRID = '#DCE2E6'
EDGE = '#3E5566'       # 描边：深蓝灰，与蓝色系同源
MUTE = '#54687A'       # 次要注释

# ------------------------------------------------------------- 字体
# 英文用 Calibri，Linux 上以度量兼容的 Carlito 替代。
# 中文用微软雅黑，Linux 上以 Noto Sans CJK 替代（同时覆盖拉丁字形，
# 中英混排不会出现缺字方框）。
for _p in ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
           '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
           '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf'):
    if os.path.exists(_p):
        try:
            fm.fontManager.addfont(_p)
        except Exception:
            pass
_HAVE = {f.name for f in fm.fontManager.ttflist}
EN_FONT = next((n for n in ('Calibri', 'Carlito') if n in _HAVE), 'DejaVu Sans')
CN_FONT = next((n for n in ('Microsoft YaHei', 'Noto Sans CJK SC',
                            'Noto Sans CJK JP', 'Droid Sans Fallback')
                if n in _HAVE), 'DejaVu Sans')
MONO = 'DejaVu Sans Mono'      # 代码标识符与状态名；Windows 上换 Consolas

# ------------------------------------------------------------- 尺寸与字号
# 单栏图宽 3.5 in，双栏图宽 7.2 in（IEEE 双栏排版）。本文按单页宽排版取 7.2。
W1, W2 = 3.5, 7.2
FS = dict(base=11.5, tick=10, label=11, legend=10, note=9, ann=9.5)
# 图内主体文字统一用半粗，标注用常规
WEIGHT = 'bold'
DPI = 300

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')


def use(lang='en'):
    """设置一次 rcParams。lang='en' 用 Calibri，'cn' 用雅黑并回退拉丁字形。"""
    fam = [CN_FONT, EN_FONT, 'DejaVu Sans'] if lang == 'cn' else [EN_FONT, 'DejaVu Sans']
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': fam,
        'axes.unicode_minus': False,
        'font.size': FS['base'],
        'axes.labelsize': FS['label'],
        'xtick.labelsize': FS['tick'],
        'ytick.labelsize': FS['tick'],
        'legend.fontsize': FS['legend'],
        'text.color': SLATE,
        'axes.labelcolor': SLATE,
        'xtick.color': SLATE,
        'ytick.color': SLATE,
        'axes.edgecolor': '#B9C2C9',
        'figure.dpi': DPI,
        'savefig.dpi': DPI,
        # 让 PDF/EPS 里的字体以 TrueType 嵌入，满足 IEEE 的字体嵌入要求
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
    })


def frame(ax, legend_loc='upper left', ncol=1, legend=True):
    """统一的坐标区外观：只留左下两条轴线、浅网格、无边框图例。"""
    ax.grid(True, which='major', color=GRID, lw=.8)
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        ax.spines[s].set_color('#B9C2C9')
    if legend:
        ax.legend(frameon=False, loc=legend_loc, ncol=ncol)


# 输出目录层级：类别 → 语言 → 格式
CAT = {'schematic': '示意图', 'data': '数据图'}
LANG = {'cn': '中文', 'en': '英文'}


def outdir(kind, lang, ext):
    """out/<示意图|数据图>/<中文|英文>/<PDF|PNG>/"""
    return os.path.join(OUT, CAT[kind], LANG[lang], ext.upper())


def audit(fig, ax, name, lang):
    """排版自检：保存前跑一遍，把版面缺陷打印出来，不靠肉眼一张张看。

    查七类：文字越界、文字互相重叠、字体缺字（会渲染成方框或问号）、
    色块遮住文字、文字压在别的色块上、文字比所在色块宽、箭头端点落空。
    默认开启；设 FIGAUDIT=0 可关掉。无输出即全部通过。
    """
    fig.canvas.draw()
    ab = ax.get_window_extent()
    items = []
    for t in ax.texts:
        if not t.get_text().strip():
            continue
        try:
            bb = t.get_window_extent()
        except Exception:
            continue
        items.append((t.get_text().replace('\n', ' ')[:34], bb))
    issues = []
    for txt, bb in items:
        if bb.x0 < ab.x0 - 1 or bb.x1 > ab.x1 + 1 or bb.y0 < ab.y0 - 1 or bb.y1 > ab.y1 + 1:
            issues.append(f'越界   「{txt}」')
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i][1], items[j][1]
            ox = min(a.x1, b.x1) - max(a.x0, b.x0)
            oy = min(a.y1, b.y1) - max(a.y0, b.y0)
            if ox > 2 and oy > 2:
                issues.append(f'重叠   「{items[i][0]}」 × 「{items[j][0]}」')
    # 三、缺字：字体里没有该字形时会渲染成方框或问号
    fam = plt.rcParams['font.sans-serif']
    faces = []
    for nm in fam:
        try:
            faces.append(ft2font.FT2Font(fm.findfont(nm, fallback_to_default=False)))
        except Exception:
            pass
    seen = set()
    for t in ax.texts:
        for ch in t.get_text():
            if ch in seen or ch in ' \n' or ord(ch) < 32:
                continue
            seen.add(ch)
            if faces and not any(f.get_char_index(ord(ch)) for f in faces):
                issues.append(f'缺字   U+{ord(ch):04X} 「{ch}」 出现在「{t.get_text()[:20]}」')

    # 四、遮挡：层级更高的色块压在文字上
    for t in ax.texts:
        if not t.get_text().strip():
            continue
        tb = t.get_window_extent()
        for p in ax.patches:
            if p.get_zorder() <= t.get_zorder() or p.get_alpha() == 0:
                continue
            fc = p.get_facecolor()
            if len(fc) > 3 and fc[3] < 0.05:
                continue
            pb = p.get_window_extent()
            if (min(tb.x1, pb.x1) - max(tb.x0, pb.x0) > 2 and
                    min(tb.y1, pb.y1) - max(tb.y0, pb.y0) > 2):
                issues.append(f'遮挡   色块压住「{t.get_text()[:24]}」')

    # 七、压图：文字压在不属于它的色块上（色块层级更低时前面查不出来）
    for t in ax.texts:
        if not t.get_text().strip():
            continue
        tb = t.get_window_extent()
        cx, cy = (tb.x0 + tb.x1) / 2, (tb.y0 + tb.y1) / 2
        for p in ax.patches:
            if not isinstance(p, (FancyBboxPatch, Rectangle)):
                continue
            fc = p.get_facecolor()
            if len(fc) > 3 and fc[3] < 0.05:
                continue
            pb = p.get_window_extent()
            if pb.width < 4 or pb.height < 4:
                continue
            if pb.x0 < cx < pb.x1 and pb.y0 < cy < pb.y1:
                continue                       # 是这个框自己的标注
            if (min(tb.x1, pb.x1) - max(tb.x0, pb.x0) > 3 and
                    min(tb.y1, pb.y1) - max(tb.y0, pb.y0) > 3):
                issues.append(f'压图   「{t.get_text()[:24]}」压在别的色块上')
                break

    # 六、溢出：文字比它所在的色块还宽
    for t in ax.texts:
        if not t.get_text().strip():
            continue
        tb = t.get_window_extent()
        cx, cy = (tb.x0 + tb.x1) / 2, (tb.y0 + tb.y1) / 2
        for p in ax.patches:
            if not isinstance(p, (FancyBboxPatch, Rectangle)):
                continue          # 只查真正的标签底框，云朵圆瓣之类不算
            fc = p.get_facecolor()
            if len(fc) > 3 and fc[3] < 0.05:      # 虚线框等无填充容器不算
                continue
            pb = p.get_window_extent()
            if pb.width < 4 or pb.height < 4:
                continue
            if pb.width * pb.height > 25 * max(tb.width * tb.height, 1):
                continue                          # 大面积底图，不是标签底框
            if not (pb.x0 < cx < pb.x1 and pb.y0 < cy < pb.y1):
                continue
            if tb.x0 < pb.x0 - 1 or tb.x1 > pb.x1 + 1:
                issues.append(f'溢出   「{t.get_text()[:20]}」比所在色块宽')
            break

    # 五、箭头落空：端点没有落在任何图形上
    tol = fig.dpi * 0.07     # 容差按 dpi 折算：留 0.07 in 的贴合间隙算命中
    for a in ax.patches:
        if not isinstance(a, FancyArrowPatch):
            continue
        try:
            p0, p1 = a._posA_posB
        except Exception:
            continue
        for pt, tag in ((p0, '起点'), (p1, '终点')):
            d = ax.transData.transform(pt)
            hit = (d[0] <= ab.x0 + tol or d[0] >= ab.x1 - tol or
                   d[1] <= ab.y0 + tol or d[1] >= ab.y1 - tol)   # 画布进出口
            for p in ax.patches:
                if hit:
                    break
                if p is a or isinstance(p, FancyArrowPatch):
                    continue
                b = p.get_window_extent()
                if (b.x0 - tol <= d[0] <= b.x1 + tol) and (b.y0 - tol <= d[1] <= b.y1 + tol):
                    hit = True
            for t in ax.texts:                               # 指向标注的引线
                if hit:
                    break
                b = t.get_window_extent()
                if (b.x0 - tol <= d[0] <= b.x1 + tol) and (b.y0 - tol <= d[1] <= b.y1 + tol):
                    hit = True
            for ln in ax.lines:                              # 生命线、时间轴
                if hit:
                    break
                xd, yd = ln.get_xdata(), ln.get_ydata()
                if len(xd) == 1:                     # 单点标记（采集点等）
                    q = ax.transData.transform((xd[0], yd[0]))
                    if abs(q[0] - d[0]) <= tol and abs(q[1] - d[1]) <= tol:
                        hit = True
                    continue
                if len(xd) < 2:
                    continue
                for k in range(len(xd) - 1):
                    q0 = ax.transData.transform((xd[k], yd[k]))
                    q1 = ax.transData.transform((xd[k + 1], yd[k + 1]))
                    if (min(q0[0], q1[0]) - tol <= d[0] <= max(q0[0], q1[0]) + tol and
                            min(q0[1], q1[1]) - tol <= d[1] <= max(q0[1], q1[1]) + tol):
                        hit = True
                        break
            if not hit:
                issues.append(f'落空   箭头{tag} {tuple(round(v, 1) for v in pt)} 不在任何图形上')

    if issues:
        print(f'  [检查] {name}_{lang}: {len(issues)} 处')
        for m in issues:
            print(f'         {m}')
    return issues


def save(fig, name, lang, kind='schematic'):
    """按 类别／语言／格式 三级归档，同时输出 PDF（投稿）与 PNG（预览）。"""
    fig.tight_layout()
    if os.environ.get('FIGAUDIT', '1') != '0':
        audit(fig, fig.axes[0], name, lang)
    for ext in ('pdf', 'png'):
        d = outdir(kind, lang, ext)
        os.makedirs(d, exist_ok=True)
        fig.savefig(os.path.join(d, f'{name}.{ext}'),
                    facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print(f'  {CAT[kind]}/{LANG[lang]}/  {name}.pdf + .png')


def floor_line(ax, floor, text, x=None, ha='left'):
    """统一的"仿真环境本底"标注。"""
    ax.axhline(floor, color='#B9C2C9', lw=1.0, ls=':')
    x0, x1 = ax.get_xlim()
    ax.text(x if x is not None else x0 + (x1 - x0) * 0.02,
            floor * 1.13, text, fontsize=FS['note'], color=MUTE, ha=ha)


def q(v, p):
    s = sorted(v)
    return s[min(len(s) - 1, int(p * (len(s) - 1)))]
