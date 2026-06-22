# -*- coding: utf-8 -*-
"""中科存储 GEO Autopilot · 历史趋势看板（trend.py）。

读取 history/snapshot_*.json，产出苹果风趋势图（GVI / 提及率 / 信源覆盖 / 收录页数）。
单点也能画（首日）；缺失值跳过，绝不插值臆造。
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import paths  # noqa: E402
import metrics as M  # noqa: E402

plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Segoe UI", "DejaVu Sans"],
    "axes.unicode_minus": False, "figure.facecolor": "white", "axes.facecolor": "white",
    "savefig.facecolor": "white", "axes.edgecolor": "#D2D2D7", "grid.color": "#E8E8ED",
    "axes.grid": True, "grid.linewidth": 0.8, "text.color": "#1D1D1F",
    "axes.labelcolor": "#1D1D1F", "xtick.color": "#1D1D1F", "ytick.color": "#1D1D1F",
})

BLUE, GREEN, ORANGE = "#0071E3", "#34C759", "#FF9F0A"


def _series(hist, key):
    xs, ys = [], []
    for h in hist:
        v = h.get(key)
        if v is not None:
            xs.append(h["date"][5:])  # MM-DD
            ys.append(v)
    return xs, ys


def make_figures():
    paths.ensure_dirs()
    hist = M.load_history()
    out = []
    if not hist:
        return out

    # 1. GVI 趋势
    xs, ys = _series(hist, "gvi")
    if xs:
        fig, ax = plt.subplots(figsize=(8.4, 3.8), dpi=160)
        ax.plot(xs, ys, "-o", color=BLUE, lw=2.2, ms=6, zorder=3)
        for x, y in zip(xs, ys):
            ax.annotate(f"{y:.2f}", (x, y), textcoords="offset points",
                        xytext=(0, 8), ha="center", fontsize=8, color="#1D1D1F")
        ax.set_title("总体 GVI 趋势（0–100，真实重测）", fontsize=12.5, fontweight="bold")
        ax.set_ylabel("GVI")
        ax.set_ylim(0, max(12, max(ys) * 1.3))
        ax.grid(axis="x", visible=False)
        fig.tight_layout()
        p = os.path.join(paths.FIGURES, "trend_gvi.png")
        fig.savefig(p)
        plt.close(fig)
        out.append(p)

    # 2. 提及率 + 推荐类提及率
    xs, ys = _series(hist, "mention_rate")
    xs2, ys2 = _series(hist, "recommendation_mention")
    if xs:
        fig, ax = plt.subplots(figsize=(8.4, 3.8), dpi=160)
        ax.plot(xs, [v * 100 for v in ys], "-o", color=BLUE, lw=2.2, ms=6, label="品牌被提及率", zorder=3)
        if xs2:
            ax.plot(xs2, [v * 100 for v in ys2], "-o", color=ORANGE, lw=2.0, ms=5,
                    label="开放式推荐类被提及率", zorder=3)
        ax.set_title("被提及率趋势（%）", fontsize=12.5, fontweight="bold")
        ax.set_ylabel("%")
        ax.legend(fontsize=9, frameon=False)
        ax.grid(axis="x", visible=False)
        fig.tight_layout()
        p = os.path.join(paths.FIGURES, "trend_mention.png")
        fig.savefig(p)
        plt.close(fig)
        out.append(p)

    # 3. 信源覆盖（DeepSeek/通义）
    ds_x, ds_y, ty_y = [], [], []
    for h in hist:
        cov = h.get("coverage", {})
        if cov.get("DeepSeek") is not None:
            ds_x.append(h["date"][5:])
            ds_y.append((cov.get("DeepSeek") or 0) * 100)
            ty_y.append((cov.get("通义千问") or 0) * 100)
    if ds_x:
        fig, ax = plt.subplots(figsize=(8.4, 3.8), dpi=160)
        ax.plot(ds_x, ds_y, "-o", color=BLUE, lw=2.2, ms=6, label="DeepSeek 加权覆盖", zorder=3)
        ax.plot(ds_x, ty_y, "-o", color=GREEN, lw=2.2, ms=6, label="通义 加权覆盖", zorder=3)
        ax.axhline(40, color=ORANGE, ls="--", lw=1.2, label="目标阈值 40%")
        ax.set_title("站外信源加权覆盖趋势（%）", fontsize=12.5, fontweight="bold")
        ax.set_ylabel("%")
        ax.set_ylim(0, 100)
        ax.legend(fontsize=9, frameon=False)
        ax.grid(axis="x", visible=False)
        fig.tight_layout()
        p = os.path.join(paths.FIGURES, "trend_coverage.png")
        fig.savefig(p)
        plt.close(fig)
        out.append(p)

    return out


if __name__ == "__main__":
    figs = make_figures()
    print(f"[trend] 生成 {len(figs)} 张趋势图 -> {paths.FIGURES}")
    for f in figs:
        print("  -", os.path.basename(f))
