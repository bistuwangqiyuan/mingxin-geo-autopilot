# -*- coding: utf-8 -*-
"""铭信 GEO 提升计划 · 复现链与一致性、诚实性校验（自我净化留痕）。

对齐当前流水线：
  geo_audit.py → geo_scoring.py / geo_projection.py / source_audit.py
              → build_report_html.py → export_report_pdf.py

校验项：
1. 复现链产物齐全：raw/ 采样、数据 JSON、HTML、PDF、全部图表。
2. 数值一致性：HTML 中的关键基线数值与 geo_baseline.json 完全一致。
3. 深化数据自洽：by_intent/by_persona/by_lang 样本数之和 = 有效采样数；
   head_to_head 的 (win+loss+both+neither) = 有效采样数；opportunity_gap 自洽。
4. 诚实性：预测明确标注为“规划假设/非承诺”；引用率短板如实披露；
   无任何待人工取证(B 级)模型被编造分数。
5. PDF 页数统计（如安装 pypdf）。

复现：python verify_geo.py
"""
from __future__ import annotations

import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "outputs")
FIG = os.path.join(OUT, "figures")
RAW = os.path.join(OUT, "raw")
HTML = os.path.join(OUT, "铭信-GEO提升计划.html")
PDF = os.path.join(os.path.dirname(BASE), "铭信-GEO提升计划.pdf")

DATA_FILES = ["geo_baseline.json", "geo_projection.json", "source_gap.json",
              "entity_facts.json", "run_manifest.json"]

FIGS = ["gvi_by_model.png", "mention_rate_by_tier.png", "gvi_radar.png",
        "share_of_voice.png", "mention_by_intent.png", "head_to_head.png",
        "source_coverage.png", "source_priority.png",
        "projection_trajectory.png", "projection_tornado.png",
        "projection_seed_sensitivity.png"]


def _load(name):
    with open(os.path.join(OUT, name), "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    errors, warns, oks = [], [], []

    # 1. 产物齐全 -----------------------------------------------------------
    for name in DATA_FILES:
        p = os.path.join(OUT, name)
        if os.path.exists(p) and os.path.getsize(p) > 0:
            oks.append(f"数据存在：{name}")
        else:
            errors.append(f"缺失数据：{name}")
    for path, name in [(HTML, "报告 HTML"), (PDF, "对外 PDF")]:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            oks.append(f"产物存在：{name}（{os.path.getsize(path)/1e6:.2f} MB）")
        else:
            errors.append(f"缺失产物：{name}")
    for fn in FIGS:
        if os.path.exists(os.path.join(FIG, fn)):
            oks.append(f"图表存在：{fn}")
        else:
            errors.append(f"缺失图表：{fn}")

    # raw 采样数
    n_raw = 0
    if os.path.isdir(RAW):
        for root, _dirs, files in os.walk(RAW):
            n_raw += len([f for f in files if f.endswith(".json")])
    if n_raw > 0:
        oks.append(f"raw/ 真实采样文件：{n_raw} 条")
    else:
        errors.append("raw/ 无采样文件")

    if errors:
        _report(errors, warns, oks)
        sys.exit(1)

    base = _load("geo_baseline.json")
    proj = _load("geo_projection.json")
    man = _load("run_manifest.json")
    with open(HTML, "r", encoding="utf-8") as f:
        html = f.read()

    ov = base["overall"]

    # 2. 数值一致性（HTML 必含的关键基线数值） -----------------------------
    checks = [
        ("总体 GVI", f"{ov['gvi']:.1f}"),
        ("被提及率", f"{ov['mention_rate']*100:.1f}%"),
        ("引用率", f"{ov['citation_rate']*100:.1f}%"),
        ("机会缺口总数", str(base["opportunity_gap"]["total"])),
    ]
    for label, token in checks:
        if token in html:
            oks.append(f"数值一致：{label} {token} 出现在 HTML")
        else:
            errors.append(f"数值不一致：{label} {token} 未出现在 HTML")

    # 3. 深化数据自洽 -------------------------------------------------------
    n_ok = ov["n_records_ok"]
    for field, label in [("by_intent", "意图"), ("by_persona", "角色"), ("by_lang", "语言")]:
        s = sum(d["n"] for d in base[field].values())
        if s == n_ok:
            oks.append(f"自洽：{label}切分样本数之和 {s} = 有效采样 {n_ok}")
        else:
            errors.append(f"不自洽：{label}切分样本数之和 {s} ≠ 有效采样 {n_ok}")

    for name, v in base["head_to_head"].items():
        tot = v["win"] + v["loss"] + v["both"] + v["neither"]
        if tot != n_ok:
            errors.append(f"不自洽：head_to_head[{name}] 计数之和 {tot} ≠ {n_ok}")
            break
    else:
        oks.append(f"自洽：head_to_head 每个竞品 win+loss+both+neither = {n_ok}")

    og = base["opportunity_gap"]
    if sum(og["by_tier"].values()) == og["total"] == sum(og["by_intent"].values()):
        oks.append(f"自洽：opportunity_gap 总数 {og['total']} 与 tier/intent 拆分一致")
    else:
        errors.append("不自洽：opportunity_gap 拆分之和与总数不符")

    # 4. 诚实性 -------------------------------------------------------------
    for token, desc in [("规划假设", "预测标注为规划假设"),
                        ("非承诺", "预测标注为非承诺"),
                        ("白帽", "白帽红线声明")]:
        if token in html:
            oks.append(f"诚实性：{desc} 已在报告中声明")
        else:
            warns.append(f"诚实性：未在报告中匹配到“{token}”")

    if ov["citation_rate"] < 0.05 and ("≈0" in html or "短板" in html):
        oks.append("诚实性：引用率短板如实披露")
    else:
        warns.append("诚实性：引用率短板披露未匹配")

    # B 级（待人工取证）模型不得在 by_model 中带分数
    fabricated = [m for m, v in base["by_model"].items() if v.get("grade") == "B"]
    if fabricated:
        warns.append(f"存在 B 级模型分数（需确认有真实人工取证）：{fabricated}")
    else:
        oks.append("诚实性：无任何待取证模型被编造分数（by_model 全为 A 级真测）")

    if man["counts"]["ok"] == n_raw == n_ok:
        oks.append(f"一致：manifest.ok={man['counts']['ok']} = raw 文件 {n_raw} = 有效采样 {n_ok}")
    else:
        warns.append(f"采样计数差异：manifest.ok={man['counts']['ok']} raw={n_raw} ok={n_ok}")

    # 5. PDF 页数 -----------------------------------------------------------
    try:
        from pypdf import PdfReader
        pages = len(PdfReader(PDF).pages)
        oks.append(f"PDF 页数：{pages}")
    except Exception as e:
        warns.append(f"未统计 PDF 页数（{e.__class__.__name__}）")

    _report(errors, warns, oks)
    sys.exit(1 if errors else 0)


def _report(errors, warns, oks):
    print("=" * 60)
    print("铭信 GEO 提升计划 · 复现链校验报告")
    print("=" * 60)
    for o in oks:
        print(f"  [OK]   {o}")
    for w in warns:
        print(f"  [WARN] {w}")
    for e in errors:
        print(f"  [FAIL] {e}")
    print("-" * 60)
    print(f"通过 {len(oks)} · 警告 {len(warns)} · 失败 {len(errors)}")
    print("结论：" + ("校验通过，可对外交付。" if not errors else "存在失败项，需修复。"))


if __name__ == "__main__":
    main()
