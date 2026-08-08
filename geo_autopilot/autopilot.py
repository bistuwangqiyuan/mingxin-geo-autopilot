# -*- coding: utf-8 -*-
"""铭信 GEO Autopilot · 每日无人值守主编排器（autopilot.py）。

模式：
  --dry-run   不联网、不写站点、不推送（最快，校验装配是否完整）
  --once      本地完整跑（含真实 GVI 小样、重建、报告），但**不 git push**
  --ci        云端完整跑（含真实 GVI、重建、联网真测、提交并推送站点、告警）

护栏（实事求是、求实效）：
  --gvi-limit N   每模型仅采样前 N 条（预算/超时护栏；0=全部）
  --skip-gvi      跳过真实采样，沿用上次（如实标注）
  --no-llm        决策脑用确定性规则（LLM 不可达时的诚实回退）
  每步失败不静默：记录到 outputs/run_log.json，关键步骤失败触发告警。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

import paths

RUN_LOG = os.path.join(paths.OUTPUTS, "run_log.json")
STEPS = []
T0 = time.time()


def log(msg):
    print(f"[autopilot] {msg}", flush=True)


def record(name, ok, note="", critical=False, elapsed=None):
    STEPS.append({"name": name, "ok": bool(ok), "note": note,
                  "critical": critical, "elapsed": elapsed})


def run_py(script, cwd, args=None, timeout=3600, critical=False, env=None):
    """运行一个 Python 脚本，记录结果。"""
    name = f"{os.path.basename(cwd)}/{script} {' '.join(args or [])}".strip()
    t = time.time()
    e = dict(os.environ)
    e["PYTHONIOENCODING"] = "utf-8"
    if env:
        e.update(env)
    try:
        proc = subprocess.run([sys.executable, script, *(args or [])], cwd=cwd,
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout, env=e)
        ok = proc.returncode == 0
        tail = ((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()
        note = tail[-1] if tail else ""
        record(name, ok, note, critical, round(time.time() - t, 1))
        log(f"{'OK ' if ok else 'ERR'} {name}  ({time.time()-t:.1f}s)")
        if not ok:
            log("  tail: " + " | ".join(tail[-3:]))
        return ok, proc
    except subprocess.TimeoutExpired:
        record(name, False, f"timeout>{timeout}s", critical, timeout)
        log(f"ERR {name}  (timeout)")
        return False, None
    except Exception as ex:  # noqa: BLE001
        record(name, False, f"exception: {ex}", critical, round(time.time() - t, 1))
        return False, None


def git(args, cwd, critical=False):
    name = f"git -C {os.path.basename(cwd)} {' '.join(args[:2])}"
    t = time.time()
    try:
        proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=300)
        ok = proc.returncode == 0
        record(name, ok, (proc.stdout or proc.stderr or "").strip().splitlines()[-1:] and
               ((proc.stdout or proc.stderr or "").strip().splitlines()[-1]) or "", critical)
        return ok, proc
    except Exception as ex:  # noqa: BLE001
        record(name, False, f"git exception: {ex}", critical)
        return False, None


def deploy_repo(repo_dir, message, push):
    """提交并（可选）推送一个站点仓库；返回是否有改动被提交。"""
    if not os.path.isdir(os.path.join(repo_dir, ".git")):
        record(f"deploy {os.path.basename(repo_dir)}", False, "非 git 仓库，跳过", False)
        return False
    git(["add", "-A"], repo_dir)
    st, proc = git(["status", "--porcelain"], repo_dir)
    if proc is None or not (proc.stdout or "").strip():
        record(f"deploy {os.path.basename(repo_dir)}", True, "无改动，无需部署", False)
        return False
    git(["commit", "-m", message], repo_dir)
    if push:
        ok, _ = git(["push", "origin", "HEAD"], repo_dir, critical=False)
        if not ok:
            # 高频运行护栏：远端可能在本次运行期间被推进（人工/其它任务），rebase 后重试一次
            git(["fetch", "origin"], repo_dir)
            git(["rebase", "origin/main"], repo_dir)
            ok, _ = git(["push", "origin", "HEAD:main"], repo_dir, critical=True)
        record(f"push {os.path.basename(repo_dir)}", ok,
               "已推送触发部署" if ok else "推送失败(rebase 重试后仍失败)", True)
        return ok
    record(f"deploy {os.path.basename(repo_dir)}", True, "已提交（本地，未推送）", False)
    return True


def save_run_log(mode):
    paths.ensure_dirs()
    doc = {"mode": mode, "started": time.strftime("%Y-%m-%dT%H:%M:%S",
           time.localtime(T0)), "elapsed": round(time.time() - T0, 1),
           "paths": paths.summary(), "steps": STEPS}
    with open(RUN_LOG, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    log(f"run_log -> {RUN_LOG}")
    return doc


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--once", action="store_true")
    g.add_argument("--ci", action="store_true")
    ap.add_argument("--gvi-limit", type=int, default=int(os.environ.get("MX_GVI_LIMIT", "0")))
    ap.add_argument("--skip-gvi", action="store_true")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--push", action="store_true", help="允许 git push（--ci 默认开启）")
    args = ap.parse_args()

    mode = "ci" if args.ci else ("once" if args.once else "dry-run")
    dry = mode == "dry-run"
    do_net = mode in ("once", "ci")
    do_push = args.push or mode == "ci"
    if args.no_llm:
        os.environ["MX_ALLOW_LLM"] = "0"

    paths.ensure_dirs()
    log(f"mode={mode} net={do_net} push={do_push} gvi_limit={args.gvi_limit}")
    log("paths: " + json.dumps(paths.summary()["exists"], ensure_ascii=False))

    GEO, LOOP = paths.GEO_PLAN, paths.LOOP

    # 0. 行业热词挖掘（四步法第 1 步；台账去重限量，LLM 失败种子库兜底，纯本地写盘）
    run_py("keyword_miner.py", paths.AUTOPILOT_DIR, [], timeout=300, critical=False)

    # 1. 真实 GVI 重测（护栏：limit/timeout；dry-run 或 skip 则沿用上次）
    if dry or args.skip_gvi:
        record("gvi_measure", True, "dry-run/skip：沿用上次真实重测（如实标注）", False)
    else:
        gvi_args = ["--force"]
        if args.gvi_limit:
            gvi_args += ["--limit", str(args.gvi_limit)]
        run_py("gvi_measure.py", LOOP, gvi_args, timeout=2400, critical=False)

    # 2. AI 决策脑
    run_py("geo_brain.py", paths.AUTOPILOT_DIR, [], timeout=300, critical=False)

    # 3. 内容自进化（经 verify 闸门；dry-run 仅校验）
    apply_args = ["--dry-run"] if dry else []
    run_py("apply_proposals.py", paths.AUTOPILOT_DIR, apply_args, timeout=600, critical=False)

    # 4. 重建站外目录 + 信源覆盖诚实更新 + 评分 + 英文成品包（Medium/Quora/LinkedIn）
    run_py("build_offsite_site.py", LOOP, [], timeout=300)
    run_py("build_offsite_github.py", LOOP, [], timeout=300)
    run_py("make_geo_kit_en.py", LOOP, [], timeout=300, critical=False)
    run_py("source_audit.py", GEO, [], timeout=300)
    run_py("geo_scoring.py", GEO, [], timeout=600)

    # 5. 联网真测（仅 once/ci）+ 流量信号检测（四步法第 4 步；GA4 未配置如实跳过）
    if do_net:
        run_py("indexnow_submit.py", LOOP, [], timeout=300, critical=False)
        run_py("live_audit.py", LOOP, [], timeout=600, critical=False)
        run_py("traffic_check.py", paths.AUTOPILOT_DIR, [], timeout=180, critical=False)

    # 6. 部署（仅 ci push；once 本地提交不推）
    #
    # 官网仓不再参与：内容自进化的产出已在第 3 步经 HTTP 提交给站点接口落库并即时生效，
    # 不需要 clone 私有仓、不需要 commit、也不需要 Deploy Hook。去掉这条链路同时消掉了
    # 「公开仓 CI 持有私有主仓写权限」这个安全面。知识库仓是公开仓，仍按原样提交。
    if do_net:
        deploy_repo(paths.KB_REPO, "chore(geo-autopilot): daily KB refresh", do_push)

    # 7. 历史快照 + 趋势 + 日报 + PDF
    run_py("build_daily_report.py", paths.AUTOPILOT_DIR, [], timeout=300, critical=True)
    run_py("export_daily_pdf.py", paths.AUTOPILOT_DIR, [], timeout=300, critical=False)

    # 8. 告警（dry-run 仅本地落盘）
    alert_env = {"MX_ALERT_DRYRUN": "1"} if dry else {}
    run_py("alerting.py", paths.AUTOPILOT_DIR, [], timeout=120, critical=False, env=alert_env)

    doc = save_run_log(mode)
    n_ok = sum(1 for s in STEPS if s["ok"])
    n_crit_fail = sum(1 for s in STEPS if s["critical"] and not s["ok"])
    log(f"完成：{n_ok}/{len(STEPS)} 步 OK；关键失败 {n_crit_fail}。用时 {doc['elapsed']}s")
    sys.exit(1 if n_crit_fail else 0)


if __name__ == "__main__":
    main()
