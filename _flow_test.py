# -*- coding: utf-8 -*-
"""全流程真实功能测试运行器（测试→修错→再测循环用）。

按依赖顺序真实执行三条流水线的全部环节 + 验收测试，逐项记录 PASS/FAIL。
真实数据、真实网络、真实 LLM 调用（采样量受限以控制时长/成本，但全为真调用）。
"""
import io
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
RESULTS = []


def load_env():
    p = os.path.join(ROOT, ".env")
    if os.path.isfile(p):
        for line in io.open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def run(name, cwd, args, timeout=1800):
    t0 = time.time()
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        p = subprocess.run([sys.executable, "-X", "utf8", *args],
                           cwd=os.path.join(ROOT, cwd), capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, env=env)
        ok = p.returncode == 0
        tail = ((p.stdout or "") + "\n" + (p.stderr or "")).strip().splitlines()
        note = " | ".join(tail[-2:]) if tail else ""
    except subprocess.TimeoutExpired:
        ok, note = False, f"TIMEOUT>{timeout}s"
    except Exception as e:  # noqa: BLE001
        ok, note = False, f"spawn: {e}"
    el = round(time.time() - t0, 1)
    RESULTS.append({"name": name, "ok": ok, "elapsed": el, "note": note[:400]})
    print(f"[{'PASS' if ok else 'FAIL'}] {name} ({el}s)" + ("" if ok else f"\n       {note[:400]}"), flush=True)
    return ok


STEPS = [
    # ---- 0. 模块可导入性（快速冒烟）----
    ("import:llm_providers", "geo_plan", ["-c", "import llm_providers; print(llm_providers.available())"]),
    ("import:geo_data", "geo_plan", ["-c", "import geo_data as G; print(len(G.QUERY_BASKET), len(G.reachable_engines()))"]),
    ("import:geo_config", "geo_plan", ["-c", "import geo_config as C; print(len(C.MODELS_API))"]),
    ("import:site_facts", "seo_geo_loop", ["-c", "import site_facts as D; print(D.BRAND_ZH, D.SITE_URL)"]),
    ("import:paths", "geo_autopilot", ["-c", "import paths; paths.ensure_dirs(); import json; print(json.dumps(paths.summary(), ensure_ascii=False))"]),
    # ---- 1. geo_plan 主链（真实 LLM 探测 + 打分 + 报告 + PDF + 校验）----
    ("geo_plan:audit_probe", "geo_plan", ["geo_audit.py", "--probe"]),
    ("geo_plan:scoring70", "geo_plan", ["geo_scoring.py"]),
    ("geo_plan:source_audit", "geo_plan", ["source_audit.py"]),
    ("geo_plan:projection", "geo_plan", ["geo_projection.py"]),
    ("geo_plan:scoring12", "geo_plan", ["scoring.py"]),
    ("geo_plan:charts_geo", "geo_plan", ["charts_geo.py"]),
    ("geo_plan:build_geo_html", "geo_plan", ["build_geo_html.py"]),
    ("geo_plan:build_report_html", "geo_plan", ["build_report_html.py"]),
    ("geo_plan:build_impl_report", "geo_plan", ["build_implementation_report.py"]),
    ("geo_plan:export_geo_pdf", "geo_plan", ["export_geo_pdf.py"]),
    ("geo_plan:export_impl_pdf", "geo_plan", ["export_implementation_pdf.py"]),
    ("geo_plan:make_offsite_kit", "geo_plan", ["make_offsite_kit.py"]),
    ("geo_plan:verify_geo", "geo_plan", ["verify_geo.py"]),
    # ---- 2. seo_geo_loop 链（GVI 小样真测 + 站外构建 + 线上审计 + 报告）----
    ("loop:gvi_measure_lim2", "seo_geo_loop", ["gvi_measure.py", "--limit", "2", "--force"]),
    ("loop:make_geo_kit_en", "seo_geo_loop", ["make_geo_kit_en.py"]),
    ("loop:build_offsite_site", "seo_geo_loop", ["build_offsite_site.py"]),
    ("loop:build_offsite_github", "seo_geo_loop", ["build_offsite_github.py"]),
    ("loop:charts", "seo_geo_loop", ["charts.py"]),
    ("loop:live_audit", "seo_geo_loop", ["live_audit.py"]),
    ("loop:update_live_status", "seo_geo_loop", ["_update_live_status.py"]),
    ("loop:indexnow_submit", "seo_geo_loop", ["indexnow_submit.py"]),
    ("loop:build_report_html", "seo_geo_loop", ["build_report_html.py"]),
    ("loop:export_report_pdf", "seo_geo_loop", ["export_report_pdf.py"]),
    # ---- 3. geo_autopilot 链（挖词 → 决策脑 → 应用 → 校验 → 指标 → 日报 → 告警）----
    ("ap:keyword_miner", "geo_autopilot", ["keyword_miner.py"]),
    ("ap:geo_brain", "geo_autopilot", ["geo_brain.py"]),
    ("ap:apply_proposals", "geo_autopilot", ["apply_proposals.py"]),
    ("ap:metrics", "geo_autopilot", ["metrics.py"]),
    ("ap:trend", "geo_autopilot", ["trend.py"]),
    ("ap:traffic_check", "geo_autopilot", ["traffic_check.py"]),
    ("ap:build_daily_report", "geo_autopilot", ["build_daily_report.py"]),
    ("ap:export_daily_pdf", "geo_autopilot", ["export_daily_pdf.py"]),
    ("ap:alerting", "geo_autopilot", ["alerting.py"]),
    # ---- 4. 编排器完整跑（含网络，不推送）+ 验收测试 ----
    ("orchestrator:once_skipgvi", "geo_autopilot", ["autopilot.py", "--once", "--skip-gvi"]),
    ("acceptance:test_suite", "tests", ["test_geo_seo_autopilot.py"]),
]


def main():
    load_env()
    only = set(sys.argv[1:])
    for name, cwd, args in STEPS:
        if only and name not in only:
            continue
        run(name, cwd, args)
    n_ok = sum(1 for r in RESULTS if r["ok"])
    print("-" * 70)
    print(f"TOTAL: {n_ok}/{len(RESULTS)} PASS")
    with open(os.path.join(ROOT, "_flow_test_results.json"), "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=2)
    sys.exit(0 if n_ok == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
