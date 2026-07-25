"""诊断 GEO Autopilot 的 GitHub Actions 停跑根因（可复现，只读）。

用途：连续失败但 job 步骤数为 0 时，区分以下根因：
  A. Actions 配额耗尽（私有仓库免费额度 2000 分钟/月）
  B. GH_PAT / secrets 失效导致 job 无法启动
  C. 代码或步骤级失败（此时步骤数 > 0，本脚本会明确排除 A/B）

用法:
    python scripts/actions_diagnose.py
    python scripts/actions_diagnose.py --json      # 机器可读输出

依赖: 已登录的 gh CLI（gh auth status 正常）。仅使用标准库。

计费口径依据（GitHub 官方文档，2026-07 核对）:
  - GitHub Free 账户私有仓库：2000 Actions 分钟/月
  - Linux (ubuntu-latest) runner 计费倍率 1x
  - 每次 job 的计费时长按分钟向上取整
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone

REPO = "bistuwangqiyuan/zk-geo-autopilot"
FREE_PRIVATE_MINUTES_PER_MONTH = 2000
LINUX_BILLING_MULTIPLIER = 1


def gh(endpoint: str) -> dict | list | None:
    """调用 gh api，失败返回 None 而不抛出（用于探测无权限端点）。"""
    proc = subprocess.run(
        ["gh", "api", endpoint], capture_output=True, text=True, encoding="utf-8"
    )
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def collect() -> dict:
    result: dict = {"repo": REPO, "generated_at": datetime.now(timezone.utc).isoformat()}

    repo_meta = gh(f"repos/{REPO}") or {}
    result["private"] = repo_meta.get("private")
    result["archived"] = repo_meta.get("archived")
    result["disabled"] = repo_meta.get("disabled")

    runs_data = gh(f"repos/{REPO}/actions/runs?per_page=100") or {}
    # GitHub REST 返回的键是 workflow_runs
    runs = runs_data.get("workflow_runs", [])
    result["runs_fetched"] = len(runs)
    result["runs_total"] = runs_data.get("total_count")
    result["conclusions"] = dict(Counter(r.get("conclusion") for r in runs))

    successes = [r for r in runs if r.get("conclusion") == "success"]
    failures = [r for r in runs if r.get("conclusion") == "failure"]

    # 失败连续段：按时间正序，找最后一次成功之后的全部失败
    by_time = sorted(runs, key=lambda r: r["created_at"])
    last_success = next(
        (r for r in reversed(by_time) if r.get("conclusion") == "success"), None
    )
    result["last_success_at"] = last_success["created_at"] if last_success else None
    if last_success:
        streak = [
            r
            for r in by_time
            if r["created_at"] > last_success["created_at"]
            and r.get("conclusion") == "failure"
        ]
    else:
        streak = failures
    result["failure_streak_len"] = len(streak)
    result["failure_streak_first_at"] = streak[0]["created_at"] if streak else None
    result["failure_streak_last_at"] = streak[-1]["created_at"] if streak else None

    # 关键判据：失败运行的 job 是否有步骤。步骤数 0 => runner 从未启动。
    step_probe = []
    for r in streak[-3:]:
        jobs = gh(f"repos/{REPO}/actions/runs/{r['id']}/jobs") or {}
        for j in jobs.get("jobs", []):
            dur = None
            if j.get("started_at") and j.get("completed_at"):
                dur = (iso(j["completed_at"]) - iso(j["started_at"])).total_seconds()
            step_probe.append(
                {
                    "run_id": r["id"],
                    "created_at": r["created_at"],
                    "job_conclusion": j.get("conclusion"),
                    "steps": len(j.get("steps", [])),
                    "job_seconds": dur,
                }
            )
    result["failure_job_probe"] = step_probe
    result["all_failures_have_zero_steps"] = bool(step_probe) and all(
        p["steps"] == 0 for p in step_probe
    )

    # 真实计费时长：取历史成功运行的 timing（而非估算）
    timings = []
    for r in successes[:10]:
        t = gh(f"repos/{REPO}/actions/runs/{r['id']}/timing")
        if not t:
            continue
        billable = t.get("billable", {}) or {}
        ubuntu = billable.get("UBUNTU", {}) or {}
        timings.append(
            {
                "run_id": r["id"],
                "created_at": r["created_at"],
                "run_duration_ms": t.get("run_duration_ms"),
                "billable_ubuntu_ms": ubuntu.get("total_ms"),
            }
        )
    result["success_timings"] = timings

    # 账单端点（通常需额外 scope；无权限时如实标记）
    billing = gh("user/settings/billing/actions")
    result["billing_api"] = billing if billing else "unavailable (404/insufficient scope)"

    # secrets 元数据（不含值），用于判断 PAT 是否长期未更新
    secrets = gh(f"repos/{REPO}/actions/secrets") or {}
    result["secrets"] = [
        {"name": s["name"], "updated_at": s["updated_at"]}
        for s in secrets.get("secrets", [])
    ]

    return result


def analyse(d: dict) -> dict:
    """基于采集数据做可复现的用量测算与根因判断。"""
    out: dict = {}

    # 用量测算：优先用真实 billable_ubuntu_ms，回退到 run_duration_ms
    samples = []
    for t in d.get("success_timings", []):
        ms = t.get("billable_ubuntu_ms") or t.get("run_duration_ms")
        if ms:
            samples.append(ms)

    if samples:
        avg_ms = sum(samples) / len(samples)
        # 计费按分钟向上取整
        billed_min_per_run = math.ceil(avg_ms / 60000) * LINUX_BILLING_MULTIPLIER
        runs_per_day = 6  # cron: 30 0/4/8/12/16/20
        per_day = billed_min_per_run * runs_per_day
        per_month = per_day * 30
        out["usage_estimate"] = {
            "samples": len(samples),
            "avg_run_ms": round(avg_ms),
            "billed_minutes_per_run": billed_min_per_run,
            "runs_per_day": runs_per_day,
            "minutes_per_day": per_day,
            "minutes_per_30d": per_month,
            "free_quota": FREE_PRIVATE_MINUTES_PER_MONTH,
            "quota_exhausted_after_days": round(
                FREE_PRIVATE_MINUTES_PER_MONTH / per_day, 1
            )
            if per_day
            else None,
            "exceeds_free_quota": per_month > FREE_PRIVATE_MINUTES_PER_MONTH,
        }
    else:
        out["usage_estimate"] = None

    # 根因判断
    reasons = []
    zero_steps = d.get("all_failures_have_zero_steps")
    fast_fail = all(
        (p.get("job_seconds") or 99) < 15 for p in d.get("failure_job_probe", [])
    ) and bool(d.get("failure_job_probe"))

    if zero_steps and fast_fail:
        reasons.append(
            "job 在极短时间内失败且步骤数为 0 => runner 从未启动，"
            "排除代码/步骤级故障。典型原因是账单或配额被拒。"
        )
        if d.get("private"):
            reasons.append(
                "仓库为 private，受 2000 分钟/月免费额度约束（public 仓库无限量免费）。"
            )
        ue = out.get("usage_estimate")
        if ue and ue.get("exceeds_free_quota"):
            reasons.append(
                f"按真实历史时长测算，当前频率月耗约 {ue['minutes_per_30d']} 分钟 "
                f"> 免费额度 {ue['free_quota']} 分钟，约 {ue['quota_exhausted_after_days']} 天耗尽 => 高度吻合配额耗尽。"
            )
        elif ue:
            reasons.append(
                f"按真实历史时长测算月耗约 {ue['minutes_per_30d']} 分钟，未超免费额度 "
                f"{ue['free_quota']}，配额耗尽的解释力较弱，需优先核查账单状态/支付方式失效。"
            )
    elif d.get("failure_job_probe"):
        reasons.append("失败 job 存在步骤（steps>0）=> 属步骤级/代码级失败，应查具体步骤日志。")
    else:
        reasons.append("未取到失败 job 探测数据，无法判断。")

    if d.get("billing_api") == "unavailable (404/insufficient scope)":
        reasons.append(
            "账单 API 无权限，无法程序化证实额度状态；需在 GitHub Settings → Billing "
            "页面人工确认（本判断为间接推断，不作绝对断言）。"
        )

    out["diagnosis"] = reasons
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    args = ap.parse_args()

    data = collect()
    data.update(analyse(data))

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    print(f"仓库: {data['repo']}  private={data['private']}  "
          f"archived={data['archived']}  disabled={data['disabled']}")
    print(f"采样运行数: {data['runs_fetched']} / 总数 {data['runs_total']}")
    print(f"结论分布: {data['conclusions']}")
    print(f"最后一次成功: {data['last_success_at']}")
    print(f"连续失败: {data['failure_streak_len']} 次"
          f"({data['failure_streak_first_at']} → {data['failure_streak_last_at']})")
    print()
    print("失败 job 探测（步骤数为 0 说明 runner 未启动）:")
    for p in data["failure_job_probe"]:
        print(f"  run {p['run_id']} @ {p['created_at']}  "
              f"concl={p['job_conclusion']}  steps={p['steps']}  {p['job_seconds']}s")
    print()
    print("历史成功运行真实时长:")
    for t in data["success_timings"]:
        print(f"  {t['created_at']}  run_duration_ms={t['run_duration_ms']}  "
              f"billable_ubuntu_ms={t['billable_ubuntu_ms']}")
    print()
    ue = data.get("usage_estimate")
    if ue:
        print("用量测算（可复现）:")
        for k, v in ue.items():
            print(f"  {k}: {v}")
    print()
    print("Secrets 更新时间:")
    for s in data["secrets"]:
        print(f"  {s['name']}: {s['updated_at']}")
    print()
    print("根因判断:")
    for r in data["diagnosis"]:
        print(f"  - {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
