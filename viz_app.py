# -*- coding: utf-8 -*-
"""浙江辅助服务数据可视化：AGC 月度补偿 + 储能调频补偿收入
运行: streamlit run viz_app.py --server.port 8501
"""
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from agc_data import load_agc, load_storage_all, ALL_MONTHS

st.set_page_config(page_title="浙江辅助服务补偿可视化", page_icon="⚡", layout="wide")

# ---------- 数据 ----------
@st.cache_data
def get_data():
    agc = load_agc()
    agc_df = pd.DataFrame(agc, columns=["月份", "补偿金额（万元）", "结算类型"])
    stations, matrix = load_storage_all()
    recs = []
    for s in stations:
        for m, v in matrix[s].items():
            recs.append({"并网主体": s, "月份": m, "补偿金额（万元）": v})
    sto_df = pd.DataFrame(recs)
    sto_df["结算类型"] = sto_df["月份"].apply(
        lambda m: "模拟结算" if m <= "2025-06" else "正式结算")
    return agc_df, sto_df

agc_df, sto_df = get_data()

# ---------- 侧边栏筛选 ----------
st.sidebar.title("⚙️ 筛选")

tab_label = st.sidebar.radio("数据视图", ["AGC/二次调频月度补偿", "储能调频补偿收入"])

if tab_label == "AGC/二次调频月度补偿":
    months_all = ALL_MONTHS
    m_range = st.sidebar.select_slider(
        "月份范围", options=months_all,
        value=(months_all[0], months_all[-1]))
    settle_opt = st.sidebar.multiselect(
        "结算类型", ["模拟结算", "正式结算"], default=["模拟结算", "正式结算"])
    topn = st.sidebar.slider("显示前 N 个月", 3, len(months_all), len(months_all))
    df = agc_df[
        (agc_df["月份"] >= m_range[0]) & (agc_df["月份"] <= m_range[1])
        & (agc_df["结算类型"].isin(settle_opt))
    ].sort_values("月份", ascending=False).head(topn).sort_values("月份")
else:
    stations_all = sorted(sto_df["并网主体"].unique(),
                          key=lambda s: -sto_df[sto_df["并网主体"] == s]["补偿金额（万元）"].sum())
    m_range = st.sidebar.select_slider(
        "月份范围", options=ALL_MONTHS, value=(ALL_MONTHS[0], ALL_MONTHS[-1]))
    settle_opt = st.sidebar.multiselect(
        "结算类型", ["模拟结算", "正式结算"], default=["模拟结算", "正式结算"])
    sel_stations = st.sidebar.multiselect(
        "并网主体（不选=全部）", stations_all, default=[])
    topn = st.sidebar.slider("按总收入取前 N 个主体", 5, len(stations_all),
                             min(40, len(stations_all)))
    show = sel_stations if sel_stations else stations_all[:topn]
    df = sto_df[
        (sto_df["并网主体"].isin(show))
        & (sto_df["月份"] >= m_range[0]) & (sto_df["月份"] <= m_range[1])
        & (sto_df["结算类型"].isin(settle_opt))
    ]

st.sidebar.markdown("---")
st.sidebar.caption("📌 2025-01 ~ 2025-06 为**模拟结算**；2025-07 ~ 2026-09 为**正式结算**。"
                   "所有金额单位均为**万元**。")

# ---------- 主页面 ----------
st.title("⚡ 浙江辅助服务补偿数据可视化")
st.markdown(
    ":warning: **数据口径说明**：2025-01 ~ 2025-06 为 **模拟结算**，"
    "2025-07 ~ 2026-09 为 **正式结算**；所有金额已转换为 **万元**。")

tab1, tab2 = st.tabs(["📈 可视化", "📋 源数据查看/导出"])

with tab1:
    if df.empty:
        st.warning("当前筛选条件下无数据。")
    else:
        pivot = df.pivot_table(index="月份", values="补偿金额（万元）", aggfunc="sum")
        c1, c2, c3 = st.columns(3)
        c1.metric("合计（万元）", f"{df['补偿金额（万元）'].sum():,.2f}")
        c2.metric("月均（万元）", f"{df['补偿金额（万元）'].mean():,.2f}")
        c3.metric("记录数", f"{len(df):,}")

        st.subheader("月度趋势")
        monthly = df.groupby("月份", as_index=False)["补偿金额（万元）"].sum()
        fig = px.bar(monthly, x="月份", y="补偿金额（万元）",
                     color="补偿金额（万元）", color_continuous_scale="RdBu_r",
                     text_auto=".0f" if tab_label.startswith("AGC") else ".4f")
        fig.update_layout(height=380, xaxis_title=None,
                          yaxis_title="补偿金额（万元）")
        # 模拟/正式结算分界
        if monthly["月份"].min() <= "2025-06" < monthly["月份"].max():
            fig.add_vline(x=monthly["月份"].tolist().index("2025-07") - 0.5,
                          line_dash="solid", line_color="#1a2740", line_width=2,
                          annotation_text="模拟→正式结算", annotation_position="top left")
        st.plotly_chart(fig, use_container_width=True)

        if tab_label == "储能调频补偿收入":
            st.subheader("热力图（并网主体 × 月份）")
            heat = df.pivot_table(index="并网主体", columns="月份",
                                  values="补偿金额（万元）", aggfunc="sum")
            order = (df.groupby("并网主体")["补偿金额（万元）"].sum()
                     .sort_values(ascending=False).index.tolist())
            heat = heat.reindex(order)
            fig2 = go.Figure(go.Heatmap(
                z=heat.values.round(4), x=heat.columns, y=heat.index,
                colorscale="RdBu_r", reversescale=True,
                colorbar=dict(title="万元"),
                hovertemplate="%{y} · %{x}<br>%{z:.4f} 万元<extra></extra>",
                xgap=2, ygap=2))
            fig2.update_layout(height=min(1400, 220 + len(heat) * 22), yaxis=dict(
                autorange="reversed", tickfont=dict(size=9)))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.subheader("明细")
            fig3 = px.line(df, x="月份", y="补偿金额（万元）", markers=True)
            fig3.update_layout(height=340, yaxis_title="补偿金额（万元）")
            st.plotly_chart(fig3, use_container_width=True)

with tab2:
    st.subheader("源数据（已转换为万元）")
    show_df = df.copy()
    show_df["补偿金额（万元）"] = show_df["补偿金额（万元）"].round(
        0 if tab_label.startswith("AGC") else 4)
    st.dataframe(show_df, use_container_width=True, height=460)
    st.download_button(
        "⬇️ 导出当前筛选数据 (CSV)",
        data=show_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"浙江辅助服务补偿_{tab_label[:6]}.csv", mime="text/csv")
