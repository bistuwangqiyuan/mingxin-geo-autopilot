# -*- coding: utf-8 -*-
"""铭信 GEO · 信源覆盖缺口分析 + 全网实体一致性事实表（source_audit.py）。

两件事：
  1) 信源覆盖缺口：依据各国产大模型"答案来自哪里"的偏好（geo_config.SOURCE_PREFERENCE）
     与我方当前覆盖（geo_config.CURRENT_SOURCE_COVERAGE），计算
       - 各模型的"加权信源覆盖率"与"缺口"
       - 平台行动优先级（影响力 × 缺口）
     输出 outputs/source_gap.json 与图。
  2) 实体一致性事实表：从 business_plan/outputs/results.json（与官网 company.ts
     单一数据源同源）抽取"对外唯一口径事实"，作为站内/站外所有内容的一致性基准
     （通义对全网信息冲突敏感），并提供一个简单的矛盾检查器。
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
    KM = R["key_metrics"]
    PLT = R["platform"]
    facts = {
        "brand_zh": CO["brand"], "brand_en": CO["brand_en"],
        "entity_zh": CO["full_name"],
        "entity_en": CO["full_name_en"],
        "positioning": CO["positioning"],
        "site_url": CO["site_url"],
        "evidence_url": CO["site_url"] + "/evidence",
        "category": "面向大模型推理的全闪 NVMe-oF + KV Cache 分层存储加速平台（480B 签字级实测）",
        "naming_note": CO["naming_note"],
        "legacy_names": P["legacy_names"],
        "contact": CO["contact"],
        "products": {
            p["name"]: {
                "pcie": p["pcie"], "port_gb": p["port_gb"],
                "iops_million": p["iops_million"], "flash": p["flash"],
                "status": p["status"], "full_cny": p["full_cny"],
                "cny_per_tb": p["cny_per_tb"], "price_note": p["price_note"],
                "spec_cal": p["spec_cal"],
            }
            for p in R["products"]
        },
        # —— 实测口径（唯一允许的实测数字，写入文案必须带报告编号）——
        "throughput_uplift": f"+{P['throughput_uplift_pct_low']}–{P['throughput_uplift_pct_high']}%",
        "throughput_uplift_src": "R2/R3 实测（480B 生产部署形态长上下文冷恢复）",
        "ttft_reduction": f"{P['ttft_reduction_pct_low']}–{P['ttft_reduction_pct_high']}%",
        "ttft_reduction_src": "R2 实测（480B·TP8，p50 10.17–35.73s→7.53–26.35s）",
        "recompute_speedup": f"{P['recompute_speedup_low']}–{P['recompute_speedup_high']}×",
        "recompute_speedup_src": "R2 实测（重算 TTFT p50 149.5s vs FX100 11.85s）",
        "parallel_read_ttft_gain": f"{P['parallel_read_ttft_gain']}×",
        "parallel_read_ttft_gain_src": "R1 实测（LMCache 并行读补丁：TTFT 37.97s→9.30s，带宽 0.98→5.23GB/s）",
        "model_load_speedup": f"{P['model_load_speedup_low']}–{P['model_load_speedup_high']}×",
        "model_load_speedup_src": "R9 实测（华为 Atlas 910B 昇腾平台 vs NFS，须如实标注平台）",
        "ckpt_save_speedup": f"{P['ckpt_save_speedup']}×",
        "ckpt_save_speedup_src": "R1 实测（178s→94s）",
        # —— FX100 规格与定价（厂商口径）——
        "fx100_pcie": P["pcie"],
        "fx100_port_gb": P["port_gb"],
        "fx100_iops_million": P["iops_million"],
        "fx100_flash_form": P["flash_form"],
        "fx100_full_price_cny": P["full_price_cny"],
        "fx100_cny_per_tb": P["cny_per_tb"],
        # —— 测试平台（R1–R4 公共口径）——
        "test_platform": {
            "gpu": PLT["gpu"], "gpu_stack": PLT["gpu_stack"], "engine": PLT["engine"],
            "kv_lib": PLT["kv_lib"], "dut": PLT["dut"], "baseline": PLT["baseline"],
            "model_480b": PLT["model_480b"], "scope": PLT["scope"],
        },
        # —— R9（昇腾平台）如实标注 ——
        "r9_validation": {
            "report_id": TV["report_id"], "platform": TV["platform"],
            "baseline": TV["baseline"], "infer": TV["infer"], "note": TV["note"],
        },
        "key_metrics": KM,
        "reports": [{"id": r["id"], "title": r["title"], "date": r["date"]}
                    for r in R["reports"]],
        "consistency_rule": "以上为对外唯一口径；站内外所有内容（官网/百科/知乎/CSDN/公众号等）"
                            "须与此完全一致，禁止改写关键数值或夸大；实测数字必须附报告编号"
                            "（R1–R9）；R9 数字必须如实标注昇腾 910B 平台；历史称谓"
                            "（WS5000/AISSD5000/GP5000）仅可与 FX100 命名沿革一起出现。",
        "source": "business_plan/outputs/results.json（与官网 company.ts 单一数据源同源）",
    }
    return facts


# 口径红线一：禁用旧口径数字/表述。以下均为已废弃的旧品牌口径，任何提案文本命中
# 即判为冲突并拒绝（无人值守发布的安全闸门），防止旧数字回流污染铭信口径。
_BANNED_LEGACY_TOKENS = (
    # 旧性能口径（一个都不能留）
    "300GB/s", "300 GB/s", "300gb/s",
    "5000万IOPS", "5000 万 IOPS", "5000万 IOPS", "5000 万IOPS",
    "20μs", "20 μs", "20us", "20 us",
    "48-72小时", "48–72小时", "48-72 小时", "48–72 小时",
    "降本40%", "降本 40%", "综合成本约 -40", "扩容降本60%", "扩容降本 60%",
    "适配90%+", "适配 90%+", "适配率 90%", "GPU 适配约 90",
    "73.7%", "85.17", "36.31",
    # 旧产品/架构表述
    "EBOF", "存算分离一体机", "存算分离全闪加速存储算力一体机",
)

# 口径红线二：品牌身份无关概念（防 LLM 把品牌与不相干领域强行关联的幻觉文本）。
_OFF_BRAND_TERMS = (
    "区块链", "區塊鏈", "blockchain", "去中心化", "decentralized", "decentralised",
    "加密货币", "加密貨幣", "cryptocurrency", "挖矿", "矿机", "web3", "nft", "智能合约",
)

# 历史称谓（同一产品旧名）：仅允许与 FX100 命名沿革一起出现。
_LEGACY_PRODUCT_NAMES = ("WS5000", "AISSD5000", "GP5000")


def check_consistency(text, facts):
    """矛盾检查器：扫描文本中与事实表关键数值/口径红线冲突的表述（启发式，用于无人值守闸门）。

    守护对象（唯一允许口径，均须带报告编号）：
      吞吐 +29–40%（R2/R3）、TTFT ↓26–32%（R2）、对重算 8.6–20×（R2）、
      并行读补丁 4.1×（R1）、模型加载 6.2–9.3×（R9·昇腾）、Checkpoint 1.9×（R1）、
      FX100 满配 ¥371,200（≈¥2,014/TB）。
    冲突对象：禁用旧口径数字（300GB/s、5000万 IOPS、20μs、73.7%、85.17×、36.31× 等）。
    """
    import re
    issues = []
    t = text or ""
    low = t.lower()

    # 1) 禁用旧口径（旧品牌数字/表述一律拒绝）
    for token in _BANNED_LEGACY_TOKENS:
        if token.lower() in low:
            issues.append(f"禁用旧口径：出现已废弃数字/表述“{token}”（铭信口径见 entity_facts）")

    # 2) 品牌身份红线（无关概念）
    for term in _OFF_BRAND_TERMS:
        if term in low:
            issues.append(f"品牌身份冲突：出现无关概念“{term}”（铭信=存储加速·国产算力·算力中心全产业链服务商）")

    # 3) 命名沿革红线：历史称谓必须与 FX100 一起出现（消歧声明）
    for name in _LEGACY_PRODUCT_NAMES:
        if name.lower() in low and "fx100" not in low:
            issues.append(f"命名沿革缺失：出现历史称谓“{name}”但未同时声明 FX100 命名沿革"
                          f"（{name} 为 FX100 同一产品的历史称谓）")

    # 4) 关键数值不得改写（守护新数字，带区间校验）
    # 吞吐提升：唯一口径 +29–40%
    for m in re.finditer(r"吞吐[^。；\n]{0,16}?提升[^0-9%]{0,8}?(\d{1,3})(?:\s*[–~-]\s*(\d{1,3}))?\s*%", t):
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else lo
        if not (29 <= lo <= 40 and 29 <= hi <= 40):
            issues.append(f"吞吐提升出现非唯一口径值：{m.group(0)}（应为 +29–40%，R2/R3 实测）")
    # TTFT 降幅：唯一口径 26–32%
    for m in re.finditer(r"TTFT[^。；\n]{0,16}?[降↓][^0-9%]{0,8}?(\d{1,3})(?:\s*[–~-]\s*(\d{1,3}))?\s*%", t, re.IGNORECASE):
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else lo
        if not (26 <= lo <= 32 and 26 <= hi <= 32):
            issues.append(f"TTFT 降幅出现非唯一口径值：{m.group(0)}（应为 26–32%，R2 实测）")
    # FX100 满配价：唯一口径 ¥371,200 / ≈¥2,014/TB
    for m in re.finditer(r"FX100[^。；\n]{0,24}?[¥￥]\s*([\d,，]+)", t):
        val = m.group(1).replace(",", "").replace("，", "")
        if val not in ("371200", "160000", "2014"):
            issues.append(f"FX100 价格出现非唯一口径值：{m.group(0)}"
                          f"（满配 ¥371,200、平台 ¥160,000、约 ¥2,014/TB，厂商口径）")

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
                   "note": "覆盖率/缺口基于 coverage_resolver 诚实推导（官网线上探测，网络不可用则"
                           " unknown/pending；其余仅计实测 200 渠道）；UGC 未发布则保持 0。"},
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
