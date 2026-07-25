"""抓取失败运行的 GitHub 侧错误注解（annotations），用于定论根因。

job 步骤数为 0 时日志为空，唯一可得的官方错误说明在 check-run annotations 里。

用法: python scripts/actions_annotations.py [run_id ...]
不传 run_id 时自动取最近 3 次失败运行。
"""
from __future__ import annotations

import json
import subprocess
import sys

REPO = "bistuwangqiyuan/zk-geo-autopilot"


def gh(endpoint: str):
    p = subprocess.run(
        ["gh", "api", endpoint], capture_output=True, text=True, encoding="utf-8"
    )
    if p.returncode != 0:
        return {"_error": p.stderr.strip()[:300]}
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"_raw": p.stdout[:300]}


def recent_failures(n: int = 3) -> list[int]:
    d = gh(f"repos/{REPO}/actions/runs?status=failure&per_page={n}")
    return [r["id"] for r in d.get("workflow_runs", [])]


def main() -> int:
    ids = [int(a) for a in sys.argv[1:]] or recent_failures()
    for run_id in ids:
        print(f"===== run {run_id} =====")
        run = gh(f"repos/{REPO}/actions/runs/{run_id}")
        print(f"  created_at   : {run.get('created_at')}")
        print(f"  conclusion   : {run.get('conclusion')}")
        print(f"  run_attempt  : {run.get('run_attempt')}")
        print(f"  check_suite  : {run.get('check_suite_id')}")

        jobs = gh(f"repos/{REPO}/actions/runs/{run_id}/jobs")
        for j in jobs.get("jobs", []):
            print(f"  job {j['id']}  concl={j.get('conclusion')}  steps={len(j.get('steps', []))}")
            ann = gh(f"repos/{REPO}/check-runs/{j['id']}/annotations")
            if isinstance(ann, list) and ann:
                for a in ann:
                    print(f"    [{a.get('annotation_level')}] {a.get('title')}")
                    print(f"      {a.get('message')}")
            else:
                print(f"    (no annotations: {ann})")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
