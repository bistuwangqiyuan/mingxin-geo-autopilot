# -*- coding: utf-8 -*-
"""苹果（Apple Keynote / macOS）视觉风格 matplotlib 主题。

设计语言：大留白、极简无边框、浅灰水平网格、克制的高级配色（System Colors）、
圆角图元、近似 San Francisco / PingFang 的中文字体（Windows 上以 Microsoft YaHei 近似）。
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from cycler import cycler

# ---- 字体（中文 + 拉丁回退）-------------------------------------------------
_CJK_CANDIDATES = ["PingFang SC", "Microsoft YaHei", "Source Han Sans CN", "SimHei", "DengXian"]
_available = {f.name for f in font_manager.fontManager.ttflist}
CJK_FONT = next((f for f in _CJK_CANDIDATES if f in _available), "sans-serif")

# ---- Apple System Colors（深色文本 + 系统强调色）---------------------------
INK = "#1D1D1F"          # Apple 近黑（文本/标题）
INK_SOFT = "#6E6E73"     # 次级文本（macOS secondary label）
HAIRLINE = "#D2D2D7"     # 分隔线
GRID = "#E8E8ED"         # 浅灰网格
PANEL = "#FBFBFD"        # 画布背景（Apple 网站浅灰白）
WHITE = "#FFFFFF"

BLUE = "#0A84FF"         # System Blue
INDIGO = "#5E5CE6"       # System Indigo
TEAL = "#30B0C7"         # System Teal
GREEN = "#34C759"        # System Green
ORANGE = "#FF9F0A"       # System Orange
PINK = "#FF375F"         # System Pink
PURPLE = "#BF5AF2"       # System Purple
GRAY = "#8E8E93"         # System Gray
YELLOW = "#FFD60A"

# 主序列（用于多系列图）—— 克制而有层次
PALETTE = [BLUE, INDIGO, TEAL, ORANGE, GREEN, PINK, PURPLE, GRAY]
# 蓝色渐变（用于堆叠/漏斗，体现 Apple 一致性）
BLUE_RAMP = ["#0A84FF", "#3D9BFF", "#64ADFF", "#8CC2FF", "#B6D8FF", "#DCEBFF"]


def apply_apple_style():
    plt.rcParams.update({
        "figure.facecolor": WHITE,
        "axes.facecolor": WHITE,
        "savefig.facecolor": WHITE,
        "font.family": [CJK_FONT, "Arial", "sans-serif"],
        "font.size": 13,
        "axes.unicode_minus": False,
        "text.color": INK,
        "axes.labelcolor": INK,
        "axes.titlecolor": INK,
        "xtick.color": INK_SOFT,
        "ytick.color": INK_SOFT,
        "axes.edgecolor": HAIRLINE,
        "axes.linewidth": 1.0,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRID,
        "grid.linewidth": 1.0,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "axes.prop_cycle": cycler(color=PALETTE),
        "axes.titlesize": 17,
        "axes.titleweight": "bold",
        "axes.titlepad": 16,
        "axes.labelpad": 8,
        "legend.frameon": False,
        "legend.fontsize": 11,
        "figure.dpi": 150,
        "savefig.dpi": 220,
        "lines.linewidth": 2.6,
        "lines.solid_capstyle": "round",
        "patch.linewidth": 0,
    })


def new_ax(w=9.2, h=5.4):
    """统一画布尺寸与留白。"""
    fig, ax = plt.subplots(figsize=(w, h))
    fig.subplots_adjust(left=0.10, right=0.94, top=0.80, bottom=0.14)
    return fig, ax


def title_block(ax, title, subtitle=None):
    """Apple Keynote 式标题：主标题加粗，副标题浅灰（均置于绘图区上方，互不重叠）。"""
    ax.text(0.0, 1.165, title, transform=ax.transAxes, fontsize=18,
            fontweight="bold", color=INK, ha="left", va="bottom")
    if subtitle:
        ax.text(0.0, 1.055, subtitle, transform=ax.transAxes,
                fontsize=12, color=INK_SOFT, ha="left", va="bottom")


def with_alpha(hex_color, alpha):
    """将 #RRGGBB 颜色按 alpha 与白底混合，返回浅色版 #RRGGBB（用于 SAM 浅底/SOM 实色叠加）。"""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = int(r * alpha + 255 * (1 - alpha))
    g = int(g * alpha + 255 * (1 - alpha))
    b = int(b * alpha + 255 * (1 - alpha))
    return f"#{r:02X}{g:02X}{b:02X}"


def thousands(x, pos=None):
    return f"{x:,.0f}"


def save(fig, path):
    fig.savefig(path, bbox_inches="tight", pad_inches=0.28, facecolor=WHITE)
    plt.close(fig)
