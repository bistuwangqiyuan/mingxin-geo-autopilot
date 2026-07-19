# -*- coding: utf-8 -*-
"""铭信 GEO+SEO 提升闭环 · 苹果风格复现图（matplotlib → PNG）。

读取：outputs/loop_results.json、outputs/gvi_compare.json、
      geo_plan/outputs/geo_projection.json
产出：outputs/figures/*.png（全部由数据计算，无手绘、可复现）。

复现：python charts.py
"""
from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "outputs")
FIG = os.path.join(OUT, "figures")
GEO = os.path.join(os.path.dirname(BASE), "geo_plan")

APPLE_BLUE = "#0071E3"
APPLE_INDIGO = "#5E5CE6"
APPLE_GREEN = "#34C759"
APPLE_ORANGE = "#FF9F0A"
APPLE_PINK = "#FF375F"
APPLE_DARK = "#1D1D1F"
APPLE_GRAY = "#86868B"
GRID = "#E8E8ED"
ACCENT = [APPLE_BLUE, APPLE_GREEN, APPLE_ORANGE, APPLE_PINK, APPLE_INDIGO, "#64D2FF"]


def _setup():
    plt.rcParams.update({
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "Segoe UI", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
        "axes.edgecolor": GRID, "axes.labelcolor": APPLE_DARK,
        "xtick.color": APPLE_DARK, "ytick.color": APPLE_DARK, "text.color": APPLE_DARK,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
    })


def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def cri_trajectory(loop):
    rounds = loop["rounds"]
    xs = [r["round"] for r in rounds]
    ys = [r["cri"] for r in rounds]
    fig, ax = plt.subplots(figsize=(9, 4.6), dpi=170)
    ax.plot(xs, ys, "-o", color=APPLE_BLUE, lw=2.4, ms=6, zorder=3)
    ax.fill_between(xs, [loop["baseline_cri"]] * len(xs), ys, color=APPLE_BLUE, alpha=0.08, zorder=1)
    for r in rounds:
        if r["round"] == 0 or r["delta"] != 0:
            ax.annotate(f'{r["cri"]:.1f}', (r["round"], r["cri"]),
                        textcoords="offset points", xytext=(0, 9),
                        ha="center", fontsize=8.5, color=APPLE_DARK)
    ax.axhline(loop["ceiling_cri"], color=APPLE_GRAY, ls="--", lw=1, zorder=2)
    ax.text(xs[-1], loop["ceiling_cri"] + 0.6, f'收敛上限 {loop["ceiling_cri"]:.1f}',
            ha="right", va="bottom", fontsize=8.5, color=APPLE_GRAY)
    ax.set_xlabel("优化轮次（0=基线）")
    ax.set_ylabel("CRI（站内 GEO+SEO 就绪度，0–100）")
    ax.set_title("CRI 逐轮提升轨迹（确定性、可复现）", fontsize=13, fontweight="bold")
    ax.set_xticks(xs)
    ax.set_ylim(min(ys) - 6, 102)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "cri_trajectory.png"))
    plt.close(fig)


def lever_contribution(loop):
    rounds = [r for r in loop["rounds"] if r["round"] >= 1 and r["lever_enabled"]]
    names = [r["lever_name"] for r in rounds]
    deltas = [r["delta"] for r in rounds]
    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=170)
    colors = [ACCENT[i % len(ACCENT)] for i in range(len(names))]
    bars = ax.barh(range(len(names))[::-1], deltas, color=colors, zorder=3)
    ax.set_yticks(range(len(names))[::-1])
    ax.set_yticklabels(names, fontsize=9.5)
    for i, (b, d) in enumerate(zip(bars, deltas)):
        ax.text(d + 0.06, b.get_y() + b.get_height() / 2, f"+{d:.2f}",
                va="center", fontsize=9, color=APPLE_DARK)
    ax.set_xlabel("该杠杆组带来的 CRI 增量（分）")
    ax.set_title("各杠杆组的边际贡献（逐轮 Δ）", fontsize=13, fontweight="bold")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, max(deltas) * 1.25)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "lever_contribution.png"))
    plt.close(fig)


def pillar_radar(loop):
    base = loop["rounds"][0]["pillars"]
    final = loop["rounds"][-1]["pillars"]
    labels = ["A 技术SEO", "B AI抓取", "C 结构化", "D 答案优先", "E 实体一致"]
    keys = ["A", "B", "C", "D", "E"]
    ang = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    ang += ang[:1]
    bvec = [base[k] for k in keys] + [base[keys[0]]]
    fvec = [final[k] for k in keys] + [final[keys[0]]]
    fig, ax = plt.subplots(figsize=(6.2, 6.2), dpi=170, subplot_kw=dict(polar=True))
    ax.plot(ang, bvec, color=APPLE_GRAY, lw=2, label="基线")
    ax.fill(ang, bvec, color=APPLE_GRAY, alpha=0.12)
    ax.plot(ang, fvec, color=APPLE_BLUE, lw=2.4, label="最终")
    ax.fill(ang, fvec, color=APPLE_BLUE, alpha=0.18)
    ax.set_xticks(ang[:-1])
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.50", "0.75", "1.0"], fontsize=8, color=APPLE_GRAY)
    ax.set_title("五支柱画像：基线 → 最终（0–1）", fontsize=12, fontweight="bold", pad=20)
    ax.legend(loc="lower right", bbox_to_anchor=(1.13, -0.05), frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "pillar_radar.png"))
    plt.close(fig)


def pillar_delta(loop):
    base = loop["rounds"][0]["pillars"]
    final = loop["rounds"][-1]["pillars"]
    keys = ["A", "B", "C", "D", "E"]
    labels = ["A 技术SEO", "B AI抓取", "C 结构化", "D 答案优先", "E 实体一致"]
    x = np.arange(len(keys))
    fig, ax = plt.subplots(figsize=(9, 4.4), dpi=170)
    w = 0.38
    ax.bar(x - w / 2, [base[k] for k in keys], w, label="基线", color=APPLE_GRAY, zorder=3)
    ax.bar(x + w / 2, [final[k] for k in keys], w, label="最终", color=APPLE_BLUE, zorder=3)
    for i, k in enumerate(keys):
        ax.text(i + w / 2, final[k] + 0.015, f"{final[k]:.2f}", ha="center", fontsize=8.5)
        ax.text(i - w / 2, base[k] + 0.015, f"{base[k]:.2f}", ha="center", fontsize=8.5, color=APPLE_GRAY)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_ylabel("支柱得分（0–1）")
    ax.set_ylim(0, 1.12)
    ax.set_title("五支柱：基线 vs 最终", fontsize=13, fontweight="bold")
    ax.legend(frameon=False, fontsize=9, ncol=2)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "pillar_delta.png"))
    plt.close(fig)


def gvi_compare_chart():
    p = os.path.join(OUT, "gvi_compare.json")
    if not os.path.exists(p):
        return False
    c = _load(p)
    models = c["models"]
    start = [c["start"]["by_model"].get(m, 0) for m in models]
    end = [c["end"]["by_model"].get(m, 0) for m in models]
    x = np.arange(len(models))
    fig, ax = plt.subplots(figsize=(9, 4.4), dpi=170)
    w = 0.38
    ax.bar(x - w / 2, start, w, label=f'起点 GVI 总体 {c["start"]["gvi"]}', color=APPLE_GRAY, zorder=3)
    ax.bar(x + w / 2, end, w, label=f'终点 GVI 总体 {c["end"]["gvi"]}', color=APPLE_BLUE, zorder=3)
    for i in range(len(models)):
        ax.text(i - w / 2, start[i] + 0.06, f"{start[i]:.1f}", ha="center", fontsize=8, color=APPLE_GRAY)
        ax.text(i + w / 2, end[i] + 0.06, f"{end[i]:.1f}", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=9.5)
    ax.set_ylabel("GVI（0–100，真实 API 采样）")
    ax.set_title("真实 GEO 可见性指数 GVI：起点 vs 终点（同口径真测）", fontsize=12.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=9)
    ax.grid(axis="x", visible=False)
    top = max(start + end + [1]) * 1.35
    ax.set_ylim(0, top)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "gvi_compare.png"))
    plt.close(fig)
    return True


def projection_chart():
    p = os.path.join(GEO, "outputs", "geo_projection.json")
    if not os.path.exists(p):
        return False
    proj = _load(p)
    phases = proj["phases"]
    order = list(phases.keys())
    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=170)
    for ti, t in enumerate(["T1", "T2", "T3"]):
        p50 = [phases[ph]["tiers"][t]["mention_p50"] * 100 for ph in order]
        p10 = [phases[ph]["tiers"][t]["mention_p10"] * 100 for ph in order]
        p90 = [phases[ph]["tiers"][t]["mention_p90"] * 100 for ph in order]
        xs = range(len(order))
        ax.plot(xs, p50, "-o", color=ACCENT[ti], lw=2.2, ms=5, label=f"{t} 中位(P50)")
        ax.fill_between(xs, p10, p90, color=ACCENT[ti], alpha=0.10)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([ph.split("_")[0] for ph in order], fontsize=9)
    ax.set_ylabel("品牌提及率（%）")
    ax.set_title("GEO 提及率提升预测 P10–P90（规划区间，非承诺）", fontsize=12.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=8.5, ncol=3)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "geo_projection.png"))
    plt.close(fig)
    return True


def cri_v2_trajectory():
    """第二阶段 CRI v2 轨迹（轮次 10 基线 → 15，g9–g13）。"""
    p = os.path.join(OUT, "loop_results_v2.json")
    if not os.path.exists(p):
        return False
    loop = _load(p)
    rounds = loop["rounds"]
    xs = [r["round"] for r in rounds]
    ys = [r["cri"] for r in rounds]
    fig, ax = plt.subplots(figsize=(9, 4.6), dpi=170)
    ax.plot(xs, ys, "-o", color=APPLE_INDIGO, lw=2.4, ms=6, zorder=3)
    ax.fill_between(xs, [ys[0]] * len(xs), ys, color=APPLE_INDIGO, alpha=0.08, zorder=1)
    for r in rounds:
        ax.annotate(f'{r["cri"]:.1f}', (r["round"], r["cri"]),
                    textcoords="offset points", xytext=(0, 9), ha="center",
                    fontsize=8.5, color=APPLE_DARK)
    ax.axhline(97.9, color=APPLE_PINK, ls="--", lw=1, zorder=2)
    ax.text(xs[0], 97.9 + 0.25, "第一阶段 v1 上限 97.9", ha="left", va="bottom",
            fontsize=8.5, color=APPLE_PINK)
    ax.set_xlabel("优化轮次（10=阶段基线 g1–g8）")
    ax.set_ylabel("CRI v2（更严格口径，0–100）")
    ax.set_title("CRI v2 第 11–15 轮提升轨迹（g9–g13，确定性可复现）",
                 fontsize=13, fontweight="bold")
    ax.set_xticks(xs)
    ax.set_ylim(min(ys) - 4, 101)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "cri_v2_trajectory.png"))
    plt.close(fig)
    return True


def lever_contribution_v2():
    p = os.path.join(OUT, "loop_results_v2.json")
    if not os.path.exists(p):
        return False
    loop = _load(p)
    rounds = [r for r in loop["rounds"] if r.get("lever_enabled")]
    names = [r["lever_name"] for r in rounds]
    deltas = [r["delta"] for r in rounds]
    fig, ax = plt.subplots(figsize=(9, 4.4), dpi=170)
    colors = [ACCENT[i % len(ACCENT)] for i in range(len(names))]
    bars = ax.barh(range(len(names))[::-1], deltas, color=colors, zorder=3)
    ax.set_yticks(range(len(names))[::-1])
    ax.set_yticklabels(names, fontsize=9.5)
    for b, d in zip(bars, deltas):
        ax.text(d + 0.05, b.get_y() + b.get_height() / 2, f"+{d:.2f}",
                va="center", fontsize=9, color=APPLE_DARK)
    ax.set_xlabel("该新杠杆带来的 CRI v2 增量（分）")
    ax.set_title("新增 5 杠杆（g9–g13）的边际贡献", fontsize=13, fontweight="bold")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, max(deltas) * 1.25)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "lever_contribution_v2.png"))
    plt.close(fig)
    return True


def live_lab_chart():
    """线上 mingxinstorage.xyz 实验室性能指标（Playwright/CDP 真测，按审计主机网络）。"""
    p = os.path.join(OUT, "lighthouse.json")
    if not os.path.exists(p):
        return False
    data = _load(p)
    labs = [r for r in data.get("results", []) if r.get("ok") and r.get("method") == "lab"]
    if not labs:
        return False
    urls = [r["url"].replace("https://mingxinstorage.xyz", "") for r in labs]
    metrics = [("FCP", "fcp"), ("LCP", "lcp"), ("Load", "load")]
    x = np.arange(len(urls))
    w = 0.26
    fig, ax = plt.subplots(figsize=(9, 4.4), dpi=170)
    for i, (lbl, key) in enumerate(metrics):
        vals = [round((r["metrics"].get(key) or 0) / 1000.0, 2) for r in labs]
        bars = ax.bar(x + (i - 1) * w, vals, w, label=lbl, color=ACCENT[i], zorder=3)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.05, f"{v:.1f}s",
                    ha="center", fontsize=7.5)
    ax.set_xticks(x)
    ax.set_xticklabels(urls, fontsize=9)
    ax.set_ylabel("秒（越低越好）")
    ax.set_title("线上 mingxinstorage.xyz 实验室性能真测（Playwright/CDP · 审计主机网络）",
                 fontsize=12, fontweight="bold")
    ax.legend(frameon=False, fontsize=9, ncol=3)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "live_lab.png"))
    plt.close(fig)
    return True


def main():
    _setup()
    os.makedirs(FIG, exist_ok=True)
    loop = _load(os.path.join(OUT, "loop_results.json"))
    cri_trajectory(loop)
    lever_contribution(loop)
    pillar_radar(loop)
    pillar_delta(loop)
    g = gvi_compare_chart()
    pr = projection_chart()
    made = ["cri_trajectory", "lever_contribution", "pillar_radar", "pillar_delta"]
    if g:
        made.append("gvi_compare")
    if pr:
        made.append("geo_projection")
    if cri_v2_trajectory():
        made.append("cri_v2_trajectory")
    if lever_contribution_v2():
        made.append("lever_contribution_v2")
    if live_lab_chart():
        made.append("live_lab")
    print("图表已生成：", ", ".join(made), "->", FIG)


if __name__ == "__main__":
    main()
