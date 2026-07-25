"""判定 Actions 被拒是"账户级"还是"本仓库级"。

方法：取账户内近期有活动的私有仓库，统计各自在分界时刻前后的成功/失败分布。
若多个互不相关的仓库在同一时刻集体转为失败，则为账户级（账单/付款）原因；
若仅本仓库失败，则为仓库级原因。

用法: python scripts/actions_account_health.py --cutoff 2026-07-21T00:00:00Z
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone

from repo_target import LEGACY_REPO, repo_slug

# 账户内近期活跃的私有仓库（由 actions_usage_account.py 的输出得到）。
# 保留已归档的 LEGACY_REPO：本脚本判定的是"账户级还是仓库级"，历史对照样本
# 恰恰是判据的一部分，删掉反而削弱结论。
REPOS = [
    repo_slug(),
    LEGACY_REPO,
    "bistuwangqiyuan/mingxin-marketing-cron",
    "bistuwangqiyuan/aiseoauto",
    "bistuwangqiyuan/amd",
    "bistuwangqiyuan/aiteams",
]

BILLING_MSG = "recent account payments have failed"


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


def dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutoff", default="2026-07-21T00:00:00Z")
    args = ap.parse_args()
    cutoff = dt(args.cutoff)

    print(f"分界时刻: {cutoff.isoformat()}")
    print()
    account_level_hits = 0
    for repo in REPOS:
        d = gh(f"repos/{repo}/actions/runs?per_page=100")
        if not d:
            print(f"{repo}: 无法读取")
            continue
        runs = d.get("workflow_runs", [])
        before = Counter(
            r.get("conclusion") for r in runs if dt(r["created_at"]) < cutoff
        )
        after = Counter(
            r.get("conclusion") for r in runs if dt(r["created_at"]) >= cutoff
        )

        # 取分界后一次失败运行，看是否为账单类注解
        billing_flag = ""
        after_failures = [
            r
            for r in runs
            if dt(r["created_at"]) >= cutoff and r.get("conclusion") == "failure"
        ]
        if after_failures:
            jobs = gh(f"repos/{repo}/actions/runs/{after_failures[0]['id']}/jobs") or {}
            for j in jobs.get("jobs", []):
                ann = gh(f"repos/{repo}/check-runs/{j['id']}/annotations")
                if isinstance(ann, list):
                    for a in ann:
                        if BILLING_MSG in (a.get("message") or ""):
                            billing_flag = "  <== 账单类拒绝"
                            break
        if billing_flag:
            account_level_hits += 1

        print(f"{repo}")
        print(f"   分界前: {dict(before) or '无运行'}")
        print(f"   分界后: {dict(after) or '无运行'}{billing_flag}")

    print()
    print(f"出现账单类拒绝的仓库数: {account_level_hits} / {len(REPOS)}")
    if account_level_hits >= 2:
        print("结论: 账户级账单/付款问题（多个无关仓库同时被拒），非本仓库配置问题。")
    elif account_level_hits == 1:
        print("结论: 仅本仓库出现账单类拒绝，需进一步区分（可能其他仓库分界后无运行）。")
    else:
        print("结论: 未发现账单类拒绝注解。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
