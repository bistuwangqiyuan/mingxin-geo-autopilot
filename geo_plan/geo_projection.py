# -*- coding: utf-8 -*-
"""铭信 GEO 提升预测（geo_projection.py）。

目标：在"实事求是、避免乐观谬误"的前提下，给出各阶段、各类目下铭信
被 AI 大模型"提及/首位提及"概率的保守预测区间（P10/P50/P90）与敏感性分析。

建模口径（公开、可复现、可质疑）：
  我们不能在"字面为 0 的基线"上做乘法提升——GEO 的第一步是先让品牌"可被检索、
  可被解析"，从而产生一个很小的潜在被提及先验 seed。随后每启用一个 GEO 杠杆，
  按其赔率乘子（odds-ratio）在 logit 空间叠加，并以类目可达上限 ceiling 封顶：

      q = p / ceiling ∈ (0,1)
      logit(q_phase) = logit(seed/ceiling) + Σ_lever log(OR_lever) + offsite_logor
      p_phase = ceiling × sigmoid( logit(q_phase) )

  - seed：建成"可被抓取+结构化的事实页"后的潜在被提及先验（每类目一个，假设值）。
  - ceiling：类目可达上限（geo_config.P_CEILING），防止"全模型必第一"。
  - OR_lever：geo_config.LEVERS 的 P10/P50/P90 乘子（取自 GEO 公开研究的下沿，保守）。
  - offsite：站外按"该阶段覆盖的高权重信源平台数"做带衰减的叠加（避免指数爆炸）。
  - P10 用所有杠杆的 P10 乘子、P90 用 P90，给出保守—乐观区间。

  所有 seed/ceiling/OR 均为"规划假设"，本脚本同时输出对 seed 的敏感性。
  复现：python geo_projection.py
"""
from __future__ import annotations

import json
import math
import os

import geo_config as C

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "outputs")
FIG = os.path.join(OUT, "figures")

# 建成事实页后的潜在被提及先验（假设，按类目；窄类目更易被点名）
SEED = {"T1": 0.05, "T2": 0.025, "T3": 0.012}

# 各阶段启用的站内杠杆
PHASE_LEVERS = {
    "P0_基线": [],
    "P1_地基": ["crawler_access", "structured_data", "answer_first", "llms_txt", "entity_consistency"],
    "P2_T1夺冠": ["crawler_access", "structured_data", "answer_first", "llms_txt", "entity_consistency"],
    "P3_T2梯队": ["crawler_access", "structured_data", "answer_first", "llms_txt", "entity_consistency"],
    "P4_稳固出海": ["crawler_access", "structured_data", "answer_first", "llms_txt", "entity_consistency"],
}

# 各阶段覆盖的站外信源平台（决定 offsite 叠加；权重取自 SOURCE_PREFERENCE 的归属模型）
PHASE_OFFSITE = {
    "P0_基线": [],
    "P1_地基": [],
    "P2_T1夺冠": ["CSDN", "知乎技术区", "GitHub/GitCode", "技术白皮书", "阿里云开发者社区", "语雀公开知识库"],
    "P3_T2梯队": ["CSDN", "知乎技术区", "GitHub/GitCode", "技术白皮书", "阿里云开发者社区", "语雀公开知识库",
                "百度百科", "百家号(蓝V)", "微信公众号", "搜狐号", "网易号", "今日头条"],
    "P4_稳固出海": ["CSDN", "知乎技术区", "GitHub/GitCode", "技术白皮书", "阿里云开发者社区", "语雀公开知识库",
                "百度百科", "百家号(蓝V)", "微信公众号", "搜狐号", "网易号", "今日头条",
                "权威媒体", "政府/教育网站(.gov/.edu)"],
}

PHASE_ORDER = ["P0_基线", "P1_地基", "P2_T1夺冠", "P3_T2梯队", "P4_稳固出海"]
PHASE_WEEKS = {"P0_基线": "第0周", "P1_地基": "第1–2周", "P2_T1夺冠": "第3–6周",
               "P3_T2梯队": "第7–14周", "P4_稳固出海": "第15周起"}


def logit(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def sigmoid(x):
    return 1 / (1 + math.exp(-x))


def _platform_weight(platform):
    """某信源平台的综合权重 = 偏好它的模型权重之和（带归一），用于 offsite 叠加。"""
    w = 0.0
    for vendor, cfg in C.SOURCE_PREFERENCE.items():
        if platform in cfg["primary"]:
            w += cfg["weight"] * 1.0
        elif platform in cfg["secondary"]:
            w += cfg["weight"] * 0.5
    return w


def offsite_logor(platforms, band):
    """站外覆盖的 log-OR 叠加，按平台综合权重排序后做几何衰减，避免爆炸。"""
    lev = C.LEVERS["offsite_source"][band]  # 单平台 OR
    base_logor = math.log(lev)
    contribs = sorted((_platform_weight(p) for p in platforms), reverse=True)
    total = 0.0
    for i, w in enumerate(contribs):
        decay = 0.75 ** i            # 第 i 个平台的边际递减
        total += base_logor * min(w, 1.0) * decay
    return total


def project_phase(phase, tier, band):
    """返回某阶段、某类目、某分位（band）下的被提及概率。"""
    ceiling = C.P_CEILING[tier]
    seed = SEED[tier]
    x = logit(seed / ceiling)
    for lev in PHASE_LEVERS[phase]:
        x += math.log(C.LEVERS[lev][band])
    x += offsite_logor(PHASE_OFFSITE[phase], band)
    q = sigmoid(x)
    return ceiling * q


def first_mention_rate(mention_p, tier):
    """由被提及概率派生"首位提及率"（保守：窄类目转化高，宽类目低）。"""
    conv = {"T1": 0.72, "T2": 0.5, "T3": 0.32}[tier]
    return mention_p * conv


def run_projection():
    res = {"assumptions": {"seed": SEED, "ceiling": C.P_CEILING,
                           "levers": C.LEVERS, "note": "全部为规划假设，非承诺；区间 P10/P90 取杠杆乘子下/上沿。"},
           "phases": {}}
    for phase in PHASE_ORDER:
        res["phases"][phase] = {"weeks": PHASE_WEEKS[phase],
                                "site_levers": PHASE_LEVERS[phase],
                                "offsite_platforms": PHASE_OFFSITE[phase], "tiers": {}}
        for tier in ("T1", "T2", "T3"):
            p10 = project_phase(phase, tier, "p10")
            p50 = project_phase(phase, tier, "p50")
            p90 = project_phase(phase, tier, "p90")
            res["phases"][phase]["tiers"][tier] = {
                "mention_p10": round(p10, 4), "mention_p50": round(p50, 4), "mention_p90": round(p90, 4),
                "first_mention_p50": round(first_mention_rate(p50, tier), 4),
                "ceiling": C.P_CEILING[tier],
            }
    return res


def tornado_T1():
    """对 T1 终态(P4)做单杠杆敏感性：逐个移除某杠杆看 P50 提及率跌多少。"""
    tier = "T1"
    full = project_phase("P4_稳固出海", tier, "p50")
    rows = []
    # 站内杠杆
    for lev in PHASE_LEVERS["P4_稳固出海"]:
        ceiling = C.P_CEILING[tier]
        x = logit(SEED[tier] / ceiling)
        for l2 in PHASE_LEVERS["P4_稳固出海"]:
            if l2 != lev:
                x += math.log(C.LEVERS[l2]["p50"])
        x += offsite_logor(PHASE_OFFSITE["P4_稳固出海"], "p50")
        p_wo = ceiling * sigmoid(x)
        rows.append({"lever": C.LEVERS[lev]["name"], "drop": round(full - p_wo, 4)})
    # 站外整体
    ceiling = C.P_CEILING[tier]
    x = logit(SEED[tier] / ceiling)
    for l2 in PHASE_LEVERS["P4_稳固出海"]:
        x += math.log(C.LEVERS[l2]["p50"])
    p_wo = ceiling * sigmoid(x)
    rows.append({"lever": "站外多信源覆盖(全部)", "drop": round(full - p_wo, 4)})
    rows.sort(key=lambda r: -r["drop"])
    return {"full_p50": round(full, 4), "rows": rows}


def seed_sensitivity():
    """对 seed 先验做 ±50% 敏感性（看 T1 终态 P50 提及率如何变化）。"""
    out = []
    base = SEED["T1"]
    for f in (0.5, 0.75, 1.0, 1.25, 1.5):
        SEED["T1"] = base * f
        out.append({"seed_factor": f, "seed": round(SEED["T1"], 4),
                    "T1_P4_mention_p50": round(project_phase("P4_稳固出海", "T1", "p50"), 4)})
    SEED["T1"] = base
    return out


def make_figures(res, tornado, seedsens):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "Segoe UI", "DejaVu Sans"],
        "axes.unicode_minus": False, "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white", "axes.edgecolor": "#D2D2D7", "grid.color": "#E8E8ED",
        "axes.grid": True, "grid.linewidth": 0.8, "text.color": "#1D1D1F",
        "axes.labelcolor": "#1D1D1F", "xtick.color": "#1D1D1F", "ytick.color": "#1D1D1F",
    })
    os.makedirs(FIG, exist_ok=True)
    blue, green, orange = "#0071E3", "#34C759", "#FF9F0A"
    colors = {"T1": blue, "T2": green, "T3": orange}

    # 1. 阶段轨迹（各类目 P50 + P10–P90 区间带）
    fig, ax = plt.subplots(figsize=(8.6, 4.6), dpi=160)
    xs = list(range(len(PHASE_ORDER)))
    for tier in ("T1", "T2", "T3"):
        p50 = [res["phases"][ph]["tiers"][tier]["mention_p50"] * 100 for ph in PHASE_ORDER]
        p10 = [res["phases"][ph]["tiers"][tier]["mention_p10"] * 100 for ph in PHASE_ORDER]
        p90 = [res["phases"][ph]["tiers"][tier]["mention_p90"] * 100 for ph in PHASE_ORDER]
        ax.plot(xs, p50, "-o", color=colors[tier], linewidth=2, label=f"{tier} {C.TIERS[tier].split('（')[0]}")
        ax.fill_between(xs, p10, p90, color=colors[tier], alpha=0.13)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{ph.split('_')[1]}\n{PHASE_WEEKS[ph]}" for ph in PHASE_ORDER], fontsize=9)
    ax.set_ylabel("被提及概率（%）")
    ax.set_title("分阶段 · 各类目被提及概率预测（P50 线，P10–P90 区间带）", fontsize=12.5, fontweight="bold")
    ax.legend(fontsize=8.5, frameon=False)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "projection_trajectory.png"))
    plt.close(fig)

    # 2. T1 终态 tornado
    rows = tornado["rows"]
    names = [r["lever"] for r in rows][::-1]
    drops = [r["drop"] * 100 for r in rows][::-1]
    fig, ax = plt.subplots(figsize=(8.4, 4.4), dpi=160)
    ax.barh(range(len(names)), drops, color=blue, zorder=3)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel("移除该杠杆后 T1 终态被提及率下降（百分点）")
    ax.set_title("T1 终态杠杆敏感性（Tornado）", fontsize=12.5, fontweight="bold")
    for i, v in enumerate(drops):
        ax.text(v + 0.1, i, f"{v:.1f}", va="center", fontsize=8, color="#1D1D1F")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "projection_tornado.png"))
    plt.close(fig)

    # 3. seed 敏感性
    fig, ax = plt.subplots(figsize=(7.4, 4), dpi=160)
    xs2 = [s["seed_factor"] for s in seedsens]
    ys2 = [s["T1_P4_mention_p50"] * 100 for s in seedsens]
    ax.plot(xs2, ys2, "-o", color=green, linewidth=2)
    ax.set_xlabel("seed 先验缩放系数（×）")
    ax.set_ylabel("T1 终态被提及率 P50（%）")
    ax.set_title("seed 先验敏感性（±50%）", fontsize=12.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "projection_seed_sensitivity.png"))
    plt.close(fig)


def main():
    res = run_projection()
    tornado = tornado_T1()
    seedsens = seed_sensitivity()
    res["tornado_T1"] = tornado
    res["seed_sensitivity_T1"] = seedsens
    with open(os.path.join(OUT, "geo_projection.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    make_figures(res, tornado, seedsens)
    print("提升预测完成（保守区间）：")
    for ph in PHASE_ORDER:
        t1 = res["phases"][ph]["tiers"]["T1"]
        print(f"  {ph:12s} {PHASE_WEEKS[ph]:8s} T1 被提及 P50={t1['mention_p50']*100:5.1f}%  "
              f"(P10={t1['mention_p10']*100:.1f}% ~ P90={t1['mention_p90']*100:.1f}%)  "
              f"首位提及P50={t1['first_mention_p50']*100:.1f}%")
    print("  Tornado 头部：", [r["lever"] for r in tornado["rows"][:3]])
    print("  数据 -> outputs/geo_projection.json  图 -> outputs/figures/")


if __name__ == "__main__":
    main()
