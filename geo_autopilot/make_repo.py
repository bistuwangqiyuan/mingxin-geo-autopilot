# -*- coding: utf-8 -*-
"""中科存储 GEO Autopilot · 自治仓库装配器（make_repo.py）。

把运行所需的最小引擎集合装配成一个可推送的 git 仓库 zk-geo-autopilot：
  repo/
    .github/workflows/geo-autopilot.yml   (从 geo_autopilot/.github 提升到根)
    geo_autopilot/                         (引擎主体)
    geo_plan/  seo_geo_loop/               (测量与构建)
    business_plan/outputs/results.json     (单一事实源)
    README.md  SETUP.md

CI 中再把 official_website / zk-storage-kb clone 为同级目录，paths.py 零改动解析。

用法：
  python make_repo.py                  # 装配到 ../zk-geo-autopilot 并 git init+commit
  python make_repo.py --dest <PATH>    # 指定目标目录
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

import paths

IGNORE = shutil.ignore_patterns(
    "__pycache__", "*.pyc", "*.bak.*", "node_modules", ".venv", "_sites", ".env")


def _copytree(src, dst):
    if not os.path.isdir(src):
        print(f"  [warn] 源不存在，跳过: {src}")
        return
    shutil.copytree(src, dst, ignore=IGNORE, dirs_exist_ok=True)


def assemble(dest, do_git=True):
    os.makedirs(dest, exist_ok=True)
    print(f"[make_repo] 目标: {dest}")

    # 1. geo_autopilot 主体（含 history/reports/outputs 真实产物）
    _copytree(paths.AUTOPILOT_DIR, os.path.join(dest, "geo_autopilot"))

    # 2. 把 workflow 提升到仓库根 .github
    src_wf = os.path.join(dest, "geo_autopilot", ".github")
    dst_gh = os.path.join(dest, ".github")
    if os.path.isdir(src_wf):
        _copytree(src_wf, dst_gh)
        shutil.rmtree(src_wf, ignore_errors=True)

    # 3. 引擎
    _copytree(paths.GEO_PLAN, os.path.join(dest, "geo_plan"))
    _copytree(paths.LOOP, os.path.join(dest, "seo_geo_loop"))

    # 4. 单一事实源
    rj_dst = os.path.join(dest, "business_plan", "outputs")
    os.makedirs(rj_dst, exist_ok=True)
    if os.path.isfile(paths.RESULTS_JSON):
        shutil.copy2(paths.RESULTS_JSON, os.path.join(rj_dst, "results.json"))

    # 5. 根 README + .gitignore
    _write_root_readme(dest)
    _write_root_gitignore(dest)

    if do_git:
        _git_init(dest)
    print("[make_repo] 装配完成。")
    return dest


def _write_root_readme(dest):
    with open(os.path.join(dest, "README.md"), "w", encoding="utf-8") as f:
        f.write(
            "# zk-geo-autopilot\n\n"
            "中科存储官网 **全自动 AI GEO 系统**（云端每日无人值守）。\n\n"
            "- 引擎与编排见 [`geo_autopilot/`](geo_autopilot/)（入口 `autopilot.py`）。\n"
            "- 每日由 GitHub Actions cron 运行：真实 GVI 重测 → AI 决策与内容自进化（经 verify 闸门）→ "
            "重建并部署官网/知识库 → IndexNow → 历史快照 → 苹果视觉日报 HTML/PDF → 告警。\n"
            "- 一次性密钥配置见 [`SETUP.md`](SETUP.md)。\n\n"
            "纪律：所有数值可复现、单一事实源；预测标注「规划假设、非承诺」；"
            "受客观约束的人工项（GSC/UGC/ICP）如实开 Issue 告警，绝不伪造完成。\n")


def _write_root_gitignore(dest):
    with open(os.path.join(dest, ".gitignore"), "w", encoding="utf-8") as f:
        f.write("__pycache__/\n*.pyc\n.venv/\nnode_modules/\n_sites/\n.env\n"
                "official_website/\noffsite_github/\n*.bak.*\n")


def _git_init(dest):
    if shutil.which("git") is None:
        print("  [warn] 未找到 git，跳过 init")
        return
    if not os.path.isdir(os.path.join(dest, ".git")):
        subprocess.run(["git", "init"], cwd=dest, check=False, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=False, capture_output=True)
    r = subprocess.run(["git", "commit", "-m", "chore: assemble GEO autopilot engine"],
                       cwd=dest, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("  git:", (r.stdout or r.stderr or "").strip().splitlines()[-1:] or "committed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=os.path.join(os.path.dirname(paths.ROOT), "zk-geo-autopilot"))
    ap.add_argument("--no-git", action="store_true")
    args = ap.parse_args()
    assemble(os.path.abspath(args.dest), do_git=not args.no_git)
    print("\n下一步（人工一次）：")
    print("  1. gh repo create zk-geo-autopilot --private --source . --push   # 在目标目录内")
    print("  2. 配置仓库 Secrets：DASHSCOPE_API_KEY、GH_PAT（见 SETUP.md）")
    print("  3. gh workflow run 'GEO Autopilot (daily)'   # 手动首跑验证")


if __name__ == "__main__":
    main()
