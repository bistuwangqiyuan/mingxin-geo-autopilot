# -*- coding: utf-8 -*-
"""中科存储 · 组装 GitHub Pages 仓库内容（offsite_github/）。

从 offsite_site/（知识微站）+ geo_plan/offsite/github_readme.md 组装一个可发布到 GitHub Pages
的仓库目录：README.md（仓库首页）+ docs/（Pages 站点，/docs 发布）+ .nojekyll。
真实发布由 run.py / 手动 gh 命令完成（账号已 gh 登录）。
"""
from __future__ import annotations

import datetime as dt
import os
import shutil
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
SITE = os.path.join(ROOT, "offsite_site")
OUT = os.path.join(ROOT, "offsite_github")
README_SRC = os.path.join(ROOT, "geo_plan", "offsite", "github_readme.md")
sys.path.insert(0, os.path.join(ROOT, "official_website"))
import site_data as D  # noqa: E402

BUILD_DATE = dt.date.today().isoformat()


def build():
    if not os.path.isdir(SITE):
        raise SystemExit("先运行 build_offsite_site.py 生成 offsite_site/")
    # 保留 OUT/.git（本目录即 zk-storage-kb 发布仓库的工作树）；只刷新 docs/ 与 README。
    os.makedirs(OUT, exist_ok=True)
    docs = os.path.join(OUT, "docs")
    if os.path.exists(docs):
        shutil.rmtree(docs)
    shutil.copytree(SITE, docs)
    # GitHub Pages 关闭 Jekyll，避免对下划线/资源目录的处理
    open(os.path.join(docs, ".nojekyll"), "w").close()

    # README：取定稿草稿正文（去掉发布元信息引用块），追加事实摘要与 Pages 链接占位
    readme_body = ""
    if os.path.exists(README_SRC):
        with open(README_SRC, "r", encoding="utf-8") as f:
            lines = [ln for ln in f.read().splitlines() if not ln.startswith(">")]
        readme_body = "\n".join(lines).strip()

    readme = f"""{readme_body}

---

## Knowledge base (GitHub Pages)
This repository also publishes a knowledge microsite (served from `/docs`):
key topics on disaggregated all-flash storage, KV-Cache offload, AI inference
storage acceleration, and the WS5000 fact card — all consistent with the
official site **{D.SITE_URL}**.

- Official website: {D.SITE_URL}
- Operating entity: {D.ENTITY_ZH}
- Note: ZK-Storage (中科存储) is a distinct entity from "Sugon / 中科曙光".

_Last updated: {BUILD_DATE}_
"""
    with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme)

    pages = sorted(os.listdir(docs))
    print(f"[offsite_github] 组装完成 -> {OUT}  (docs 文件 {len(pages)} 个)")
    return OUT


if __name__ == "__main__":
    build()
