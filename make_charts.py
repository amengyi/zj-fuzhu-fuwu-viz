# -*- coding: utf-8 -*-
"""生成两张与参考图同格式的热力图 PNG：
1. 浙江AGC月度补偿热力图（仿 各省AGC:二次调频月度补偿.png）——万元取整
2. 浙江储能调频补偿收入热力图（仿 2026年山东储能调频补偿收入.png）
   —— 全部并网主体（D列有偿一次调频补偿出现过非零的267个）· 万元保留4位小数
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import os

from agc_data import load_agc, load_storage_all, ALL_MONTHS

BASE = os.path.dirname(os.path.abspath(__file__))
plt.rcParams["font.family"] = ["Hiragino Sans GB"]
plt.rcParams["axes.unicode_minus"] = False

TITLE_COLOR = "#1a2740"
MISSING_BG = "#dfe3ea"


def _shade(v, bins, colors):
    for (lo, hi), c in zip(bins, colors):
        if lo <= v < hi:
            return c
    return colors[-1]


# ============ 图1：AGC 月度补偿 ============
def draw_agc():
    rows = load_agc()
    months = [r[0] for r in rows]
    vals = [r[1] for r in rows]

    n = len(months)
    cell_w, cell_h = 3.0, 0.62
    left = 3.4
    width = left + cell_w + 1.2
    height = 3.3 + n * cell_h

    fig = plt.figure(figsize=(width, height), dpi=110)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.axis("off")

    ax.text(width / 2, height - 0.7, "浙江 AGC / 二次调频月度补偿",
            fontsize=20, fontweight="bold", color=TITLE_COLOR, ha="center", va="center")
    ax.text(width / 2, height - 1.32,
            "单位：万元/月 · 四舍五入至整数 · 2025-01~2025-06 为模拟结算，2025-07 起为正式结算 · 资料校验：2026-10-30",
            fontsize=9.5, color="#5b6b80", ha="center", va="center")

    y0 = height - 2.15
    xcol = left + cell_w / 2
    ax.text(xcol, y0 + 0.7, "浙江\n21个月", ha="center", va="center",
            fontsize=12, fontweight="bold", color=TITLE_COLOR, linespacing=1.4)

    bins = [(-1e9, 0), (0, 250), (250, 500), (500, 1000), (1000, 2500),
            (2500, 5000), (5000, 1e9)]
    colors = ["#0b1f5e", "#a8c8f0", "#5b8fd9", "#2e5fb0", "#f5c99b", "#e8834a", "#c0392b"]

    for i, m in enumerate(months):
        y = y0 - (i + 0.5) * cell_h
        ax.text(left - 0.25, y, m, ha="right", va="center", fontsize=10.5, color="#333")
        v = vals[i]
        if v is None:
            ax.add_patch(Rectangle((left, y - cell_h / 2 + 0.05), cell_w - 0.08, cell_h - 0.1,
                                   facecolor=MISSING_BG, edgecolor="none"))
            ax.text(xcol, y, "—", ha="center", va="center", fontsize=10, color="#98a2b0")
        else:
            vi = int(round(v))
            c = _shade(v, bins, colors)
            ax.add_patch(Rectangle((left, y - cell_h / 2 + 0.05), cell_w - 0.08, cell_h - 0.1,
                                   facecolor=c, edgecolor="none"))
            tc = "white" if vi >= 2500 or vi <= 0 else "#1a2740"
            ax.text(xcol, y, f"{vi:,}", ha="center", va="center", fontsize=11,
                    color=tc, fontweight="bold" if vi >= 2500 else "normal")

    # 模拟/正式结算分界线（2025-06 与 2025-07 之间）
    k = months.index("2025-07")
    yline = y0 - k * cell_h
    ax.plot([left - 0.1, left + cell_w], [yline, yline], color="#1a2740", lw=1.4)
    ax.text(left - 0.25, yline + cell_h / 2 + 0.05, "↑ 模拟结算", ha="right", va="center",
            fontsize=8.5, color="#8a97a8")
    ax.text(left - 0.25, yline - cell_h / 2 - 0.05, "↓ 正式结算", ha="right", va="center",
            fontsize=8.5, color="#8a97a8")

    # 图例（两行排布避免超宽）
    legend_items = [("≤0", "#0b1f5e"), ("0–250", "#a8c8f0"), ("250–500", "#5b8fd9"),
                    ("500–1,000", "#2e5fb0"), ("1,000–2,500", "#f5c99b"),
                    ("2,500–5,000", "#e8834a"), ("≥5,000", "#c0392b"), ("缺失", MISSING_BG)]
    lx0, ly0, item_w = 0.4, 0.55, 2.0
    for idx, (lab, c) in enumerate(legend_items):
        r, col = divmod(idx, 4)
        lx = lx0 + col * item_w
        ly = ly0 - r * 0.42
        ax.add_patch(Rectangle((lx, ly - 0.09), 0.4, 0.26, facecolor=c, edgecolor="none"))
        ax.text(lx + 0.5, ly + 0.04, lab, ha="left", va="center", fontsize=9, color="#333")

    out = os.path.join(BASE, "AGC:二次调频月度补偿", "浙江AGC月度补偿热力图.png")
    fig.savefig(out, dpi=110, facecolor="white")
    plt.close(fig)
    print("saved:", out)


# ============ 图2：储能调频补偿收入（仅储能类主体，总收入倒序，单位：元取整） ============


def draw_storage():
    STORAGE_TYPES = {"储能", "抽蓄", "抽水蓄能", "电化学储能"}
    stations, matrix = load_storage_all(types=STORAGE_TYPES)
    months = list(ALL_MONTHS)

    n_row, n_col = len(stations), len(months)
    cell_w, cell_h = 0.8, 0.26
    left = 3.0
    width = left + n_col * cell_w + 0.6
    height = 2.6 + n_row * cell_h

    fig = plt.figure(figsize=(width, height), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.axis("off")

    ax.text(0.25, height - 0.5, "2025–2026 年浙江储能调频补偿收入",
            fontsize=16, fontweight="bold", color=TITLE_COLOR, ha="left", va="center")
    ax.text(0.25, height - 0.95,
            "仅储能类主体 · 有偿一次调频补偿 · 按总收入倒序 · 单位：元（四舍五入取整） · "
            "空=无数据",
            fontsize=8.5, color="#5b6b80", ha="left", va="center")

    y0 = height - 1.6
    ax.text(0.25, y0 + 0.3, "#", ha="center", fontsize=7, color="#666")
    ax.text(0.65, y0 + 0.3, "并网主体", ha="left", fontsize=7, color="#666")
    ax.text(left - 0.1, y0 + 0.3, "月数/总计", ha="right", fontsize=7, color="#666")
    for j, m in enumerate(months):
        ax.text(left + j * cell_w + cell_w / 2, y0 + 0.3, m[2:].replace("-", "/"),
                ha="center", va="center", fontsize=6.2, color="#555")

    # 元级分箱：0-2 / 2-5 / 5-10 / 10-20 / 20-40 / 40-80 / ≥80
    edges = [0, 2, 5, 10, 20, 40, 80, 1e9]
    bins = list(zip(edges[:-1], edges[1:]))
    colors = ["#dce7f5", "#aac8ec", "#6f9fdd", "#3a6fc4", "#e9a86b", "#d97b3f", "#b03a26"]

    for i, s in enumerate(stations):
        y = y0 - (i + 0.5) * cell_h
        vals = matrix[s]
        active = [v for v in vals.values() if v]
        total = sum(active)
        ax.text(0.25, y, str(i + 1), ha="center", va="center", fontsize=6, color="#888")
        ax.text(0.65, y, s, ha="left", va="center", fontsize=6.5, color="#222")
        ax.text(left - 0.1, y, f"{len(active)}/{int(round(total)):,}", ha="right",
                va="center", fontsize=6, color="#555")
        for j, m in enumerate(months):
            v = vals.get(m)
            if not v:
                continue
            x = left + j * cell_w
            c = _shade(v, bins, colors)
            ax.add_patch(Rectangle((x, y - cell_h / 2 + 0.015), cell_w - 0.05, cell_h - 0.03,
                                   facecolor=c, edgecolor="none"))
            vi = int(round(v))
            tc = "white" if vi >= 20 else "#1a2740"
            ax.text(x + (cell_w - 0.05) / 2, y, str(vi),
                    ha="center", va="center", fontsize=5.8, color=tc)

    # 模拟/正式结算分界线
    k = months.index("2025-07")
    yline = y0 - k * cell_h
    ax.plot([0.2, left + n_col * cell_w], [yline, yline], color="#1a2740", lw=1.0)
    ax.text(0.2, yline + 0.09, "↑ 模拟结算", ha="left", va="center", fontsize=6.5, color="#8a97a8")
    ax.text(0.2, yline - 0.09, "↓ 正式结算", ha="left", va="center", fontsize=6.5, color="#8a97a8")

    # 图例
    ly = 0.3
    lx = 0.3
    labels = ["1–2", "2–5", "5–10", "10–20", "20–40", "40–80", "≥80"]
    for lab, c in zip(labels, colors):
        ax.add_patch(Rectangle((lx, ly - 0.055), 0.26, 0.15, facecolor=c, edgecolor="none"))
        ax.text(lx + 0.32, ly + 0.02, lab, ha="left", va="center", fontsize=6.2, color="#333")
        lx += 0.32 + len(lab) * 0.048 + 0.18

    out = os.path.join(BASE, "储能调频补偿收入", "浙江储能调频补偿收入热力图.png")
    fig.savefig(out, dpi=100, facecolor="white")
    plt.close(fig)
    print("saved:", out, f"({n_row} 主体 x {n_col} 月)")


if __name__ == "__main__":
    draw_agc()
    draw_storage()
