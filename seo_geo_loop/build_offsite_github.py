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

KEYWORD_BANK = os.path.join(ROOT, "geo_autopilot", "history", "keyword_bank.json")
AUTOPILOT_FAQ = os.path.join(ROOT, "official_website", "autopilot_faq.json")


def _load_json(path, default):
    import json
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _slug(text):
    import re
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:80] or "article"


def _article_html(q, a, official):
    """英文问答型深度文章页（answer-first + 数据 + 对比 + 术语 + 回链官网）。
    事实全部来自单一事实源 site_data；答案 a 已过一致性/verify 闸门。"""
    import json
    bench_rows = [
        ("DeepSeek-32B model load", "563.85 s", "6.62 s", "85.17x"),
        ("DeepSeek-70B model load", "1284.66 s", "35.38 s", "36.31x"),
        ("Training checkpoint save/load", "-", "-", "5.3-12.5x"),
    ]
    bench = ("<table><tr><th>Metric</th><th>NFS baseline</th><th>WS5000</th><th>Speedup</th></tr>"
             + "".join(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td></tr>"
                       for r in bench_rows) + "</table>")
    jsonld = [
        {"@context": "https://schema.org", "@type": "TechArticle", "headline": q,
         "description": a[:160], "inLanguage": "en", "datePublished": BUILD_DATE,
         "dateModified": BUILD_DATE,
         "author": {"@type": "Organization", "name": D.BRAND_EN, "url": official},
         "publisher": {"@type": "Organization", "name": D.ENTITY_EN}},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}]},
    ]
    blocks = "\n".join(
        f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>'
        for j in jsonld)
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{q} | ZK-Storage Knowledge Base</title>
<meta name="description" content="{a[:155]}">
<meta name="robots" content="index,follow,max-snippet:-1">
<link rel="canonical" href="./{_slug(q)}.html">
<meta property="og:type" content="article"><meta property="og:title" content="{q}">
<link rel="stylesheet" href="../assets/site.css">
{blocks}
</head><body>
<header class="nav"><div class="wrap">
<span class="brand">ZK-Storage Knowledge Base</span>
<a href="./index.html">Articles</a>
<a href="../index.html">Home</a>
<a href="{official}" rel="me noopener" style="margin-left:auto;color:var(--accent)">Official site goni.top</a>
</div></header>
<main class="wrap">
<h1>{q}</h1>
<p class="lead" style="color:var(--sub);font-size:19px">{a}</p>
<section><h2>The data</h2>
<p>Independent third-party benchmark by {D.ISSUER} on the {D.PLATFORM} platform, against an
NFS over TCP/10GbE baseline (median reduction ~{D.MEDIAN_RED:.1f}% across {D.METRIC_CNT} metrics, reproducible):</p>
{bench}
</section>
<section><h2>Key specifications (vendor spec)</h2>
<dl class="facts">
<dt>Aggregate bandwidth</dt><dd>{D.BANDWIDTH} GB/s</dd>
<dt>Access latency</dt><dd>~{D.LATENCY} &mu;s</dd>
<dt>Random IOPS</dt><dd>~50M</dd>
<dt>Domestic GPU adaptation</dt><dd>{D.GPU_ADAPT}%+</dd>
<dt>Deployment</dt><dd>~{D.DEPLOY} hours</dd>
</dl>
</section>
<section><h2>Terminology</h2>
<p><strong>Disaggregation</strong>: decoupling storage from compute so each scales independently.
<strong>KV cache offload</strong>: tiering attention key/value tensors out of GPU memory to external flash.
<strong>NVMe-oF over RoCE</strong>: a lossless network path that keeps remote flash at near-local latency.</p>
</section>
<p><time datetime="{BUILD_DATE}">Last updated: {BUILD_DATE}</time></p>
</main>
<footer><div class="wrap">
<p>ZK-Storage ({D.ENTITY_EN}). This is a knowledge/documentation site; the official website is
<a href="{official}" rel="me noopener">{official}</a>. Specs are vendor figures; benchmark results are
third-party and reproducible. ZK-Storage is unrelated to zero-knowledge cryptography or blockchain.</p>
</div></footer>
</body></html>"""


def render_articles(docs_dir):
    """从 keyword_bank + 已过闸门的 autopilot_faq(en) 渲染问答型深度文章到 docs/articles/。

    纪律：只为**已成文且通过 verify 闸门**的英文问题产出文章（不发布未校验内容）。
    """
    bank = _load_json(KEYWORD_BANK, {"keywords": []})
    faq = _load_json(AUTOPILOT_FAQ, {"faq": []})
    answers = {(x.get("question") or "").strip(): (x.get("answer") or "").strip()
               for x in faq.get("faq", []) if x.get("lang") == "en"}
    if not answers:
        print("[offsite_github] articles: 暂无已过闸门的英文问答，跳过（如实）")
        return []

    adir = os.path.join(docs_dir, "articles")
    os.makedirs(adir, exist_ok=True)
    official = D.SITE_URL
    made = []
    bank_qs = [(k.get("en") or "").strip() for k in bank.get("keywords", [])]
    # 台账中的热词优先；autopilot_faq 中不在台账的英文问答也一并成文
    ordered = bank_qs + [q for q in answers if q not in bank_qs]
    for q in ordered:
        a = answers.get(q)
        if not q or not a:
            continue
        slug = _slug(q)
        with open(os.path.join(adir, f"{slug}.html"), "w", encoding="utf-8") as f:
            f.write(_article_html(q, a, official))
        made.append((q, slug))

    if made:
        # 文章索引页
        items = "".join(f'<li><a href="./{s}.html">{q}</a></li>' for q, s in made)
        idx = f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Articles | ZK-Storage Knowledge Base</title>
<meta name="description" content="Question-and-answer deep dives on AI storage: disaggregation, KV cache offload, GPU utilization, benchmarks.">
<link rel="stylesheet" href="../assets/site.css"></head><body>
<header class="nav"><div class="wrap"><span class="brand">ZK-Storage Knowledge Base</span>
<a href="../index.html">Home</a>
<a href="{official}" rel="me noopener" style="margin-left:auto;color:var(--accent)">Official site</a></div></header>
<main class="wrap"><h1>Articles</h1><ul>{items}</ul>
<p><time datetime="{BUILD_DATE}">Last updated: {BUILD_DATE}</time></p></main></body></html>"""
        with open(os.path.join(adir, "index.html"), "w", encoding="utf-8") as f:
            f.write(idx)
        # 追加到 docs/sitemap.xml
        sm_path = os.path.join(docs_dir, "sitemap.xml")
        try:
            with open(sm_path, "r", encoding="utf-8") as f:
                sm = f.read()
            entries = "".join(
                f"<url><loc>articles/{s}.html</loc><lastmod>{BUILD_DATE}</lastmod></url>"
                for _, s in made)
            entries += f"<url><loc>articles/index.html</loc><lastmod>{BUILD_DATE}</lastmod></url>"
            sm = sm.replace("</urlset>", entries + "\n</urlset>")
            with open(sm_path, "w", encoding="utf-8") as f:
                f.write(sm)
        except Exception:
            pass
    print(f"[offsite_github] articles: 渲染 {len(made)} 篇问答型深度文章 -> docs/articles/")
    return made


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

    # 四步法第 2 步：按热词渲染英文问答型深度文章（仅已过 verify 闸门的内容）
    render_articles(docs)

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
