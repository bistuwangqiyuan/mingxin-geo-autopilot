# -*- coding: utf-8 -*-
"""触发一次引擎运行，盯到出结果，并按验收标准给出判定。

存在的理由：验收标准是「conclusion=success **且** run_log.json 各阶段无 FAIL」。
这两个条件必须一起看——workflow 里绝大多数业务步骤都带 `|| true`（单点失败不
应拖垮整条流水线），所以 conclusion=success 并不等于每一步都成功。只看绿灯
就宣布验收通过，是在自欺欺人。

用法：
    python scripts/trigger_and_watch.py                 # 全量 GVI（阶段 6 的口径）
    python scripts/trigger_and_watch.py --gvi-limit 4   # 快速冒烟
    python scripts/trigger_and_watch.py --watch-only    # 不触发，只盯最近一次运行

退出码：0 = 验收通过；1 = 未通过；2 = 无法判定（API 或前置检查失败）。
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

from repo_target import repo_slug

WORKFLOW = "geo-autopilot.yml"
POLL_SECONDS = 30
# 上限取自 workflow 的 timeout-minutes 25，加一段富余给排队等待。
MAX_WAIT_SECONDS = 45 * 60


def gh_json(*args: str):
    p = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0:
        return None, (p.stderr or "").strip()
    try:
        return json.loads(p.stdout or "null"), None
    except json.JSONDecodeError as e:
        return None, f"响应不是合法 JSON：{e}"


def latest_run(repo: str, since: datetime | None):
    data, err = gh_json("api", f"repos/{repo}/actions/workflows/{WORKFLOW}/runs?per_page=10")
    if data is None:
        return None, err
    for run in data.get("workflow_runs", []):
        if since is not None:
            created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
            if created < since:
                continue
            if run.get("event") != "workflow_dispatch":
                continue
        return run, None
    return None, None


def fetch_run_log(repo: str):
    """从仓库读回引擎自己写的 run_log.json（仓库公开，匿名亦可读）。"""
    data, err = gh_json("api", f"repos/{repo}/contents/geo_autopilot/outputs/run_log.json")
    if data is None:
        return None, err
    try:
        raw = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(raw), None
    except Exception as e:  # noqa: BLE001 - 读不到就如实说读不到，不猜
        return None, f"解析 run_log.json 失败：{e}"


def is_stale(log: dict, run: dict) -> bool:
    """判断读回的 run_log 是不是上一轮的遗留物。

    必须查这一项：运行若在回写提交之前就失败（例如被扫描闸门拦下、或 clone 阶段
    就挂了），仓库里留着的仍是**上一轮**的 run_log。不比时间戳就把它当本轮结果
    汇报，等于拿旧数据冒充新结论。
    """
    started = log.get("started")
    if not started:
        return True
    try:
        # 引擎写的是无时区的本地时间（runner 上即 UTC），按 UTC 解读。
        log_time = datetime.fromisoformat(started).replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    run_time = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
    return log_time < run_time


def report_run_log(log: dict) -> list[str]:
    """返回失败步骤的描述列表；空列表表示各阶段无 FAIL。"""
    steps = log.get("steps") or []
    failed = [s for s in steps if not s.get("ok")]
    print(f"\n[watch] run_log.json：mode={log.get('mode')} "
          f"started={log.get('started')} elapsed={log.get('elapsed')}s "
          f"步骤 {len(steps)} 个，失败 {len(failed)} 个")

    present = (log.get("paths") or {}).get("secrets_present") or {}
    if present:
        print("[watch] 密钥到位情况："
              + "，".join(f"{k}={'是' if v else '否'}" for k, v in present.items()))

    out = []
    for s in failed:
        tag = "CRITICAL" if s.get("critical") else "非关键"
        note = (s.get("note") or "").strip().replace("\n", " ")[:160]
        print(f"    FAIL [{tag}] {s.get('name')}：{note}")
        out.append(f"{s.get('name')}（{tag}）")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gvi-limit", default="0",
                    help="每模型 GVI 采样上限，0=全量（重建基线用 0）")
    ap.add_argument("--mode", default="ci", choices=["ci", "once"])
    ap.add_argument("--watch-only", action="store_true",
                    help="不触发新运行，只盯最近一次")
    ap.add_argument("--skip-verify", action="store_true",
                    help="跳过密钥前置检查（不建议）")
    args = ap.parse_args()

    repo = repo_slug()

    if not args.watch_only and not args.skip_verify:
        verifier = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "verify_secrets.py")
        rc = subprocess.run([sys.executable, verifier, "--strict"]).returncode
        if rc != 0:
            print("\n[watch] 前置检查未通过，不触发运行——"
                  "省下一次注定失败的运行，也省下你等它失败的时间。")
            return 2
        print()

    since = None
    if not args.watch_only:
        since = datetime.now(timezone.utc)
        p = subprocess.run(
            ["gh", "workflow", "run", WORKFLOW, "--repo", repo,
             "-f", f"mode={args.mode}", "-f", f"gvi_limit={args.gvi_limit}"],
            capture_output=True, text=True, encoding="utf-8")
        if p.returncode != 0:
            print(f"[watch] 触发失败：{(p.stderr or '').strip()}")
            return 2
        print(f"[watch] 已触发 {repo} 的 {WORKFLOW}"
              f"（mode={args.mode}, gvi_limit={args.gvi_limit}）")
        # dispatch API 不返回 run id，只能按创建时间捞回来。
        time.sleep(8)

    run = None
    deadline = time.time() + MAX_WAIT_SECONDS
    while time.time() < deadline:
        run, err = latest_run(repo, since)
        if err:
            print(f"[watch] 查询运行状态失败：{err}")
            return 2
        if run is None:
            print("[watch] 运行尚未出现在列表中，等待…")
            time.sleep(POLL_SECONDS)
            continue
        status = run.get("status")
        print(f"[watch] run {run['id']} status={status} "
              f"conclusion={run.get('conclusion')}  {run.get('html_url')}")
        if status == "completed":
            break
        time.sleep(POLL_SECONDS)
    else:
        print(f"[watch] 超过 {MAX_WAIT_SECONDS // 60} 分钟仍未结束，放弃等待（运行本身仍在继续）。")
        return 2

    conclusion = run.get("conclusion")
    print(f"\n[watch] 结论：conclusion={conclusion}")

    log, err = fetch_run_log(repo)
    if log is None:
        print(f"[watch] 无法读取 run_log.json：{err}")
        print("[watch] 判定：无法确认各阶段状态，验收不通过。")
        return 1

    if is_stale(log, run):
        print(f"\n[watch] 仓库里的 run_log.json 停留在 {log.get('started')}，"
              f"早于本次运行 {run['created_at']}——本轮没有回写。")
        print("[watch] 判定：本轮未产出可核对的阶段记录，验收不通过。"
              "（不拿上一轮的数据充数）")
        print(f"[watch] 日志：{run.get('html_url')}")
        return 1

    failed = report_run_log(log)

    print()
    if conclusion == "success" and not failed:
        print("[watch] 验收通过：conclusion=success 且各阶段无 FAIL。")
        return 0
    reasons = []
    if conclusion != "success":
        reasons.append(f"conclusion={conclusion}")
    if failed:
        reasons.append(f"{len(failed)} 个步骤 FAIL（{'；'.join(failed)}）")
    print(f"[watch] 验收不通过：{'；'.join(reasons)}")
    print(f"[watch] 日志：{run.get('html_url')}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
