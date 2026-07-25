# -*- coding: utf-8 -*-
"""引擎仓库标识的单一来源。

历史教训：仓库名曾以字面量散落在 6 个诊断脚本 + tests + alerting 里，
2026-07-26 从 zk-geo-autopilot 迁到 mingxin-geo-autopilot 时得逐处翻找。
这里收口一次，以后改名只动这一个文件（或设 MX_REPO 环境变量）。

在 GitHub Actions 里无需设 MX_REPO：workflow 已把 github.repository 注入
MX_ALERT_REPO，本模块会自动采纳，因此 fork 或再次改名都能自适应。
"""
from __future__ import annotations

import os

DEFAULT_REPO = "bistuwangqiyuan/mingxin-geo-autopilot"

# 归档的前身，保留仅为让历史文档与事故复盘中的引用可被检索到。
LEGACY_REPO = "bistuwangqiyuan/zk-geo-autopilot"

WORKFLOW_PATH = ".github/workflows/geo-autopilot.yml"


def repo_slug() -> str:
    """按 MX_REPO → MX_ALERT_REPO(CI 注入) → 默认值 的顺序解析 owner/name。"""
    for key in ("MX_REPO", "MX_ALERT_REPO"):
        v = (os.environ.get(key) or "").strip()
        if v:
            return v
    return DEFAULT_REPO
