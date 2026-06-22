# -*- coding: utf-8 -*-
"""中科存储 GEO Autopilot · 环境自适应路径解析（单一来源）。

本地开发：引擎(geo_plan/seo_geo_loop)与站点(official_website/offsite_github)为同级目录。
CI(GitHub Actions)：站点仓库被 clone 到 workspace，路径经环境变量覆盖。

所有 autopilot 模块统一从这里取路径，禁止各自硬编码。
"""
from __future__ import annotations

import os

AUTOPILOT_DIR = os.path.dirname(os.path.abspath(__file__))
# 工程根：本地为 microai/；引擎与站点目录默认在根下。
ROOT = os.environ.get("ZK_WORKSPACE_ROOT") or os.path.dirname(AUTOPILOT_DIR)


def _resolve(env_key, default_rel):
    v = os.environ.get(env_key)
    if v:
        return os.path.abspath(v)
    return os.path.join(ROOT, default_rel)


# 引擎（可复现测量与构建）
GEO_PLAN = _resolve("ZK_GEO_PLAN", "geo_plan")
LOOP = _resolve("ZK_LOOP", "seo_geo_loop")

# 站点仓库（部署目标）
OFFICIAL_WEBSITE = _resolve("ZK_OFFICIAL_WEBSITE", "official_website")
KB_REPO = _resolve("ZK_KB_REPO", "offsite_github")
OFFSITE_SITE = _resolve("ZK_OFFSITE_SITE", "offsite_site")

# autopilot 自身数据
OUTPUTS = os.path.join(AUTOPILOT_DIR, "outputs")
HISTORY = os.path.join(AUTOPILOT_DIR, "history")
REPORTS = os.path.join(AUTOPILOT_DIR, "reports")
FIGURES = os.path.join(OUTPUTS, "figures")

# 关键单一事实源
RESULTS_JSON = os.path.join(ROOT, "business_plan", "outputs", "results.json")
GEO_BASELINE = os.path.join(GEO_PLAN, "outputs", "geo_baseline.json")
GVI_COMPARE = os.path.join(LOOP, "outputs", "gvi_compare.json")
LIVE_STATUS = os.path.join(LOOP, "outputs", "live_status.json")
SOURCE_GAP = os.path.join(GEO_PLAN, "outputs", "source_gap.json")
OFFSITE_PUBLISHED = os.path.join(LOOP, "outputs", "offsite_published.json")

# 站点公开地址（实测可达，用于 live 校验）
SITE_URL = os.environ.get("ZK_SITE_URL", "https://goni.top")
KB_URL = os.environ.get("ZK_KB_URL", "https://bistuwangqiyuan.github.io/zk-storage-kb/")

# 远程仓库（CI clone/push 目标）
OFFICIAL_WEBSITE_REMOTE = os.environ.get(
    "ZK_OFFICIAL_WEBSITE_REMOTE",
    "https://github.com/bistuwangqiyuan/zhongke-dpu-official.git",
)
KB_REMOTE = os.environ.get(
    "ZK_KB_REMOTE",
    "https://github.com/bistuwangqiyuan/zk-storage-kb.git",
)


def ensure_dirs():
    for d in (OUTPUTS, HISTORY, REPORTS, FIGURES):
        os.makedirs(d, exist_ok=True)


def summary():
    """返回路径解析快照（供日志/调试，绝不打印密钥）。"""
    return {
        "ROOT": ROOT,
        "GEO_PLAN": GEO_PLAN,
        "LOOP": LOOP,
        "OFFICIAL_WEBSITE": OFFICIAL_WEBSITE,
        "KB_REPO": KB_REPO,
        "exists": {
            "geo_plan": os.path.isdir(GEO_PLAN),
            "seo_geo_loop": os.path.isdir(LOOP),
            "official_website": os.path.isdir(OFFICIAL_WEBSITE),
            "kb_repo": os.path.isdir(KB_REPO),
            "results_json": os.path.isfile(RESULTS_JSON),
        },
    }


if __name__ == "__main__":
    import json
    print(json.dumps(summary(), ensure_ascii=False, indent=2))
