"""判定 Actions 是否在仓库/账户层面被关闭。

为什么需要它：运行记录归零有两种完全不同的解释——「从未触发」和「Actions 被关闭
导致 API 不再返回记录」。二者处置方式不同，不能靠猜。本脚本直接读权限端点给出答案。

复现：python scripts/actions_enabled.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from repo_target import repo_slug

REPO = repo_slug()
OUT = Path("reports/actions_enabled.json")


def gh(path: str) -> tuple[int, object]:
    p = subprocess.run(
        ["gh", "api", path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if p.returncode != 0:
        return p.returncode, p.stderr[:500]
    try:
        return 0, json.loads(p.stdout)
    except json.JSONDecodeError:
        return 0, p.stdout[:500]


def main() -> int:
    report = {}
    for label, path in [
        ("repo_actions_permissions", f"repos/{REPO}/actions/permissions"),
        ("owner_actions_permissions", "user/settings/actions/permissions"),
        ("repo_meta", f"repos/{REPO}"),
    ]:
        rc, data = gh(path)
        if label == "repo_meta" and isinstance(data, dict):
            data = {
                k: data.get(k)
                for k in ("private", "archived", "disabled", "pushed_at", "has_issues")
            }
        report[label] = {"rc": rc, "data": data}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
