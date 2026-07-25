# -*- coding: utf-8 -*-
"""开跑前自检：引擎仓库的 secrets 是否齐备到足以跑通。

为什么需要它：workflow 跑满一轮要几十分钟，而「缺一个密钥」这种错误在第 3 步
就注定失败。与其触发一次撞一次墙，不如先用一次 API 调用把结论问出来。

口径：`gh secret list` 只返回**名字**不返回值，所以本脚本只能判断「配没配」，
判断不了「值对不对」。值是否有效由运行时验证（例如 GH_PAT 权限不足会在
clone 步骤报错）。这一点必须如实说明，不要把本脚本的 READY 当成万事大吉。

用法：
    python scripts/verify_secrets.py            # 人看的报告
    python scripts/verify_secrets.py --strict   # 缺必需项时 exit 1，供 CI/定时任务判定
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

from repo_target import repo_slug

# 缺了就跑不动。目前只有一个：官网仓库 amd 是私有的，没有它 clone 步骤即失败。
REQUIRED = {
    "GH_PAT": "clone 私有仓库 amd 与知识库；缺失则流水线在第 3 步即失败",
}

# 缺了照样跑绿，但某条链是断的——**这比直接失败更危险**，因为它不报错。
# 例：indexnow_submit.py 无 CRON_SECRET 时返回 0 并写下 "跳过站点 /api/seo/ping"，
# 流水线一路 success，而收录提交其实一次都没发生过。故在此逐条点名。
DEGRADED = {
    "CRON_SECRET": "站点 /api/seo/ping 与 /api/engine/*；缺失则收录提交静默跳过（不报错）",
    "VERCEL_DEPLOY_HOOK_URL": "官网 Vercel 未连 GitHub 自动构建；缺失则改动推上去也不会上线",
    "GA4_PROPERTY_ID": "流量信号闭环；缺失则 traffic_check 恒返回 ga4_not_configured",
    "GA4_SA_JSON": "同上，需与 GA4_PROPERTY_ID 成对提供",
    "MX_GA4_ID": "页面埋码 Measurement ID",
    "AI_GATEWAY_API_KEY": "AI 网关；缺失则回落到各家直连 key（有直连 key 即无损）",
}

# 至少要有一个能用的生成模型，否则内容生产环节整体空转。
MODEL_KEYS = [
    "DEEPSEEK_API_KEY", "GLM_API_KEY", "MOONSHOT_API_KEY", "TONGYI_API_KEY",
    "DASHSCOPE_API_KEY", "HUNYUAN_API_KEY", "SPARK_API_KEY", "DOUBAO_API_KEY",
    "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
]


def existing_secret_names(repo: str) -> set[str]:
    out = subprocess.run(
        ["gh", "secret", "list", "--repo", repo, "--json", "name"],
        capture_output=True, text=True, encoding="utf-8",
    )
    if out.returncode != 0:
        print(f"[verify] 无法读取 {repo} 的 secrets 列表：{out.stderr.strip()}")
        sys.exit(2)
    return {row["name"] for row in json.loads(out.stdout or "[]")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true",
                    help="缺必需项时以退出码 1 结束，便于被自动化判定")
    args = ap.parse_args()

    repo = repo_slug()
    have = existing_secret_names(repo)
    print(f"[verify] 仓库 {repo}，已配置 {len(have)} 个 secret\n")

    missing_required = [k for k in REQUIRED if k not in have]
    print("必需（缺失即流水线失败）：")
    for k, why in REQUIRED.items():
        print(f"  {'OK  ' if k in have else 'MISS'}  {k:<24} {why}")

    degraded = [k for k in DEGRADED if k not in have]
    print("\n可选（缺失不报错，但对应链路静默失效）：")
    for k, why in DEGRADED.items():
        print(f"  {'OK  ' if k in have else '断链'}  {k:<24} {why}")

    models = [k for k in MODEL_KEYS if k in have]
    print(f"\n模型密钥 {len(models)}/{len(MODEL_KEYS)}：{', '.join(models) or '无'}")
    if not models:
        missing_required.append("<任一模型密钥>")

    print()
    if missing_required:
        print(f"[verify] NOT READY：缺 {', '.join(missing_required)}")
    else:
        print("[verify] READY：必需项齐备，可以触发运行。")
    if degraded:
        print(f"[verify] 但有 {len(degraded)} 条链路会静默失效：{', '.join(degraded)}")
    print("[verify] 口径声明：本脚本只验证「配没配」，验证不了「值对不对」。"
          "PAT 是否过期、权限是否够，只能由实际运行验证。")
    return 1 if (missing_required and args.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())
