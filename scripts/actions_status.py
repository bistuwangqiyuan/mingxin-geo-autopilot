"""站外引擎当前运行状态快照。

为什么单独写这个脚本：actions_diagnose.py 按 **workflow 文件名** 查运行记录，
而 GitHub 在 workflow 文件内容变更后会重新注册 workflow id，按文件名查有时返回 0 条，
容易被误读成"从未运行过"。本脚本改为查仓库级 runs 再按 path 过滤，口径更稳。

输出写文件而非 stdout：Windows PowerShell 管道会把 UTF-8 中文压成乱码，
写文件再读是唯一可靠的方式。

复现：python scripts/actions_status.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = "bistuwangqiyuan/zk-geo-autopilot"
WORKFLOW_PATH = ".github/workflows/geo-autopilot.yml"
OUT = Path("reports/actions_status.json")


def gh(path: str) -> dict:
    p = subprocess.run(
        ["gh", "api", path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if p.returncode != 0:
        raise SystemExit(f"gh api {path} 失败: {p.stderr[:400]}")
    return json.loads(p.stdout)


def main() -> int:
    workflows = gh(f"repos/{REPO}/actions/workflows")["workflows"]
    target = next((w for w in workflows if w["path"] == WORKFLOW_PATH), None)

    data = gh(f"repos/{REPO}/actions/runs?per_page=30")
    all_runs = data.get("workflow_runs", [])
    runs = [r for r in all_runs if r.get("path") == WORKFLOW_PATH]

    # 按 workflow id 再查一次：两条口径不一致时说明过滤条件有问题，而不是真的没运行过
    by_id = (
        gh(f"repos/{REPO}/actions/workflows/{target['id']}/runs?per_page=30") if target else {}
    )

    last_success = next((r for r in runs if r.get("conclusion") == "success"), None)
    consecutive_failures = 0
    for r in runs:
        if r.get("conclusion") == "success":
            break
        if r.get("conclusion") in ("failure", "startup_failure"):
            consecutive_failures += 1

    report = {
        "repo": REPO,
        "workflow_registered": bool(target),
        "workflow_state": target.get("state") if target else None,
        "workflow_id": target.get("id") if target else None,
        "repo_runs_total_count": data.get("total_count"),
        "repo_runs_returned": len(all_runs),
        "repo_runs_paths": sorted({r.get("path") for r in all_runs}),
        "by_workflow_id_total_count": by_id.get("total_count"),
        "by_workflow_id_returned": len(by_id.get("workflow_runs", [])),
        "runs_seen": len(runs),
        "consecutive_failures": consecutive_failures,
        "last_success_at": last_success.get("updated_at") if last_success else None,
        "recent": [
            {
                "created_at": r["created_at"],
                "conclusion": r.get("conclusion"),
                "event": r.get("event"),
                "url": r.get("html_url"),
            }
            for r in runs[:8]
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
