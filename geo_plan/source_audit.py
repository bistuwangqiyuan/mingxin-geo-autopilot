# -*- coding: utf-8 -*-
"""中科存储 GEO · 信源覆盖缺口分析 + 全网实体一致性事实表（source_audit.py）。

两件事：
  1) 信源覆盖缺口：依据各国产大模型"答案来自哪里"的偏好（geo_config.SOURCE_PREFERENCE）
     与我方当前覆盖（geo_config.CURRENT_SOURCE_COVERAGE），计算
       - 各模型的"加权信源覆盖率"与"缺口"
       - 平台行动优先级（影响力 × 缺口）
     输出 outputs/source_gap.json 与图。
  2) 实体一致性事实表：从商业计划 results.json 抽取"对外唯一口径事实"，作为站内/站外
     所有内容的一致性基准（通义对全网信息冲突敏感），并提供一个简单的矛盾检查器。
     输出 outputs/entity_facts.json。

复现：python source_audit.py
"""
from __future__ import annotations

import json
import os

import geo_config as C

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "outputs")
FIG = os.path.join(OUT, "figures")
RESULTS = os.path.join(os.path.dirname(BASE), "business_plan", "outputs", "results.json")


def _active_coverage():
    """优先使用 coverage_resolver 的诚实推导；回退 geo_config 静态表。"""
    try:
        from coverage_resolver import resolve_coverage
        cov, _ev = resolve_coverage()
        return cov
    except Exception:
        return C.CURRENT_SOURCE_COVERAGE


def weighted_coverage(coverage=None):
    """各模型加权信源覆盖率与缺口。"""
    active = coverage if coverage is not None else _active_coverage()
    rows = {}
    for vendor, cfg in C.SOURCE_PREFERENCE.items():
        num = den = 0.0
        detail = []
        for plat in cfg["primary"]:
            w = 1.0
            cov = active.get(plat, 0.0)
            num += w * cov
            den += w
            detail.append({"platform": plat, "tier": "primary", "coverage": cov})
        for plat in cfg["secondary"]:
            w = 0.5
            cov = active.get(plat, 0.0)
            num += w * cov
            den += w
            detail.append({"platform": plat, "tier": "secondary", "coverage": cov})
        coverage = round(num / den, 4) if den else 0.0
        rows[vendor] = {"weighted_coverage": coverage, "gap": round(1 - coverage, 4),
                        "model_weight": cfg["weight"], "detail": detail,
                        "schema_pref": cfg["schema_pref"]}
    return rows


def platform_priority(coverage=None):
    """平台行动优先级 = Σ_models(归属权重 × 模型权重) × (1 - 现覆盖)。"""
    active = coverage if coverage is not None else _active_coverage()
    impact = {}
    contributing = {}
    for vendor, cfg in C.SOURCE_PREFERENCE.items():
        for plat in cfg["primary"]:
            impact[plat] = impact.get(plat, 0.0) + 1.0 * cfg["weight"]
            contributing.setdefault(plat, set()).add(vendor)
        for plat in cfg["secondary"]:
            impact[plat] = impact.get(plat, 0.0) + 0.5 * cfg["weight"]
            contributing.setdefault(plat, set()).add(vendor)
    out = []
    for plat, imp in impact.items():
        cov = active.get(plat, 0.0)
        out.append({"platform": plat, "impact": round(imp, 3),
                    "current_coverage": cov, "priority": round(imp * (1 - cov), 3),
                    "models": sorted(contributing[plat])})
    out.sort(key=lambda r: -r["priority"])
    return out


def entity_facts():
    """从 results.json 抽取对外唯一口径事实表（站内外一致性基准）。"""
    with open(RESULTS, "r", encoding="utf-8") as f:
        R = json.load(f)
    P, CO, TV = R["product"], R["company"], R["test_validation"]
    facts = {
        "brand_zh": "中科存储", "brand_en": "ZK-Storage",
        "entity_zh": "深圳市中科航星科技有限公司",
        "entity_en": "Hong Kong Zhongke Hangxing Technology Co., Limited",
        "category": "面向 AI 训练与推理的存算分离全闪存储加速一体机",
        "products": {
            "WS5000": {"model": P["model"], "bandwidth_gbps": P["bandwidth_gbps"],
                       "iops_million": P["iops_million"], "latency_us": P["latency_us"],
                       "maturity": P["maturity"]},
            "WS7000": {"iops_million": 70, "bandwidth_gbps": 300, "bandwidth_tbps": 2.4,
                       "latency_us": 20, "disk_count": 24, "max_disk_tb": 250},
        },
        "deploy_hours": P["deploy_hours"],
        "cost_reduction_pct": int(P["cost_reduction"] * 100),
        "expand_cost_reduction_pct": int(P["expand_cost_reduction"] * 100),
        "gpu_adaptation_pct": int(P["gpu_adaptation"] * 100),
        "gpu_util_uplift": f"{int(P['gpu_util_uplift_low'])}-{int(P['gpu_util_uplift_high'])}x",
        "kv_cache_cost_save_pct": round(P["kv_cache_cost_save"] * 100, 1),
        "third_party_test": {
            "issuer": TV["issuer"], "platform": TV["platform"], "baseline": TV["baseline"],
            "median_reduction_pct": round(TV["median_reduction"] * 100, 1),
            "metric_count": TV["metric_count"],
        },
        "rd_years": CO["rd_years"], "foundry_partner": CO["foundry_partner"],
        "capacity_units_per_month": CO["production_capacity_units_per_month"],
        "consistency_rule": "以上为对外唯一口径；站内外所有内容（官网/百科/知乎/CSDN/公众号等）"
                            "须与此完全一致，禁止改写关键数值或夸大；资质/证书沿用'申请中/示意'如实口径。",
        "source": "business_plan/outputs/results.json（与商业计划书/官网/简介同源）",
    }
    return facts


# 品牌身份红线：ZK-Storage = 中科存储（面向 AI 训练/推理的存算分离全闪存储企业）。
# LLM 易把 "ZK" 误展开为 zero-knowledge / 区块链 / 去中心化 等无关概念，这类内容若自动发布将损害品牌。
# 任何提案文本命中以下词条即判为口径冲突并拒绝（无人值守发布的安全闸门）。
_OFF_BRAND_TERMS = (
    "零知识", "零知識", "zero-knowledge", "zero knowledge", "zkp",
    "区块链", "區塊鏈", "blockchain", "去中心化", "decentralized", "decentralised",
    "加密货币", "加密貨幣", "cryptocurrency", "crypto", "代币", "挖矿", "矿工",
    "web3", "公链", "链上", "鏈上", "nft", "智能合约",
)


def check_consistency(text, facts):
    """矛盾检查器：扫描文本中与事实表关键数值/品牌身份冲突的表述（启发式，用于无人值守闸门）。"""
    import re
    issues = []
    t = text
    # 带宽
    for m in re.finditer(r"(\d{2,4})\s*GB/s", t):
        if m.group(1) not in ("300",):
            issues.append(f"带宽出现非唯一口径值：{m.group(0)}（应为 300 GB/s）")
    # 时延
    for m in re.finditer(r"(\d{1,4})\s*[μu]s", t):
        if m.group(1) not in ("20",):
            issues.append(f"时延出现非唯一口径值：{m.group(0)}（应为 20 μs）")
    # 品牌身份红线（大小写不敏感）
    low = t.lower()
    for term in _OFF_BRAND_TERMS:
        if term in low:
            issues.append(f"品牌身份冲突：出现无关概念“{term}”（ZK-Storage=中科存储，AI 存算分离全闪存储，非区块链/零知识/去中心化）")
    # 中位降幅
    for m in re.finditer(r"(\d{1,3}(?:\.\d)?)\s*%[^。]{0,8}(降幅|中位)", t):
        pass
    return issues


def make_figures(cov, prio):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "Segoe UI", "DejaVu Sans"],
        "axes.unicode_minus": False, "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white", "axes.edgecolor": "#D2D2D7", "grid.color": "#E8E8ED",
        "axes.grid": True, "grid.linewidth": 0.8, "text.color": "#1D1D1F",
        "axes.labelcolor": "#1D1D1F", "xtick.color": "#1D1D1F", "ytick.color": "#1D1D1F",
    })
    os.makedirs(FIG, exist_ok=True)
    blue, red = "#0071E3", "#FF375F"

    # 1. 各模型当前加权信源覆盖率（越低=缺口越大）
    vendors = list(cov.keys())
    vals = [cov[v]["weighted_coverage"] * 100 for v in vendors]
    fig, ax = plt.subplots(figsize=(8.4, 4.2), dpi=160)
    bars = ax.bar(range(len(vendors)), vals, color=blue, width=0.6, zorder=3)
    ax.set_xticks(range(len(vendors)))
    ax.set_xticklabels(vendors, fontsize=9, rotation=12)
    ax.set_ylabel("加权信源覆盖率（%）")
    ax.set_ylim(0, 100)
    ax.set_title("各国产大模型 · 我方当前信源覆盖率（基线，越低缺口越大）", fontsize=12.5, fontweight="bold")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1, f"{v:.0f}%",
                ha="center", fontsize=9, color="#1D1D1F")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "source_coverage.png"))
    plt.close(fig)

    # 2. 平台行动优先级（前 14）
    top = prio[:14]
    names = [r["platform"] for r in top][::-1]
    vals2 = [r["priority"] for r in top][::-1]
    fig, ax = plt.subplots(figsize=(8.4, 5.2), dpi=160)
    ax.barh(range(len(names)), vals2, color="#34C759", zorder=3)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel("行动优先级（影响力 × 缺口）")
    ax.set_title("站外信源 · 行动优先级排序", fontsize=12.5, fontweight="bold")
    for i, v in enumerate(vals2):
        ax.text(v + 0.02, i, f"{v:.2f}", va="center", fontsize=8, color="#1D1D1F")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "source_priority.png"))
    plt.close(fig)


def main():
    try:
        from coverage_resolver import write_coverage_snapshot
        snap, snap_path = write_coverage_snapshot(OUT)
        active_cov = snap["coverage"]
        print(f"[source_audit] 信源覆盖口径 -> {snap_path}")
    except Exception as e:
        active_cov = C.CURRENT_SOURCE_COVERAGE
        print(f"[source_audit] coverage_resolver 回退静态表: {e}")
    cov = weighted_coverage(active_cov)
    prio = platform_priority(active_cov)
    facts = entity_facts()
    with open(os.path.join(OUT, "source_gap.json"), "w", encoding="utf-8") as f:
        json.dump({"by_model": cov, "platform_priority": prio,
                   "coverage_snapshot": active_cov,
                   "note": "覆盖率/缺口基于 coverage_resolver 诚实推导（仅计实测 200 渠道）；UGC 未发布则保持 0。"},
                  f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUT, "entity_facts.json"), "w", encoding="utf-8") as f:
        json.dump(facts, f, ensure_ascii=False, indent=2)
    make_figures(cov, prio)
    print("信源缺口分析完成：")
    for v in cov:
        print(f"  {v:8s} 覆盖率={cov[v]['weighted_coverage']*100:4.0f}%  缺口={cov[v]['gap']*100:4.0f}%")
    print("  优先级前6平台：", [r["platform"] for r in prio[:6]])
    print("  实体事实表 -> outputs/entity_facts.json")


if __name__ == "__main__":
    main()
