# -*- coding: utf-8 -*-
"""共享数据加载模块：AGC 月度补偿 + 储能调频补偿收入（C/D 列 full outer join）
单位统一转换为万元。
"""
import glob
import os
import re
from collections import defaultdict

import openpyxl

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGC_XLSX = os.path.join(BASE_DIR, "AGC:二次调频月度补偿", "浙江AGC补偿月份统计.xlsx")
STORAGE_DIR = os.path.join(BASE_DIR, "储能调频补偿收入")

# 模拟结算 / 正式结算的分界
SIM_MONTHS = ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06"]

ALL_MONTHS = [
    "2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
    "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
    "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06",
    "2026-07", "2026-08", "2026-09",
]


def _to_wan(v):
    """元 -> 万元"""
    if v is None:
        return None
    try:
        return float(v) / 10000.0
    except (TypeError, ValueError):
        return None


def load_agc():
    """浙江 AGC 月度补偿：返回 [(month, 万元, 结算类型)]，月份连续覆盖 2025-01 ~ 2026-09。"""
    wb = openpyxl.load_workbook(AGC_XLSX, data_only=True)
    ws = wb["Sheet1"]
    out = {}
    settle = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r[0] is None:
            continue
        dt = r[0]
        month = f"{dt.year}-{dt.month:02d}"
        out[month] = _to_wan(r[1])
        settle[month] = "模拟结算" if month in SIM_MONTHS else "正式结算"
    # 补齐缺失月份为 None（无数据）
    rows = []
    for m in ALL_MONTHS:
        rows.append((m, out.get(m), settle.get(m, "正式结算")))
    return rows


def load_storage():
    """储能调频补偿收入：取所有月度 excel 的 C(并网主体) / D(有偿一次调频补偿) 列。

    - 按站点名归并（'XX储能站' 与 'XX储能' 视为同一站点，去掉末尾'站/厂'差异归并）
    - 类似 SQL full outer join：站点并集 x 月份并集，缺失即 None
    - 2026-07 为考核文件，无补偿数据，该月整体缺失
    返回 (stations, matrix):
      stations: 按总收入降序的站名列表
      matrix: {station: {month: 万元或None}}
    """
    sto_types = {"电化学储能", "储能", "抽蓄", "抽水蓄能"}
    data = defaultdict(dict)  # 站名(归并后) -> {month: 万元}
    for f in sorted(glob.glob(os.path.join(STORAGE_DIR, "*.xlsx"))):
        base = os.path.basename(f)
        if "考核" in base or base.startswith("~$"):
            continue  # 考核文件 D 列非补偿费用，跳过
        m = re.search(r"(\d{4})年(\d{1,2})月", base)
        if not m:
            continue
        month = f"{m.group(1)}-{int(m.group(2)):02d}"
        wb = openpyxl.load_workbook(f, data_only=True)
        ws = wb["工作表"]
        for r in ws.iter_rows(min_row=4, values_only=True):
            name = str(r[2]).strip() if r[2] else ""
            if not name or name == "本月汇总":
                continue
            typ = str(r[1]).strip() if r[1] else ""
            if typ not in sto_types:
                continue
            key = name[:-1] if name.endswith("站") else name
            v = _to_wan(r[3])
            if v is None:
                continue
            data[key][month] = data[key].get(month, 0.0) + v
    stations = sorted(data, key=lambda s: (-sum(data[s].values()), s))
    matrix = {s: {m: data[s].get(m) for m in ALL_MONTHS} for s in stations}
    return stations, matrix


def load_storage_all():
    """全部并网主体（C列）x D列（有偿一次调频补偿），full outer join。

    - 站点名归并'站'后缀别名（'XX储能站' 与 'XX储能' 合并）
    - 保留任意月份 D>0 的主体（D 恒为 0 的主体无收入意义）
    - 2026-07 为考核文件，无补偿数据，该月整体缺失
    返回 (stations, matrix):
      stations: 按总收入降序的主体列表
      matrix: {station: {month: 万元或None}}
    """
    data = defaultdict(dict)
    for f in sorted(glob.glob(os.path.join(STORAGE_DIR, "*.xlsx"))):
        base = os.path.basename(f)
        if "考核" in base or base.startswith("~$"):
            continue
        m = re.search(r"(\d{4})年(\d{1,2})月", base)
        if not m:
            continue
        month = f"{m.group(1)}-{int(m.group(2)):02d}"
        wb = openpyxl.load_workbook(f, data_only=True)
        for r in wb["工作表"].iter_rows(min_row=4, values_only=True):
            name = str(r[2]).strip() if r[2] else ""
            if not name or name == "本月汇总" or not r[0]:
                continue
            key = name[:-1] if name.endswith("站") else name
            v = r[3]
            if v is None:
                continue
            try:
                v = float(v)
            except (TypeError, ValueError):
                continue
            if v != 0:
                data[key][month] = data[key].get(month, 0.0) + v
    stations = sorted(data, key=lambda s: (-sum(data[s].values()), s))
    matrix = {s: {m: (data[s].get(m, 0.0) / 10000.0 or None) for m in ALL_MONTHS}
              for s in stations}
    return stations, matrix


if __name__ == "__main__":
    agc = load_agc()
    print("AGC 月数:", len(agc), "样例:", agc[:3], agc[-2:])
    st, mx = load_storage_all()
    print("主体数:", len(st))
    print("TOP5:", [(s, round(sum(v for v in mx[s].values() if v), 4)) for s in st[:5]])
