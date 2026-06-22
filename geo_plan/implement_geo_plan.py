# -*- coding: utf-8 -*-
"""中科存储 GEO 提升计划 · 一键落地实施（不修改计划 HTML 本身）。

按 geo_plan/outputs/中科存储-GEO提升计划.html 四阶段任务，执行所有可自动化部分：
  1) 站内 GEO 地基复核（build + verify）
  2) 信源覆盖诚实更新（coverage_resolver → source_audit）
  3) 站外微站重建（seo_geo_loop/build_offsite_*）
  4) 站外定稿包刷新（make_offsite_kit.py）
  5) 测量链复现（geo_scoring / geo_projection / verify_geo）
  6) 可选：seo_geo_loop 联网动作（IndexNow / live_audit / gvi_measure）

白帽：UGC 平台（CSDN/知乎/百科/公众号等）仅交付定稿 + SOP，不自动发帖。

复现：python implement_geo_plan.py
      python implement_geo_plan.py --with-net   # 含 IndexNow + live_audit
      python implement_geo_plan.py --with-gvi   # 含真实 GVI 重测（消耗 token）
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
OW = os.path.join(ROOT, "official_website")
LOOP = os.path.join(ROOT, "seo_geo_loop")
OUT = os.path.join(BASE, "outputs")


def step(title, cmd, cwd=BASE, allow_fail=False):
    print("\n" + "=" * 72 + f"\n>> {title}\n" + "=" * 72)
    t0 = time.time()
    rc = subprocess.run([sys.executable, *cmd], cwd=cwd).returncode
    print(f"  ({title} 用时 {time.time()-t0:.1f}s, exit={rc})")
    if rc != 0 and not allow_fail:
        raise SystemExit(f"步骤失败：{title} (exit {rc})")
    return rc


def write_implementation_status(extra=None):
    """写入 outputs/implementation_status.json（实施看板单一事实源）。"""
    status_path = os.path.join(OUT, "implementation_status.json")
    gvi_path = os.path.join(LOOP, "outputs", "gvi_compare.json")
    pub_path = os.path.join(LOOP, "outputs", "offsite_published.json")
    baseline_path = os.path.join(OUT, "geo_baseline.json")
    gap_path = os.path.join(OUT, "source_gap.json")

    def _load(p):
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    baseline = _load(baseline_path)
    gap = _load(gap_path)
    gvi = _load(gvi_path)
    pub = _load(pub_path)

    phases = {
        "P1_地基": {
            "status": "done",
            "items": {
                "robots_ai_bots": "done",
                "llms_txt": "done",
                "geo_fact_pages": "done",
                "json_ld_schema": "done",
                "baseline_report": "done",
                "verify_geo": "done",
            },
            "note": "站内 GEO 基础设施已落地；GSC 部分页面已编入索引（概述报告滞后）",
        },
        "P2_T1夺冠": {
            "status": "partial",
            "items": {
                "answer_first_pages": "done",
                "offsite_microsites": "done" if pub.get("channels") else "pending",
                "csdn_zhihu_publish": "pending_manual",
                "aliyun_yuque_publish": "pending_manual",
                "gvi_lift": "not_yet" if gvi.get("delta_gvi", 0) <= 0 else "in_progress",
            },
            "note": "站外微站已上线；CSDN/知乎/语雀需人工发布（定稿见 geo_plan/offsite/）",
        },
        "P3_T2梯队": {
            "status": "pending",
            "items": {
                "baike_baijiahao": "pending_manual",
                "wechat_sohu": "pending_manual",
                "grade_b_manual_protocol": "ready",
            },
            "note": "B 级模型人工取证协议已就绪；待采集后纳入矩阵",
        },
        "P4_稳固出海": {
            "status": "partial",
            "items": {
                "english_fact_pages": "done",
                "sameas_entity_graph": "done" if pub.get("sameas_urls") else "partial",
                "english_gvi": "not_yet",
                "monthly_retest_cadence": "started",
            },
            "note": "英文页面已构建；英文 GVI 仍为 0%（需站外英文信源积累）",
        },
    }

    kpi = {
        "baseline_gvi": baseline.get("overall", {}).get("gvi"),
        "baseline_mention_rate": baseline.get("overall", {}).get("mention_rate"),
        "end_gvi": gvi.get("end", {}).get("gvi") if gvi else None,
        "delta_gvi": gvi.get("delta_gvi") if gvi else None,
        "deepseek_coverage": gap.get("by_model", {}).get("DeepSeek", {}).get("weighted_coverage"),
        "tongyi_coverage": gap.get("by_model", {}).get("通义千问", {}).get("weighted_coverage"),
    }

    doc = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "plan_reference": "geo_plan/outputs/中科存储-GEO提升计划.html",
        "phases": phases,
        "kpi": kpi,
        "blocked_manual": [
            {"task": "CSDN/知乎/语雀/百科/公众号/搜狐 发布", "reason": "无开放写 API、需实名", "sop": "geo_plan/offsite/SOP_manual_publish.md"},
            {"task": "百度收录", "reason": "ICP 备案依赖", "sop": "seo_geo_loop/outputs/external_actions_status.json"},
            {"task": "GSC 请求编入索引（剩余页）", "reason": "每日配额已用尽", "sop": "live_status.gsc_url_inspection.pending_next_day"},
        ],
    }
    if extra:
        doc.update(extra)
    os.makedirs(OUT, exist_ok=True)
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"[implement] 实施看板 -> {status_path}")
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-net", action="store_true", help="含 IndexNow + live_audit")
    ap.add_argument("--with-gvi", action="store_true", help="含真实 GVI 重测（消耗 token）")
    ap.add_argument("--skip-site-build", action="store_true")
    args = ap.parse_args()

    print("=" * 72)
    print("中科存储 GEO 提升计划 · 落地实施（implement_geo_plan.py）")
    print("=" * 72)

    if not args.skip_site_build:
        step("站内复核 build_site.py", ["build_site.py"], cwd=OW)
        step("站内复核 verify_site.py", ["verify_site.py"], cwd=OW)

    step("刷新站外定稿包 make_offsite_kit.py", ["make_offsite_kit.py"])
    step("重建 EdgeOne 微站目录", ["build_offsite_site.py"], cwd=LOOP)
    step("重建 GitHub Pages 目录", ["build_offsite_github.py"], cwd=LOOP)

    step("信源覆盖诚实更新 source_audit.py", ["source_audit.py"])
    step("基线评分 geo_scoring.py", ["geo_scoring.py"])
    step("提升预测 geo_projection.py", ["geo_projection.py"])

    if args.with_net:
        step("IndexNow 重推", ["indexnow_submit.py"], cwd=LOOP, allow_fail=True)
        step("线上真测 live_audit.py", ["live_audit.py"], cwd=LOOP, allow_fail=True)

    if args.with_gvi:
        step("真实 GVI 重测 gvi_measure.py --force", ["gvi_measure.py", "--force"], cwd=LOOP, allow_fail=True)

    step("复现校验 verify_geo.py", ["verify_geo.py"])
    step("组装计划报告 build_report_html.py", ["build_report_html.py"])
    step("导出计划 PDF export_report_pdf.py", ["export_report_pdf.py"])

    write_implementation_status({"pipeline": "implement_geo_plan.py", "with_net": args.with_net, "with_gvi": args.with_gvi})

    step("组装实施报告 build_implementation_report.py", ["build_implementation_report.py"])
    step("导出实施 PDF export_implementation_pdf.py", ["export_implementation_pdf.py"])

    print("\n[OK] GEO plan implementation complete.")
    print("   计划报告：geo_plan/outputs/中科存储-GEO提升计划.html + ../中科存储-GEO提升计划与基线报告.pdf")
    print("   实施报告：geo_plan/outputs/中科存储-GEO计划落地实施报告.html + ../中科存储-GEO计划落地实施报告.pdf")


if __name__ == "__main__":
    main()
