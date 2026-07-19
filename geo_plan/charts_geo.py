# -*- coding: utf-8 -*-
"""铭信 GEO · 苹果视觉 matplotlib 图表。

复用 business_plan/apple_style.py 主题。数据全部取自 outputs/geo_results.json
（由 scoring.py 真实计算），不在此处编造。对‘待密钥复测’引擎不绘制虚假分数，
仅以占位条 + 文字如实标注。

复现：python charts_geo.py  → figures/*.png
"""
from __future__ import annotations

import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
BP_DIR = os.path.join(os.path.dirname(BASE), "business_plan")
sys.path.insert(0, BP_DIR)

import apple_style as A  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import geo_data as G  # noqa: E402

FIG = G.FIG_DIR
RESULTS = os.path.join(G.OUT_DIR, "geo_results.json")


def _load():
    with open(RESULTS, "r", encoding="utf-8") as f:
        return json.load(f)


def chart_geo_index_by_engine(R):
    """各可实测引擎的总体 GEO 指数（含 90% CI 误差棒）+ 聚合；待密钥引擎如实标注。"""
    A.apply_apple_style()
    fig, ax = plt.subplots(figsize=(9.6, 5.8))
    fig.subplots_adjust(left=0.10, right=0.96, top=0.80, bottom=0.20)

    labels, vals, los, his = [], [], [], []
    for ek in R["meta"]["chat_engines"] + R["meta"]["search_engines"]:
        b = R["per_engine"].get(ek, {})
        if not b.get("available"):
            continue
        labels.append(b["label"])
        gi = b["overall"]["geo_index"]
        lo, hi = b["overall"]["ci90"]
        vals.append(gi); los.append(max(0, gi - lo)); his.append(max(0, hi - gi))
    # 聚合
    labels.append("对话引擎聚合")
    gi = R["aggregate"]["overall"]["geo_index"]
    lo, hi = R["aggregate"]["overall"]["ci90"]
    vals.append(gi); los.append(max(0, gi - lo)); his.append(max(0, hi - gi))

    x = np.arange(len(labels))
    colors = [A.BLUE] * (len(labels) - 1) + [A.INDIGO]
    ax.bar(x, vals, width=0.56, color=colors, zorder=3,
           yerr=[los, his], capsize=5,
           error_kw={"ecolor": A.INK_SOFT, "elinewidth": 1.2})
    for i, v in enumerate(vals):
        ax.text(i, v + max(his) * 0.12 + 0.6, f"{v:.1f}", ha="center", va="bottom",
                fontsize=10, fontweight="bold", color=A.INK)

    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_ylabel("GEO 指数（0–100，越高越好）")
    ax.set_ylim(0, max(12, max(vals) * 1.35 + 3))
    ax.grid(True, axis="y", color=A.GRID, lw=1.0); ax.set_axisbelow(True)
    n_pending = len(R["meta"]["pending_engines"])
    A.title_block(ax, "各 AI 引擎总体 GEO 指数（实测基线）",
                  f"误差棒=bootstrap 90% 置信区间；另有 {n_pending} 个引擎待密钥复测（不编造分数）")
    A.save(fig, os.path.join(FIG, "geo_index_by_engine.png"))


def chart_sov(R):
    """声量份额：铭信 vs 竞品（对话引擎聚合·总体）。"""
    A.apply_apple_style()
    sov = R["aggregate"]["competitor_sov"]
    rows = [r for r in sov["rows"] if r["mentions"] > 0 or r["is_self"]]
    rows = rows[:9]
    labels = [r["label"] for r in rows]
    vals = [r["sov"] * 100 for r in rows]
    colors = [A.BLUE if r["is_self"] else A.GRAY for r in rows]

    fig, ax = plt.subplots(figsize=(9.4, 6.0))
    fig.subplots_adjust(left=0.26, right=0.95, top=0.80, bottom=0.12)
    y = np.arange(len(labels))
    ax.barh(y, vals, color=colors, zorder=3)
    for i, v in enumerate(vals):
        ax.text(v + 0.6, i, f"{v:.1f}%", va="center", ha="left", fontsize=9.5,
                color=(A.BLUE if rows[i]["is_self"] else A.INK_SOFT),
                fontweight="bold" if rows[i]["is_self"] else "normal")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=10); ax.invert_yaxis()
    ax.set_xlabel("声量份额（被提及次数占比，%）")
    ax.set_xlim(0, max(vals) * 1.2 + 4 if vals else 10)
    ax.grid(True, axis="x", color=A.GRID, lw=1.0); ax.set_axisbelow(True)
    self_share = next((r["sov"] * 100 for r in sov["rows"] if r["is_self"]), 0.0)
    A.title_block(ax, "细分赛道声量份额：铭信 vs 竞品",
                  f"对话引擎聚合·全部查询；铭信当前声量份额约 {self_share:.1f}%（实测基线）")
    A.save(fig, os.path.join(FIG, "sov_competitors.png"))


def chart_funnel(R):
    """窄类目转化漏斗：回答数 → 被提及 → 被推荐 → 排名第一。"""
    A.apply_apple_style()
    fn = R["aggregate"]["narrow"]["funnel"]
    steps = ["AI 回答数", "被提及", "被推荐", "排名第一"]
    vals = [fn["responses"], fn["mentioned"], fn["recommended"], fn["ranked_top1"]]
    colors = A.BLUE_RAMP[:4]

    fig, ax = plt.subplots(figsize=(9.4, 5.4))
    fig.subplots_adjust(left=0.08, right=0.96, top=0.80, bottom=0.12)
    maxv = max(vals) if max(vals) > 0 else 1
    for i, (s, v) in enumerate(zip(steps, vals)):
        w = (v / maxv) if maxv else 0
        left = (1 - w) / 2
        ax.barh(len(steps) - 1 - i, w, left=left, height=0.62, color=colors[i], zorder=3)
        ax.text(0.5, len(steps) - 1 - i, f"{s}：{v}", ha="center", va="center",
                fontsize=11, color="white" if w > 0.18 else A.INK, fontweight="bold")
    ax.set_xlim(0, 1); ax.set_ylim(-0.5, len(steps) - 0.5)
    ax.axis("off")
    A.title_block(ax, "窄类目 GEO 转化漏斗（实测基线）",
                  "窄类目=全闪 NVMe-oF + KV Cache 分层存储加速（480B 签字级实测）；起点近零即如实呈现")
    A.save(fig, os.path.join(FIG, "mention_funnel.png"))


def chart_levers(R):
    """四大杠杆就绪度雷达（0–5，由自审清单 done/total 计算）。"""
    A.apply_apple_style()
    ls = R["lever_scores"]
    keys = ["L1", "L2", "L3", "L4"]
    names = [ls[k]["name"].split("（")[0] for k in keys]
    scores = [ls[k]["score5"] for k in keys]

    angles = np.linspace(0, 2 * np.pi, len(keys), endpoint=False).tolist()
    scores_c = scores + scores[:1]
    angles_c = angles + angles[:1]

    fig = plt.figure(figsize=(7.8, 6.6))
    fig.subplots_adjust(left=0.08, right=0.92, top=0.80, bottom=0.08)
    ax = fig.add_subplot(111, polar=True)
    ax.set_theta_offset(np.pi / 2); ax.set_theta_direction(-1)
    ax.set_ylim(0, 5)
    ax.plot(angles_c, scores_c, color=A.BLUE, linewidth=2.4, zorder=3)
    ax.fill(angles_c, scores_c, color=A.with_alpha(A.BLUE, 0.22), zorder=2)
    # 目标参考环（就绪度 4.0）
    tgt = [4.0] * len(keys) + [4.0]
    ax.plot(angles_c, tgt, color=A.ORANGE, linewidth=1.4, ls="--", zorder=2)
    ax.set_xticks(angles)
    ax.set_xticklabels([f"{k}\n{n}" for k, n in zip(keys, names)], fontsize=9.5)
    ax.set_yticks([1, 2, 3, 4, 5]); ax.set_yticklabels(["1", "2", "3", "4", "5"], fontsize=8)
    for ang, sc in zip(angles, scores):
        ax.text(ang, sc + 0.28, f"{sc:.1f}", ha="center", va="center",
                fontsize=10, fontweight="bold", color=A.BLUE)
    fig.text(0.08, 0.93, "GEO 四大杠杆就绪度（实事求是自审）", fontsize=18,
             fontweight="bold", color=A.INK)
    fig.text(0.08, 0.885, "蓝=当前就绪度；橙色虚线=阶段目标 4.0/5；分值=清单 done/total×5",
             fontsize=11, color=A.INK_SOFT)
    A.save(fig, os.path.join(FIG, "lever_radar.png"))


def chart_stage_targets(R):
    """分阶段 GEO 指数目标曲线（窄 vs 宽；T0 为实测）。"""
    A.apply_apple_style()
    st = R["stage_targets"]
    stages = st["stages"]
    narrow = st["narrow"]; broad = st["broad"]
    x = np.arange(len(stages))

    fig, ax = plt.subplots(figsize=(9.6, 5.6))
    fig.subplots_adjust(left=0.10, right=0.96, top=0.80, bottom=0.14)
    ax.plot(x, narrow, marker="o", color=A.BLUE, label="窄类目（争第一靶点）", zorder=3)
    ax.plot(x, broad, marker="s", color=A.TEAL, label="宽类目（可见度爬坡）", zorder=3)
    for xi, v in zip(x, narrow):
        ax.text(xi, v + 2.2, f"{v:.0f}", ha="center", va="bottom", fontsize=9.5,
                color=A.BLUE, fontweight="bold")
    for xi, v in zip(x, broad):
        ax.text(xi, v - 3.4, f"{v:.0f}", ha="center", va="top", fontsize=9.5,
                color=A.TEAL)
    ax.axhline(80, color=A.ORANGE, lw=1.2, ls="--", zorder=1)
    ax.text(len(stages) - 1, 81.5, "第一梯队阈值≈80", ha="right", va="bottom",
            fontsize=9, color=A.ORANGE)
    ax.set_xticks(x); ax.set_xticklabels(stages, fontsize=10)
    ax.set_ylabel("GEO 指数目标（0–100）")
    ax.set_ylim(0, 100)
    ax.grid(True, axis="y", color=A.GRID, lw=1.0); ax.set_axisbelow(True)
    A.title_block(ax, "分阶段可检验目标：GEO 指数路线图",
                  "T0 为实测基线；30/90/180/365 天为靶点（非名次承诺，见风险与边界）")
    ax.legend(loc="upper left", fontsize=10)
    A.save(fig, os.path.join(FIG, "stage_targets.png"))


def chart_landscape(R):
    """宽类目竞争格局：竞品被提及次数（可见度）条形，自家如实标注。"""
    A.apply_apple_style()
    sov = R["aggregate"]["broad"]["competitor_sov"]
    rows = sorted(sov["rows"], key=lambda r: -r["mentions"])
    rows = [r for r in rows if r["mentions"] > 0 or r["is_self"]][:9]
    labels = [r["label"] for r in rows]
    vals = [r["mentions"] for r in rows]
    colors = [A.BLUE if r["is_self"] else A.with_alpha(A.INDIGO, 0.7) for r in rows]

    fig, ax = plt.subplots(figsize=(9.4, 5.8))
    fig.subplots_adjust(left=0.24, right=0.95, top=0.80, bottom=0.12)
    y = np.arange(len(labels))
    ax.barh(y, vals, color=colors, zorder=3)
    for i, v in enumerate(vals):
        ax.text(v + 0.1, i, str(v), va="center", ha="left", fontsize=9.5,
                color=(A.BLUE if rows[i]["is_self"] else A.INK_SOFT),
                fontweight="bold" if rows[i]["is_self"] else "normal")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=10); ax.invert_yaxis()
    ax.set_xlabel("宽类目查询中被提及次数（可见度）")
    ax.set_xlim(0, max(vals) * 1.2 + 1 if vals else 5)
    ax.grid(True, axis="x", color=A.GRID, lw=1.0); ax.set_axisbelow(True)
    A.title_block(ax, "宽类目竞争格局：当前 AI 回答可见度",
                  "对话引擎聚合·宽类目查询；铭信起点近零，巨头主导（实测）")
    A.save(fig, os.path.join(FIG, "landscape.png"))


def build_all():
    R = _load()
    chart_geo_index_by_engine(R)
    chart_sov(R)
    chart_funnel(R)
    chart_levers(R)
    chart_stage_targets(R)
    chart_landscape(R)
    print(f"Charts saved to {FIG}")


if __name__ == "__main__":
    build_all()
