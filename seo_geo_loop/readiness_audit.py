# -*- coding: utf-8 -*-
"""中科存储 GEO+SEO 就绪度综合指数（CRI）· 确定性站内审计（可复现）。

真实扫描 ../official_website 的主站双语内容页（zh/ 与 en/，不含学院子站 training/
与 noindex 门户 portal/）与站点级文件，按 5 支柱计算 CRI(0–100)。给定站点输入，
结果**完全确定、可复现**（无随机数、无网络）。

5 支柱（权重公开、可调、和=1）：
  A 技术 SEO            0.25   每页 title/desc/H1/canonical/hreflang/og/twitter/JSON-LD/
                              lang/viewport/charset/图片 alt/内链 + 站级 sitemap/robots/indexnow/manifest
  B AI 抓取与可达       0.20   robots 放行 AI bot、声明 sitemap；llms.txt/llms-full.txt 覆盖；sitemap 覆盖
  C 结构化数据完备度    0.20   Organization(富化)/WebSite(SearchAction)/Product/FAQPage/
                              BreadcrumbList/TechArticle/Person/DefinedTermSet 应有尽有
  D 答案优先/可抽取性   0.20   问句式 H2 + 速答关键事实块 + 规格表 + FAQ + 术语 + 来源标注密度
  E 实体一致性&E-E-A-T  0.15   实体名/规格口径一致、联系方式、可见更新时间、作者归属

用法：
  python readiness_audit.py --label baseline        # 单次快照（写 outputs/snapshots/）
  python readiness_audit.py                          # 默认 label=current，仅打印
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(os.path.dirname(BASE), "official_website")
OUT = os.path.join(BASE, "outputs")
SNAP = os.path.join(OUT, "snapshots")

# 单一数据源常量（用于实体/规格一致性核对）
sys.path.insert(0, SITE)
import site_data as D  # noqa: E402

# --------------------------------------------------------------------------- #
# 权重（公开、可调；和必须=1）
# --------------------------------------------------------------------------- #
PILLAR_WEIGHTS = {"A": 0.25, "B": 0.20, "C": 0.20, "D": 0.20, "E": 0.15}
assert abs(sum(PILLAR_WEIGHTS.values()) - 1.0) < 1e-9

# 答案优先「关键页」集合（用于 D 支柱抽样）
KEY_PAGES = {
    "product.html", "technology.html", "validation.html", "solutions.html",
    "solutions-ai-dc.html", "kv-cache-offload.html", "ai-inference-storage.html",
    "faq.html", "glossary.html",
}
# g7 速答块应出现的 5 页（规格类核心页）
ANSWER_PAGES = {"product.html", "technology.html", "validation.html",
                "solutions.html", "solutions-ai-dc.html"}
# 规格表应出现的页
TABLE_PAGES = {"product.html", "technology.html", "validation.html",
               "solutions-ai-dc.html", "ai-inference-storage.html"}

AI_BOTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "anthropic-ai",
           "Claude-Web", "Claude-User", "PerplexityBot", "Perplexity-User",
           "Google-Extended", "Applebot-Extended", "Applebot", "Bytespider",
           "Amazonbot", "CCBot", "Meta-ExternalAgent", "cohere-ai", "DeepSeekBot"]

SOURCE_TOKENS = ["S9", "S38", "S4", "S5", "S42", "S43", "来源", "项目方口径", "实测", "source", "vendor spec"]

# --------------------------------------------------------------------------- #
# 正则
# --------------------------------------------------------------------------- #
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
DESC_RE = re.compile(r'<meta\s+name="description"\s+content="(.*?)"', re.S | re.I)
H1_RE = re.compile(r"<h1\b", re.I)
H2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.S | re.I)
CANON_RE = re.compile(r'<link\s+rel="canonical"\s+href="(https?://[^"]+)"', re.I)
HREFLANG_RE = re.compile(r'<link\s+rel="alternate"\s+hreflang="([^"]+)"', re.I)
OGURL_RE = re.compile(r'<meta\s+property="og:url"\s+content="(https?://[^"]+)"', re.I)
OGIMG_RE = re.compile(r'<meta\s+property="og:image"\s+content="(https?://[^"]+)"', re.I)
OGTITLE_RE = re.compile(r'<meta\s+property="og:title"', re.I)
OGDESC_RE = re.compile(r'<meta\s+property="og:description"', re.I)
TWCARD_RE = re.compile(r'<meta\s+name="twitter:card"', re.I)
TWTITLE_RE = re.compile(r'<meta\s+name="twitter:title"', re.I)
TWDESC_RE = re.compile(r'<meta\s+name="twitter:description"', re.I)
THEME_RE = re.compile(r'<meta\s+name="theme-color"', re.I)
AUTHOR_RE = re.compile(r'<meta\s+name="author"', re.I)
LANG_RE = re.compile(r'<html\s+lang="([^"]+)"', re.I)
VIEWPORT_RE = re.compile(r'<meta\s+name="viewport"', re.I)
CHARSET_RE = re.compile(r'<meta\s+charset=', re.I)
JSONLD_RE = re.compile(r'<script\s+type="application/ld\+json">(.*?)</script>', re.S | re.I)
IMG_RE = re.compile(r"<img\b[^>]*>", re.I)
ALT_RE = re.compile(r'\balt="([^"]*)"', re.I)
TIME_RE = re.compile(r"<time\s+datetime=", re.I)
HREF_RE = re.compile(r'<a\b[^>]*\bhref="([^"]+)"', re.I)
TABLE_RE = re.compile(r"<table\b", re.I)
KEYFACTS_RE = re.compile(r'class="[^"]*\bkey-facts\b', re.I)

Q_MARKS = ["？", "?", "什么", "如何", "为何", "为什么", "怎样", "怎么",
           "what", "how", "why", "which", "where", "does", "can "]


def _content_pages():
    out = []
    for lang in ("zh", "en"):
        d = os.path.join(SITE, lang)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".html"):
                out.append((lang, fn, os.path.join(d, fn)))
    return out


def _parse_jsonld(html):
    """返回 (types:set, objs:list[dict])。容错解析所有 JSON-LD 脚本。"""
    types, objs = set(), []
    for raw in JSONLD_RE.findall(html):
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        items = obj if isinstance(obj, list) else [obj]
        for it in items:
            if isinstance(it, dict):
                objs.append(it)
                t = it.get("@type")
                if isinstance(t, str):
                    types.add(t)
                elif isinstance(t, list):
                    types.update(x for x in t if isinstance(x, str))
    return types, objs


def _find_obj(objs, t):
    return next((o for o in objs if o.get("@type") == t), None)


def audit_page(lang, fname, html):
    title_m = TITLE_RE.search(html)
    title = title_m.group(1).strip() if title_m else ""
    desc_m = DESC_RE.search(html)
    desc = desc_m.group(1).strip() if desc_m else ""
    h1 = len(H1_RE.findall(html))
    hreflangs = set(HREFLANG_RE.findall(html))
    types, objs = _parse_jsonld(html)
    imgs = IMG_RE.findall(html)
    imgs_with_alt = sum(1 for im in imgs if (ALT_RE.search(im) and ALT_RE.search(im).group(1).strip()))
    internal_links = [h for h in HREF_RE.findall(html)
                      if not h.startswith(("http://", "https://", "mailto:", "tel:", "#", "data:"))]
    h2s = [re.sub(r"<[^>]+>", "", h).strip().lower() for h in H2_RE.findall(html)]
    has_q_h2 = any(any(m in h for m in Q_MARKS) for h in h2s)

    title_len = len(title)
    title_lim = 40 if lang == "zh" else 65
    org = _find_obj(objs, "Organization")
    website = _find_obj(objs, "WebSite")

    # ---- CRI v2 新增子项（确定性、可复现）----
    imgs_decoding = (all("decoding=" in im.lower() for im in imgs)) if imgs else True
    # 规格单位排版口径：数字与单位之间必须恰有空格（"300GB/s"/"20μs" 视为漂移）
    spec_canonical = not (re.search(r"\dGB/s", html) or re.search(r"\d(?:\u03bc|\u00b5)s", html))
    org_sameas = bool(org and org.get("sameAs"))
    preload_css = ('rel="preload"' in html and 'as="style"' in html)
    speakable = "SpeakableSpecification" in html
    webpage_type = "WebPage" in types

    return {
        "lang": lang, "fname": fname,
        # A：技术 SEO
        "title_ok": bool(title) and title_len <= title_lim,
        "title_len": title_len,
        "desc_ok": bool(desc) and 70 <= len(desc) <= 160,
        "desc_len": len(desc),
        "h1_one": h1 == 1,
        "canonical": bool(CANON_RE.search(html)),
        "hreflang3": len(hreflangs) >= 3,
        "og_abs": bool(OGURL_RE.search(html)) and bool(OGIMG_RE.search(html)),
        "social_full": all(r.search(html) for r in
                           (OGTITLE_RE, OGDESC_RE, TWCARD_RE, TWTITLE_RE, TWDESC_RE)),
        "jsonld": len(objs) >= 1,
        "lang_attr": bool(LANG_RE.search(html)),
        "viewport_charset": bool(VIEWPORT_RE.search(html)) and bool(CHARSET_RE.search(html)),
        "alt_cov": (imgs_with_alt == len(imgs)) if imgs else True,
        "img_total": len(imgs), "img_alt": imgs_with_alt,
        "theme_color": bool(THEME_RE.search(html)),
        "internal_links_ok": len(internal_links) >= 3,
        "internal_links": len(internal_links),
        # C：结构化数据
        "has_org": org is not None,
        "org_enriched": bool(org and org.get("knowsAbout") and org.get("contactPoint")),
        "has_website": website is not None,
        "website_search": bool(website and website.get("potentialAction")),
        "has_product": "Product" in types,
        "has_faqpage": "FAQPage" in types,
        "has_breadcrumb": "BreadcrumbList" in types,
        "has_techarticle": "TechArticle" in types,
        "has_person": "Person" in types,
        "has_definedterms": "DefinedTermSet" in types,
        "faq_q_count": sum(len(o.get("mainEntity", [])) for o in objs if o.get("@type") == "FAQPage"),
        "term_count": sum(len(o.get("hasDefinedTerm", [])) for o in objs if o.get("@type") == "DefinedTermSet"),
        # D：答案优先
        "has_q_h2": has_q_h2,
        "has_keyfacts": bool(KEYFACTS_RE.search(html)),
        "has_table": bool(TABLE_RE.search(html)),
        "has_source": any(tok in html for tok in SOURCE_TOKENS),
        # E：E-E-A-T
        "has_time": bool(TIME_RE.search(html)),
        "has_author": bool(AUTHOR_RE.search(html)),
        "entity_ok": (D.ENTITY_ZH in html) if lang == "zh" else (D.ENTITY_EN in html or "ZK-Storage" in html),
        "tel_ok": D.CONTACT_TEL in html,
        # 规格一致性：若提及带宽/时延，必须用单一数据源口径
        "spec_ok": (("GB/s" not in html or f"{D.BANDWIDTH} GB/s" in html)
                    and ("μs" not in html or f"{D.LATENCY} μs" in html or f"{D.LATENCY} \u00b5s" in html)),
        # ---- CRI v2 子项 ----
        "img_decoding": imgs_decoding,
        "spec_canonical": spec_canonical,
        "org_sameas": org_sameas,
        "preload_css": preload_css,
        "speakable": speakable,
        "webpage_type": webpage_type,
        "_raw_html_len": len(html),
        "_html": html,  # 仅供站级检查临时使用，落盘前剔除
    }


def _site_level():
    def p(rel):
        return os.path.join(SITE, rel)

    out = {"sitemap": os.path.exists(p("sitemap.xml")),
           "robots": os.path.exists(p("robots.txt")),
           "manifest": os.path.exists(p("manifest.webmanifest")) or os.path.exists(p("site.webmanifest")),
           "llms": os.path.exists(p("llms.txt")),
           "llms_full": os.path.exists(p("llms-full.txt")),
           "robots_sitemap": False, "ai_bots": 0,
           "llms_page_urls": 0, "llms_full_page_urls": 0,
           "sitemap_urls": 0}

    # IndexNow key 文件
    out["indexnow"] = any(re.fullmatch(r"[0-9a-f]{8,}\.txt", fn, re.I)
                          for fn in (os.listdir(SITE) if os.path.isdir(SITE) else []))

    # CRI v2：字体显示策略（site.css 含 font-display 或 Google Fonts &display=swap）
    css = os.path.join(SITE, "assets", "css", "site.css")
    out["font_display"] = False
    if os.path.exists(css):
        t = open(css, "r", encoding="utf-8").read()
        out["font_display"] = ("font-display" in t) or ("display=swap" in t)

    if out["robots"]:
        txt = open(p("robots.txt"), "r", encoding="utf-8").read()
        out["robots_sitemap"] = "sitemap" in txt.lower()
        out["ai_bots"] = sum(1 for ua in AI_BOTS if re.search(rf"User-agent:\s*{re.escape(ua)}\b", txt, re.I))

    if out["sitemap"]:
        out["sitemap_urls"] = len(re.findall(r"<loc>(.*?)</loc>",
                                  open(p("sitemap.xml"), "r", encoding="utf-8").read()))
    if out["llms"]:
        t = open(p("llms.txt"), "r", encoding="utf-8").read()
        out["llms_page_urls"] = len(set(re.findall(r"https?://[^\s)]+\.html", t)))
    if out["llms_full"]:
        t = open(p("llms-full.txt"), "r", encoding="utf-8").read()
        out["llms_full_page_urls"] = len(set(re.findall(r"https?://[^\s)]+\.html", t)))
    return out


def _frac(rows, key):
    return round(sum(1 for r in rows if r.get(key)) / len(rows), 4) if rows else 0.0


def _imgs_frac(rows, key):
    """只在含图片的页面上统计（避免无图页拉高/拉低分母）。"""
    sub = [r for r in rows if r.get("img_total", 0) > 0]
    return round(sum(1 for r in sub if r.get(key)) / len(sub), 4) if sub else 1.0


def run(label="current", v2=False):
    pages = _content_pages()
    rows = [audit_page(lang, fn, open(fp, "r", encoding="utf-8").read())
            for lang, fn, fp in pages]
    n = len(rows)
    site = _site_level()
    n_content = n  # zh+en 主站内容页数

    # ---- Pillar A：技术 SEO ----
    A_PAGE_KEYS = ["title_ok", "desc_ok", "h1_one", "canonical", "hreflang3", "og_abs",
                   "social_full", "jsonld", "lang_attr", "viewport_charset", "alt_cov",
                   "theme_color", "internal_links_ok"]
    a_page_items = [_frac(rows, k) for k in A_PAGE_KEYS]
    a_site_keys = ["sitemap", "robots", "robots_sitemap", "indexnow", "manifest"]
    # v2：A 增 media_dims(decoding) + preload_css 两个页级子项，font_display 并入站级。
    if v2:
        a_v2_media = _imgs_frac(rows, "img_decoding")
        a_v2_preload = _frac(rows, "preload_css")
        a_page_items += [a_v2_media, a_v2_preload]
        a_site_keys = a_site_keys + ["font_display"]
    a_page = sum(a_page_items) / len(a_page_items)
    a_site = sum(1 for k in a_site_keys if site.get(k)) / len(a_site_keys)
    A = 0.85 * a_page + 0.15 * a_site

    # ---- Pillar B：AI 抓取与可达 ----
    b1 = min(site["ai_bots"] / 15.0, 1.0)
    b2 = 1.0 if site["robots_sitemap"] else 0.0
    b3 = 1.0 if (site["llms"] and site["llms_page_urls"] >= 6) else 0.0
    b4 = 1.0 if site["llms_full"] else 0.0
    b5 = min(site["llms_full_page_urls"] / max(1, n_content), 1.0)  # llms-full 覆盖率
    # sitemap 覆盖（应含全部 zh/en 内容页；sitemap 也含 training，故按 ≥ 内容页数判定）
    b6 = 1.0 if site["sitemap_urls"] >= n_content else round(site["sitemap_urls"] / max(1, n_content), 4)
    B = (b1 + b2 + b3 + b4 + b5 + b6) / 6.0

    # ---- Pillar C：结构化数据完备度 ----
    by = {(r["lang"], r["fname"]): r for r in rows}
    def has_on(fname, key):
        vals = [r for r in rows if r["fname"] == fname]
        return all(r.get(key) for r in vals) if vals else False

    c1 = _frac(rows, "has_org")
    c2 = _frac(rows, "org_enriched")
    c3 = _frac(rows, "has_website")
    c4 = _frac(rows, "website_search")
    c5 = (1.0 if has_on("product.html", "has_product") else 0.0) * 0.5 + \
         (1.0 if has_on("solutions-ai-dc.html", "has_product") else 0.0) * 0.5
    c6 = 1.0 if has_on("faq.html", "has_faqpage") else 0.0
    c7 = _frac(rows, "has_breadcrumb")
    c8 = 1.0 if (has_on("kv-cache-offload.html", "has_techarticle")
                 and has_on("ai-inference-storage.html", "has_techarticle")) else 0.0
    c9 = 1.0 if has_on("about.html", "has_person") else 0.0
    c10 = 1.0 if has_on("glossary.html", "has_definedterms") else 0.0
    c_items = [c1, c2, c3, c4, c5, c6, c7, c8, c9, c10]
    # v2：C 增 org.sameAs 覆盖 + 首页 WebPage/Speakable。
    if v2:
        c11 = _frac(rows, "org_sameas")
        c12 = 1.0 if (has_on("index.html", "webpage_type") and has_on("index.html", "speakable")) else 0.0
        c_items += [c11, c12]
    C = sum(c_items) / len(c_items)

    # ---- Pillar D：答案优先 / 可抽取性 ----
    key_rows = [r for r in rows if r["fname"] in KEY_PAGES]
    ans_rows = [r for r in rows if r["fname"] in ANSWER_PAGES]
    tbl_rows = [r for r in rows if r["fname"] in TABLE_PAGES]
    d1 = _frac(key_rows, "has_q_h2")
    d2 = _frac(ans_rows, "has_keyfacts")
    d3 = _frac(tbl_rows, "has_table")
    faq_q = max((r["faq_q_count"] for r in rows if r["fname"] == "faq.html"), default=0)
    d4 = 1.0 if faq_q >= 6 else round(faq_q / 6.0, 4)
    term_c = max((r["term_count"] for r in rows if r["fname"] == "glossary.html"), default=0)
    d5 = 1.0 if term_c >= 8 else round(term_c / 8.0, 4)
    d6 = _frac(rows, "has_source")
    d_items = [d1, d2, d3, d4, d5, d6]
    # v2：D 增「答案块全覆盖」——全部主内容页含问句式 H2 或速答关键事实块。
    if v2:
        d7 = round(sum(1 for r in rows if r.get("has_q_h2") or r.get("has_keyfacts")) / len(rows), 4)
        d_items += [d7]
    D_ = sum(d_items) / len(d_items)

    # ---- Pillar E：实体一致性 & E-E-A-T ----
    e1 = _frac(rows, "entity_ok")
    e2 = _frac(rows, "spec_ok")
    e3 = _frac(rows, "tel_ok")
    e4 = _frac(rows, "has_time")
    e5 = _frac(rows, "has_author")
    e6 = 1.0 if all(r.get("org_enriched") for r in rows) else _frac(rows, "org_enriched")
    e_items = [e1, e2, e3, e4, e5, e6]
    # v2：E 增 规格排版一致性(spec_canonical) + 真实站外实体锚点(sameAs)。
    if v2:
        e7 = _frac(rows, "spec_canonical")
        e8 = _frac(rows, "org_sameas")
        e_items += [e7, e8]
    E = sum(e_items) / len(e_items)

    pillars = {"A": round(A, 4), "B": round(B, 4), "C": round(C, 4),
               "D": round(D_, 4), "E": round(E, 4)}
    cri = round(100.0 * sum(PILLAR_WEIGHTS[k] * pillars[k] for k in pillars), 2)

    detail = {
        "A": {"page_avg": round(a_page, 4), "site_avg": round(a_site, 4),
              "page_coverage": {k: _frac(rows, k) for k in A_PAGE_KEYS},
              "site": {k: site.get(k) for k in a_site_keys}},
        "B": {"ai_bots": site["ai_bots"], "b1": round(b1, 4), "b2": b2, "b3": b3,
              "b4": b4, "llms_full_coverage": round(b5, 4),
              "llms_full_page_urls": site["llms_full_page_urls"],
              "sitemap_urls": site["sitemap_urls"], "b6": b6},
        "C": {"org": c1, "org_enriched": c2, "website": c3, "search_action": c4,
              "product": c5, "faqpage": c6, "breadcrumb": c7, "techarticle": c8,
              "person": c9, "definedterms": c10},
        "D": {"q_h2": d1, "key_facts": d2, "tables": d3, "faq_q": faq_q,
              "glossary_terms": term_c, "source_density": d6},
        "E": {"entity": e1, "spec_consistency": e2, "contact": e3,
              "last_updated": e4, "author": e5, "entity_anchor": e6},
    }
    if v2:
        detail["A"]["media_decoding"] = a_v2_media
        detail["A"]["preload_css"] = a_v2_preload
        detail["A"]["font_display"] = 1.0 if site.get("font_display") else 0.0
        detail["C"]["org_sameas"] = c11
        detail["C"]["home_speakable"] = c12
        detail["D"]["answer_all"] = d7
        detail["E"]["spec_canonical"] = e7
        detail["E"]["entity_sameas"] = e8

    # 去除临时 _html，控制快照体积
    clean_rows = []
    for r in rows:
        rr = {k: v for k, v in r.items() if not k.startswith("_")}
        clean_rows.append(rr)

    return {
        "label": label,
        "cri_version": "v2" if v2 else "v1",
        "computed_at": dt.datetime.now().isoformat(timespec="seconds"),
        "scope": "official_website 主站双语内容页（zh/ + en/，不含 training 子站与 portal）",
        "n_pages": n,
        "weights": PILLAR_WEIGHTS,
        "pillars": pillars,
        "cri": cri,
        "detail": detail,
        "lowest_pillar": min(pillars, key=pillars.get),
        "per_page": clean_rows,
    }


def lowest_levers(snapshot, k=3):
    """返回得分最低的支柱明细子项（用于复盘『还差在哪』）。"""
    items = []
    for pillar, d in snapshot["detail"].items():
        for key, val in d.items():
            if isinstance(val, (int, float)) and not isinstance(val, bool) and val < 1.0 \
                    and key not in ("ai_bots", "faq_q", "glossary_terms", "sitemap_urls",
                                    "llms_full_page_urls", "page_avg", "site_avg", "b1", "b2",
                                    "b3", "b4", "b6"):
                items.append((round(val, 4), f"{pillar}.{key}"))
    items.sort()
    return items[:k]


def main():
    label = "current"
    if "--label" in sys.argv:
        label = sys.argv[sys.argv.index("--label") + 1]
    v2 = "--v2" in sys.argv
    snap = run(label, v2=v2)
    os.makedirs(SNAP, exist_ok=True)
    if label != "current":
        with open(os.path.join(SNAP, f"{label}.json"), "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)
    print(f"[CRI:{label}/{snap['cri_version']}] {snap['cri']}  pillars="
          + " ".join(f"{k}={v}" for k, v in snap["pillars"].items())
          + f"  pages={snap['n_pages']}")
    print("  最低子项：", "; ".join(f"{name}={v}" for v, name in lowest_levers(snap, 5)))


if __name__ == "__main__":
    main()
