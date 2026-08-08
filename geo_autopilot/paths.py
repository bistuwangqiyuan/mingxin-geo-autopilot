# -*- coding: utf-8 -*-
"""铭信 GEO Autopilot · 环境自适应路径解析（单一来源）。

本地开发：引擎(geo_plan/seo_geo_loop)与站点(official_website/offsite_github)为同级目录。
CI(GitHub Actions)：站点仓库被 clone 到 workspace，路径经环境变量覆盖。

官网本体：bistuwangqiyuan/amd 仓库（Next.js 源码位于其 site/ 子目录），
Vercel 项目 mingxin-site 部署为 https://mingxinstorage.xyz（CLI/Deploy Hook 部署，
未连 GitHub 自动构建）。

所有 autopilot 模块统一从这里取路径，禁止各自硬编码。
"""
from __future__ import annotations

import os

AUTOPILOT_DIR = os.path.dirname(os.path.abspath(__file__))
# 工程根：本地目录名仍是 zk-geo-autopilot/（磁盘路径，未随 GitHub 仓库改名而变，
# 远端已是 mingxin-geo-autopilot）；引擎与站点目录默认在根下。
ROOT = os.environ.get("MX_WORKSPACE_ROOT") or os.path.dirname(AUTOPILOT_DIR)


def _resolve(env_key, default_rel):
    v = os.environ.get(env_key)
    if v:
        return os.path.abspath(v)
    return os.path.join(ROOT, default_rel)


# 引擎（可复现测量与构建）
GEO_PLAN = _resolve("MX_GEO_PLAN", "geo_plan")
LOOP = _resolve("MX_LOOP", "seo_geo_loop")

# 站点仓库（**仅本地开发时可能存在**）。CI 不再 clone 私有的 amd 仓库：
# 内容产出改经 HTTP 提交给站点接口，见 AUTOPILOT_FAQ_URL。保留这几个常量是为了
# 本地跑 --once 时仍能按老布局解析路径，线上不依赖它们。
OFFICIAL_WEBSITE = _resolve("MX_OFFICIAL_WEBSITE", "official_website")
SITE_SUBDIR = os.environ.get("MX_SITE_SUBDIR", "site")
SITE_SRC = os.path.join(OFFICIAL_WEBSITE, SITE_SUBDIR)  # Next.js 站点根（package.json 所在）
KB_REPO = _resolve("MX_KB_REPO", "offsite_github")
OFFSITE_SITE = _resolve("MX_OFFSITE_SITE", "offsite_site")

# autopilot 自身数据
OUTPUTS = os.path.join(AUTOPILOT_DIR, "outputs")
HISTORY = os.path.join(AUTOPILOT_DIR, "history")
REPORTS = os.path.join(AUTOPILOT_DIR, "reports")
FIGURES = os.path.join(OUTPUTS, "figures")

# 内容自进化产出：本仓库内的单一依据（去重 + metrics 口径），随每次运行提交入库。
# 上线副本在站点数据库里，由 AUTOPILOT_FAQ_URL 接口写入。
AUTOPILOT_FAQ = os.path.join(OUTPUTS, "autopilot_faq.json")

# 关键单一事实源
RESULTS_JSON = os.path.join(ROOT, "business_plan", "outputs", "results.json")
GEO_BASELINE = os.path.join(GEO_PLAN, "outputs", "geo_baseline.json")
GVI_COMPARE = os.path.join(LOOP, "outputs", "gvi_compare.json")
LIVE_STATUS = os.path.join(LOOP, "outputs", "live_status.json")
SOURCE_GAP = os.path.join(GEO_PLAN, "outputs", "source_gap.json")
OFFSITE_PUBLISHED = os.path.join(LOOP, "outputs", "offsite_published.json")

# 站点公开地址（实测可达，用于 live 校验）
SITE_URL = os.environ.get("MX_SITE_URL", "https://mingxinstorage.xyz")
KB_URL = os.environ.get("MX_KB_URL", "https://bistuwangqiyuan.github.io/mingxin-storage-kb/")

# 远程仓库（CI clone/push 目标）
OFFICIAL_WEBSITE_REMOTE = os.environ.get(
    "MX_OFFICIAL_WEBSITE_REMOTE",
    "https://github.com/bistuwangqiyuan/amd.git",
)
KB_REMOTE = os.environ.get(
    "MX_KB_REMOTE",
    "https://github.com/bistuwangqiyuan/mingxin-storage-kb.git",
)

# 站点自带引擎/SEO 接口（Bearer CRON_SECRET）：
#   POST {SITE_URL}/api/seo/ping     触发 IndexNow/百度推送/WebSub（站点自持 INDEXNOW_KEY）
#   GET  {SITE_URL}/api/engine/*     内容引擎（生成/审计/快照，由站点自身 cron 驱动）
CRON_SECRET = os.environ.get("CRON_SECRET", "")
SEO_PING_URL = f"{SITE_URL}/api/seo/ping"
#   POST {SITE_URL}/api/engine/autopilot-faq  内容自进化条目落库（取代写官网仓库）
AUTOPILOT_FAQ_URL = f"{SITE_URL}/api/engine/autopilot-faq"

# Vercel 部署触发（可选）：项目未连 GitHub，push 后需 Deploy Hook 或 vercel CLI 触发。
VERCEL_DEPLOY_HOOK_URL = os.environ.get("VERCEL_DEPLOY_HOOK_URL", "")


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
        "SITE_SRC": SITE_SRC,
        "KB_REPO": KB_REPO,
        "SITE_URL": SITE_URL,
        "exists": {
            "geo_plan": os.path.isdir(GEO_PLAN),
            "seo_geo_loop": os.path.isdir(LOOP),
            "official_website": os.path.isdir(OFFICIAL_WEBSITE),
            "site_src": os.path.isdir(SITE_SRC),
            "kb_repo": os.path.isdir(KB_REPO),
            "results_json": os.path.isfile(RESULTS_JSON),
        },
        "secrets_present": {
            "cron_secret": bool(CRON_SECRET),
            "vercel_deploy_hook": bool(VERCEL_DEPLOY_HOOK_URL),
        },
    }


if __name__ == "__main__":
    import json
    print(json.dumps(summary(), ensure_ascii=False, indent=2))
