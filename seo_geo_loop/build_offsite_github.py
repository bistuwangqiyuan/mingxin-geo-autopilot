# -*- coding: utf-8 -*-
"""铭信 · 组装 GitHub Pages 知识库仓库内容（offsite_github/ = mingxin-storage-kb）。

从 offsite_site/（知识微站）组装一个可发布到 GitHub Pages 的仓库目录：
README.md（仓库首页）+ docs/（Pages 站点，/docs 发布）+ .nojekyll。
真实发布由 run.py / 手动 gh 命令完成（账号已 gh 登录）；线上地址
https://bistuwangqiyuan.github.io/mingxin-storage-kb/。

事实单一来源：site_facts（business_plan/outputs/results.json 镜像，与官网 company.ts 同源）。
"""
from __future__ import annotations

import datetime as dt
import os
import shutil

import site_facts as D

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
SITE = os.path.join(ROOT, "offsite_site")
OUT = os.path.join(ROOT, "offsite_github")

BUILD_DATE = dt.date.today().isoformat()
LEGACY = "/".join(D.LEGACY_NAMES)  # AISSD5000/WS5000/GP5000

KEYWORD_BANK = os.path.join(ROOT, "geo_autopilot", "history", "keyword_bank.json")
# 内容引擎问答闸门产物。2026-08-08 起存在本仓库内，理由同 make_geo_kit_en.py。
AUTOPILOT_FAQ = os.path.join(ROOT, "geo_autopilot", "outputs", "autopilot_faq.json")


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
    """英文问答型深度文章页（answer-first + 签字级数据 + 术语 + 回链官网）。
    事实全部来自单一事实源 site_facts；答案 a 已过一致性/verify 闸门。"""
    import json
    bench = ("<table><tr><th>Metric</th><th>Value</th><th>Source</th></tr>"
             + "".join(f"<tr><td>{m['label']}</td><td><b>{m['value']}</b></td>"
                       f"<td>{m['source']}</td></tr>" for m in D.KEY_METRICS)
             + "</table>")
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
    plat = D.PLATFORM
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{q} | Mingxin Storage Knowledge Base</title>
<meta name="description" content="{a[:155]}">
<meta name="robots" content="index,follow,max-snippet:-1">
<link rel="canonical" href="./{_slug(q)}.html">
<meta property="og:type" content="article"><meta property="og:title" content="{q}">
<link rel="stylesheet" href="../assets/site.css">
{blocks}
</head><body>
<header class="nav"><div class="wrap">
<span class="brand">Mingxin Storage Knowledge Base</span>
<a href="./index.html">Articles</a>
<a href="../index.html">Home</a>
<a href="{official}" rel="me noopener" style="margin-left:auto;color:var(--accent)">Official site mingxinstorage.xyz</a>
</div></header>
<main class="wrap">
<h1>{q}</h1>
<p class="lead" style="color:var(--sub);font-size:19px">{a}</p>
<section><h2>The data (signed-off test reports R1–R9)</h2>
<p>Measured on {plat["gpu"]}, {plat["gpu_stack"]}, {plat["engine"]} + LMCache with
{plat["model_480b"]} (R1–R4 shared platform); the model-load numbers are from the Huawei
Atlas 910B (Ascend) platform (R9), stated as such. Reproducible via the R8 export pack.</p>
{bench}
</section>
<section><h2>Key specifications — {D.MODEL} (vendor spec)</h2>
<dl class="facts">
<dt>Product</dt><dd>{D.MODEL} (formerly {LEGACY} — same product, unified FX naming)</dd>
<dt>PCIe</dt><dd>PCIe 3.0</dd>
<dt>Network port</dt><dd>{D.FX100_PORT_GB} GbE</dd>
<dt>Random IOPS</dt><dd>{D.FX100_IOPS_M}M</dd>
<dt>Fully-populated reference price</dt><dd>&yen;{D.FX100_FULL_CNY:,} (&asymp;&yen;{D.FX100_CNY_PER_TB:,}/TB)</dd>
</dl>
</section>
<section><h2>Terminology</h2>
<p><strong>KV-cache tiering</strong>: scheduling attention key/value tensors between GPU HBM and
external flash by access heat, so cold long-context sessions avoid full prefill recomputation.
<strong>NVMe-oF over RoCE</strong>: a lossless network path that keeps remote flash at near-local latency.
<strong>TTFT</strong>: time to first token, the core latency metric for cold-session recovery.</p>
</section>
<p><time datetime="{BUILD_DATE}">Last updated: {BUILD_DATE}</time></p>
</main>
<footer><div class="wrap">
<p>{D.BRAND_EN} ({D.ENTITY_EN}). This is a knowledge/documentation site; the official website is
<a href="{official}" rel="me noopener">{official}</a>. Specs are vendor figures; performance results
come from signed-off test reports (evidence library: <a href="{official}/evidence">{official}/evidence</a>).
"Mingxin" here refers specifically to {D.ENTITY_EN} and is unrelated to other companies of the same name.</p>
</div></footer>
</body></html>"""


def render_articles(docs_dir):
    """从 keyword_bank + 已过闸门的 autopilot_faq(en) 渲染问答型深度文章到 docs/articles/。

    纪律：只为**已成文且通过 verify 闸门**的英文问题产出文章（不发布未校验内容）。
    autopilot_faq.json 不存在时（站点内容引擎尚未落盘）优雅跳过。
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
<title>Articles | Mingxin Storage Knowledge Base</title>
<meta name="description" content="Question-and-answer deep dives on AI storage acceleration: KV-cache tiering, domestic-GPU enablement, signed-off benchmarks (R1–R9).">
<link rel="stylesheet" href="../assets/site.css"></head><body>
<header class="nav"><div class="wrap"><span class="brand">Mingxin Storage Knowledge Base</span>
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
    # 保留 OUT/.git（本目录即 mingxin-storage-kb 发布仓库的工作树）；只刷新 docs/ 与 README。
    os.makedirs(OUT, exist_ok=True)
    docs = os.path.join(OUT, "docs")
    if os.path.exists(docs):
        shutil.rmtree(docs)
    shutil.copytree(SITE, docs)
    # GitHub Pages 关闭 Jekyll，避免对下划线/资源目录的处理
    open(os.path.join(docs, ".nojekyll"), "w").close()

    # 保留仓库根部既有 blog/（站点引擎早期发布、已被收录的 URL），并入 docs/ 一同发布
    root_blog = os.path.join(OUT, "blog")
    if os.path.isdir(root_blog):
        shutil.copytree(root_blog, os.path.join(docs, "blog"), dirs_exist_ok=True)

    # 四步法第 2 步：按热词渲染英文问答型深度文章（仅已过 verify 闸门的内容）
    render_articles(docs)

    readme = f"""# Mingxin Storage Knowledge Base（铭信存储知识库）

Knowledge/documentation repository for **{D.BRAND_ZH}（{D.BRAND_EN}）** — {D.POSITIONING_EN}.

- Official website: **{D.SITE_URL}** （官方网站，请以此为准）
- Operating entity: {D.ENTITY_ZH} / {D.ENTITY_EN}
- Evidence library (signed-off test reports R1–R9): {D.SITE_URL}/evidence

## Key facts (single source of truth, signed-off reports R1–R9)

- KV-cache tiering on a 480B production deployment: throughput **{D.THROUGHPUT_UPLIFT}**,
  TTFT **down {D.TTFT_REDUCTION}** (R2/R3); **{D.RECOMPUTE_SPEEDUP}** vs no-external-store
  recomputation (R2).
- LMCache parallel-read patch: cold TTFT **{D.PARALLEL_READ_X}x** better (R1);
  training checkpoint save **{D.CKPT_SAVE_X}x** (R1).
- Model load **{D.MODEL_LOAD_SPEEDUP}** vs NFS — measured on the Huawei Atlas 910B (Ascend)
  platform (R9), stated as such.
- Flagship **{D.MODEL}** (formerly {LEGACY} — same product, unified FX naming; series:
  {', '.join(D.SERIES)}): PCIe 3.0, {D.FX100_PORT_GB} GbE, {D.FX100_IOPS_M}M IOPS,
  fully-populated reference price ¥{D.FX100_FULL_CNY:,} (≈¥{D.FX100_CNY_PER_TB:,}/TB, vendor figures).

## Knowledge base (GitHub Pages)

This repository publishes a knowledge microsite (served from `/docs`): KV-cache tiering,
domestic-GPU enablement, the {D.MODEL} fact card, the R1–R9 evidence index and FAQ —
all consistent with the official site **{D.SITE_URL}**.

## Disambiguation（消歧）

"Mingxin（铭信）" here refers specifically to **{D.ENTITY_ZH}** and is a distinct entity from
other companies of the same name. Naming note: {D.NAMING_NOTE}

_Last updated: {BUILD_DATE}_
"""
    with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme)

    pages = sorted(os.listdir(docs))
    print(f"[offsite_github] 组装完成 -> {OUT}  (docs 文件 {len(pages)} 个)")
    return OUT


if __name__ == "__main__":
    build()
