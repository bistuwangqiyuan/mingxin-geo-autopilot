"""按仓库测算账户级 GitHub Actions 分钟消耗（当月），定位真实消耗源。

背景：Actions 免费额度（私有仓库 2000 分钟/月）是**账户级共享**的，
不是每仓库独立。单看一个仓库的用量无法解释额度耗尽，必须全账户汇总。

计费口径（GitHub 官方，2026-07 核对）：
  - 仅**私有**仓库消耗额度；public 仓库使用 GitHub 托管 runner 免费且无限量
  - Linux(ubuntu) 倍率 1x，Windows 2x，macOS 10x
  - 每个 **job** 的时长按分钟向上取整后计费

本脚本用各仓库 runs 的 timing.billable 数据汇总，无该数据时回退到
run_duration_ms 并标注为估算。输出 JSON 便于第三方复算。

用法:
    python scripts/actions_usage_account.py                # 当月
    python scripts/actions_usage_account.py --since 2026-07-01
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timezone

MULTIPLIER = {"UBUNTU": 1, "WINDOWS": 2, "MACOS": 10}


def gh(endpoint: str):
    p = subprocess.run(
        ["gh", "api", endpoint], capture_output=True, text=True, encoding="utf-8"
    )
    if p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return None


def gh_paginate(endpoint: str, key: str | None = None, cap: int = 500):
    """分页拉取，cap 为最大条目数上限，防止无界请求。"""
    items: list = []
    page = 1
    while len(items) < cap:
        sep = "&" if "?" in endpoint else "?"
        d = gh(f"{endpoint}{sep}per_page=100&page={page}")
        if d is None:
            break
        batch = d.get(key, []) if key else d
        if not isinstance(batch, list) or not batch:
            break
        items.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return items[:cap]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--since",
        help="起始日期 YYYY-MM-DD，默认当月 1 日（对齐 GitHub 账单周期的近似）",
    )
    ap.add_argument("--json", action="store_true")
    # 由脚本自己写文件：Windows PowerShell 的 `>` 重定向会写成 UTF-16，
    # 导致后续用 UTF-8 解析报告失败。
    ap.add_argument("--out", help="把 JSON 报告写入该路径（UTF-8）")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    since = (
        datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
        if args.since
        else now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    )

    # cap 必须远大于实际仓库数：若枚举被截断，用量合计会偏低而得出"未超额"的错误结论。
    REPO_CAP = 5000
    repos = gh_paginate("user/repos?affiliation=owner", None, cap=REPO_CAP)
    if len(repos) >= REPO_CAP:
        report_truncated = True
    else:
        report_truncated = False
    private = [r for r in repos if r.get("private")]

    # 只对统计窗口前后有过推送的仓库拉运行记录（纯静态仓库不会有 Actions 运行），
    # 否则对数百个仓库逐个拉 timing 会产生数千次 API 调用。
    # 注意：定时 cron 可在无推送时运行，故窗口放宽到 since 前 180 天。
    from datetime import timedelta

    push_floor = since - timedelta(days=180)
    candidates = [
        r
        for r in private
        if r.get("pushed_at")
        and datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00")) >= push_floor
    ]

    report = {
        "generated_at": now.isoformat(),
        "since": since.isoformat(),
        "repos_total": len(repos),
        "repos_private": len(private),
        "repos_scanned": len(candidates),
        "repo_enumeration_truncated": report_truncated,
        "per_repo": [],
        "notes": [],
    }

    grand_billed = 0
    for r in candidates:
        full = r["full_name"]
        runs = gh_paginate(f"repos/{full}/actions/runs", "workflow_runs", cap=300)
        recent = [
            x
            for x in runs
            if datetime.fromisoformat(x["created_at"].replace("Z", "+00:00")) >= since
        ]
        if not recent:
            continue

        billed = 0
        estimated = False
        # 逐 run 取 timing；数据量大时按 job 汇总更准，这里用 run 级 billable
        for x in recent:
            t = gh(f"repos/{full}/actions/runs/{x['id']}/timing")
            if not t:
                continue
            b = t.get("billable") or {}
            run_billed = 0
            for env, info in b.items():
                ms = (info or {}).get("total_ms") or 0
                run_billed += math.ceil(ms / 60000) * MULTIPLIER.get(env, 1)
            if run_billed == 0 and t.get("run_duration_ms"):
                # billable 为 0：可能是 GitHub 未回填，用墙钟时长做上界估算
                run_billed = math.ceil(t["run_duration_ms"] / 60000)
                estimated = True
            billed += run_billed

        grand_billed += billed
        report["per_repo"].append(
            {
                "repo": full,
                "runs_since": len(recent),
                "billed_minutes": billed,
                "contains_estimated": estimated,
            }
        )

    report["per_repo"].sort(key=lambda x: -x["billed_minutes"])
    report["total_billed_minutes_private"] = grand_billed
    report["free_quota_minutes"] = 2000
    report["over_quota"] = grand_billed > 2000
    report["notes"].append(
        "billable 为 0 的运行用 run_duration_ms 向上取整做上界估算，已标注 contains_estimated。"
    )
    report["notes"].append(
        "public 仓库不计入（GitHub 托管 runner 对 public 仓库免费无限量）。"
    )
    if report_truncated:
        report["notes"].append(
            "警告：仓库枚举达到上限可能被截断，合计值为下界，不能据此断言未超额。"
        )

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"已写入 {args.out}")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"统计区间: {since.date()} → {now.date()}（UTC）")
    print(f"仓库: 共 {report['repos_total']} 个，其中私有 {report['repos_private']} 个，"
          f"实际扫描 {report['repos_scanned']} 个（近 180 天有推送）")
    if report_truncated:
        print("警告: 仓库枚举可能被截断，合计值为下界")
    print()
    print(f"{'仓库':<45} {'运行数':>7} {'计费分钟':>9}  估算")
    for row in report["per_repo"]:
        print(f"{row['repo']:<45} {row['runs_since']:>7} {row['billed_minutes']:>9}"
              f"  {'是' if row['contains_estimated'] else ''}")
    print()
    print(f"私有仓库合计计费分钟: {grand_billed} / 免费额度 2000  "
          f"=> {'已超额' if report['over_quota'] else '未超额'}")
    for n in report["notes"]:
        print(f"注: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
