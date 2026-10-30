# -*- coding: utf-8 -*-
"""浙江辅助服务数据可视化：AGC 月度补偿 + 储能调频补偿收入
图表完全复刻参考 PNG 样式（分档配色/图例/单元格数值/结算分界线）。
运行: streamlit run viz_app.py --server.port 8501
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from agc_data import load_agc, load_storage_all, ALL_MONTHS

STORAGE_TYPES = {"储能", "抽蓄", "抽水蓄能", "电化学储能"}
TITLE_COLOR = "#1a2740"

st.set_page_config(page_title="浙江辅助服务补偿可视化", page_icon="⚡", layout="wide")

# ---------- 数据 ----------
@st.cache_data
def get_data():
    agc = load_agc()
    agc_df = pd.DataFrame(agc, columns=["月份", "补偿金额（万元）", "结算类型"])
    stations, matrix = load_storage_all(types=STORAGE_TYPES)
    recs = []
    for s in stations:
        for m, v in matrix[s].items():
            if v:
                recs.append({"并网主体": s, "月份": m, "补偿金额（万元）": v})
    sto_df = pd.DataFrame(recs)
    sto_df["结算类型"] = sto_df["月份"].apply(
        lambda m: "模拟结算" if m <= "2025-06" else "正式结算")
    return agc_df, sto_df

agc_df, sto_df = get_data()

# ---------- 分档样式（与参考 PNG 一致） ----------
# AGC：万元/月
AGC_BINS = [(-1e9, 0), (0, 100), (100, 250), (250, 500), (500, 1000),
            (1000, 2500), (2500, 5000), (5000, 10000), (10000, 1e9)]
AGC_COLORS = ["#122a6e", "#9cc0ee", "#5b8fd9", "#2e5fb0", "#dbe7f6",
              "#f7cf9f", "#ef9950", "#e2762e", "#b7372a"]
AGC_LEGEND = ["<0", "0—100", "100—250", "250—500", "500—1,000",
              "1,000—2,500", "2,500—5,000", "5,000—10,000", "≥10,000", "缺失"]
AGC_MISSING = "#dfe3ea"
# 储能：元/月
STO_BINS = [(0, 2), (2, 5), (5, 10), (10, 20), (20, 40), (40, 80), (80, 1e9)]
STO_COLORS = ["#dce7f5", "#aac8ec", "#6f9fdd", "#3a6fc4", "#e9a86b", "#d97b3f", "#b03a26"]
STO_LEGEND = ["1–2", "2–5", "5–10", "10–20", "20–40", "40–80", "≥80"]
# 储能总收入（元）
TOTAL_BINS = [(0, 500), (500, 2000), (2000, 5000), (5000, 10000), (10000, 1e9)]
TOTAL_COLORS = ["#dce7f5", "#9cc0ee", "#5b8fd9", "#e8834a", "#b03a26"]
TOTAL_LEGEND = ["<500", "500–2,000", "2,000–5,000", "5,000–10,000", "≥10,000"]


def _bindex(v, bins):
    for i, (lo, hi) in enumerate(bins):
        if lo <= v < hi:
            return i
    return len(bins) - 1


def _colorscale(colors):
    n = len(colors)
    cs = []
    for i, c in enumerate(colors):
        cs += [[i / n, c], [(i + 1) / n, c]]
    return cs


def legend_html(items):
    spans = "".join(
        f"<span style='display:inline-flex;align-items:center;margin:0 14px 6px 0;'>"
        f"<span style='width:14px;height:14px;background:{c};display:inline-block;"
        f"margin-right:5px;border-radius:2px;'></span>{lab}</span>"
        for lab, c in items)
    return f"<div style='font-size:13px;color:#333;margin:2px 0 8px;'>{spans}</div>"


def month_label(m, with_year):
    y, mm = m[:4], int(m[5:7])
    return f"{y[-2:]}/{mm}月" if with_year else f"{mm}月"


# ---------- 侧边栏筛选 ----------
st.sidebar.title("⚙️ 筛选")
tab_label = st.sidebar.radio("数据视图", ["AGC/二次调频月度补偿", "储能调频补偿收入"])
year_opt = st.sidebar.selectbox("年份", ["全部", "2025", "2026"])
settle_opt = st.sidebar.multiselect(
    "结算类型", ["模拟结算", "正式结算"], default=["模拟结算", "正式结算"])

with_year = year_opt == "全部"
if tab_label == "AGC/二次调频月度补偿":
    src = agc_df
else:
    src = sto_df

df = src[src["结算类型"].isin(settle_opt)]
if not with_year:
    df = df[df["月份"].str.startswith(year_opt)]

topn = len(df["并网主体"].unique())
if tab_label == "储能调频补偿收入":
    stations_all = sorted(df["并网主体"].unique(),
                          key=lambda s: -df[df["并网主体"] == s]["补偿金额（万元）"].sum())
    topn = st.sidebar.slider("按总收入取前 N 个主体", 5, len(stations_all),
                             len(stations_all))

st.sidebar.markdown("---")
st.sidebar.caption("📌 2025-01 ~ 2025-06 为**模拟结算**；2025-07 ~ 2026-09 为**正式结算**。"
                   "AGC 单位为**万元**，储能热力图单位为**元**，均四舍五入取整。")

# ---------- 主页面 ----------
st.title("⚡ 浙江辅助服务补偿数据可视化")
st.markdown(
    ":warning: **数据口径说明**：2025-01 ~ 2025-06 为 **模拟结算**，"
    "2025-07 ~ 2026-09 为 **正式结算**。")

tab1, tab2 = st.tabs(["📈 可视化", "📋 源数据查看/导出"])

with tab1:
    if df.empty:
        st.warning("当前筛选条件下无数据。")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("合计（万元）", f"{df['补偿金额（万元）'].sum():,.2f}")
        c2.metric("月均（万元）", f"{df['补偿金额（万元）'].mean():,.2f}")
        c3.metric("记录数", f"{len(df):,}")

        if tab_label == "AGC/二次调频月度补偿":
            # ===== 图1：复刻《各省AGC/二次调频月度补偿》样式（月份为行） =====
            st.markdown("#### 浙江 AGC / 二次调频月度补偿")
            st.caption("单位：万元/月 · 四舍五入至整数 · 蓝色为低值·红色为高值 · "
                       "按图例分档 · 灰色为缺失")
            monthly = df.groupby("月份")["补偿金额（万元）"].sum()
            months = [m for m in ALL_MONTHS if m in monthly.index]
            labels = [month_label(m, with_year) for m in months]

            z, texts = [], []
            for m in months:
                v = monthly.get(m)
                if v is None or pd.isna(v):
                    z.append(9)
                    texts.append("—")
                else:
                    b = _bindex(v, AGC_BINS)
                    z.append(b)
                    texts.append(f"{round(v):,}")

            fig = go.Figure(go.Heatmap(
                z=[z], x=["浙江"], y=labels,
                zmin=0, zmax=9, colorscale=_colorscale(AGC_COLORS + [AGC_MISSING]),
                showscale=False, xgap=3, ygap=3, hoverinfo="skip"))
            # 单元格数值（白字用于深色档）
            for yi, (lab, t, b) in enumerate(zip(labels, texts, z)):
                if t == "—":
                    fc, col = 10, "#98a2b0"
                else:
                    fc = 11
                    col = "white" if b in (0, 6, 7, 8) else TITLE_COLOR
                fig.add_annotation(x="浙江", y=lab, text=t, showarrow=False,
                                   font=dict(size=fc, color=col))
            # 列头
            fig.add_annotation(x="浙江", yref="paper", y=1.02, xanchor="center",
                               text=f"<b>浙江<br>{len(months)}个月</b>", showarrow=False,
                               font=dict(size=14, color=TITLE_COLOR))
            fig.update_yaxes(autorange="reversed", tickfont=dict(size=11),
                             showgrid=False)
            fig.update_xaxes(side="top", showgrid=False)
            # 模拟/正式结算分界线
            if "2025-06" in months and "2025-07" in months:
                k = months.index("2025-07")
                fig.add_shape(type="line", xref="paper", x0=0, x1=1,
                              yref="y", y0=k - 0.5, y1=k - 0.5,
                              line=dict(color=TITLE_COLOR, width=2))
            fig.update_layout(height=90 + len(months) * 34,
                              margin=dict(l=10, r=10, t=70, b=10))
            st.plotly_chart(fig, use_container_width=True)
            if "2025-06" in months and "2025-07" in months:
                st.caption("──────── 分界线：上方为模拟结算，下方为正式结算 ────────")
            st.markdown(legend_html(list(zip(AGC_LEGEND, AGC_COLORS + [AGC_MISSING]))),
                        unsafe_allow_html=True)

        else:
            # ===== 图2：复刻《山东储能调频补偿收入》样式（月份为列，总收入倒序） =====
            st.markdown("#### 浙江储能调频补偿收入")
            st.caption("单位：元（取整） · 空白=无数据 · 按所选范围总收入倒序 · "
                       "2026-07 暂无补偿结算数据 · 虚线右侧说明见分界标注")
            show_stations = stations_all[:topn]
            sub = df[df["并网主体"].isin(show_stations)]
            months = sorted(sub["月份"].unique())
            totals = sub.groupby("并网主体")["补偿金额（万元）"].sum()
            piv = sub.pivot_table(index="并网主体", columns="月份",
                                  values="补偿金额（万元）", aggfunc="sum")
            piv = piv.reindex(show_stations)

            ylabels = [f"{i + 1}　{s}" for i, s in enumerate(show_stations)]
            xlabels = [month_label(m, with_year) for m in months] + ["总收入"]

            colors = STO_COLORS + TOTAL_COLORS
            z, txt, wcols = [], [], []
            for s in show_stations:
                zr, tr, wr = [], [], []
                for m in months:
                    v = piv.at[s, m] if m in piv.columns else None
                    if v is None or pd.isna(v) or v <= 0:
                        zr.append(None); tr.append(""); wr.append(False)
                    else:
                        b = _bindex(v, STO_BINS)
                        zr.append(b)
                        tr.append(f"{round(v)}")
                        wr.append(b >= 4)
                t = totals.get(s, 0) * 10000  # 元
                b = _bindex(t, TOTAL_BINS)
                zr.append(b); tr.append(f"{round(t):,}"); wr.append(b >= 3)
                z.append(zr); txt.append(tr); wcols.append(wr)

            fig2 = go.Figure(go.Heatmap(
                z=z, x=xlabels, y=ylabels,
                zmin=0, zmax=len(colors) - 1, colorscale=_colorscale(colors),
                showscale=False, xgap=2, ygap=2, hoverinfo="skip"))
            for i, (tr, wr) in enumerate(zip(txt, wcols)):
                for j, (t, w) in enumerate(zip(tr, wr)):
                    if not t:
                        continue
                    fig2.add_annotation(
                        x=xlabels[j], y=ylabels[i], text=t, showarrow=False,
                        font=dict(size=9, color="white" if w else TITLE_COLOR))
            # 模拟/正式结算分界线（2025-06 | 2025-07 之间）
            if "2025-06" in months and "2025-07" in months:
                k = months.index("2025-07")
                fig2.add_vline(x=k - 0.5, line_color=TITLE_COLOR, line_width=1.5)
            fig2.update_yaxes(autorange="reversed", tickfont=dict(size=10),
                              showgrid=False)
            fig2.update_layout(height=140 + len(show_stations) * 24,
                               margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig2, use_container_width=True)
            if "2025-06" in months and "2025-07" in months:
                st.caption("──────── 分界线：左侧为模拟结算，右侧为正式结算 ────────")
            st.markdown(legend_html(list(zip(STO_LEGEND, STO_COLORS)) +
                                    [("总收入·" + l, c)
                                     for l, c in zip(TOTAL_LEGEND, TOTAL_COLORS)]),
                        unsafe_allow_html=True)

with tab2:
    st.subheader("源数据（AGC 单位：万元；储能单位：万元）")
    show_df = df.copy()
    show_df["补偿金额（万元）"] = show_df["补偿金额（万元）"].round(
        0 if tab_label.startswith("AGC") else 4)
    st.dataframe(show_df, use_container_width=True, height=460)
    st.download_button(
        "⬇️ 导出当前筛选数据 (CSV)",
        data=show_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"浙江辅助服务补偿_{tab_label[:6]}.csv", mime="text/csv")
