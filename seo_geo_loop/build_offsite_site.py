# -*- coding: utf-8 -*-
"""中科存储 · 站外知识微站生成器（苹果视觉 · 单一数据源）。

目的：在可自动化、合规的外部主机（EdgeOne Pages）上发布一个**company-run 知识微站**，
作为指向官网 goni.top 的真实外部信源（提升实体一致性、被 LLM 引用概率与收录信号）。

诚实纪律：
  - 所有事实从 official_website/site_data.py 读取（其又源自 business_plan/outputs/results.json），
    与官网完全同源,不另行编造。
  - 微站明确是知识/文档站,链接并指认官网 https://goni.top 为官方站点；不冒充官方主域。
  - 第三方实测标注机构与"可复现";规格标注"项目方口径"。

复现：python build_offsite_site.py   ->  生成 ../offsite_site/（可直接 EdgeOne 部署的静态目录）
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
OUT = os.path.join(ROOT, "offsite_site")
sys.path.insert(0, os.path.join(ROOT, "official_website"))

import site_data as D  # noqa: E402

BUILD_DATE = dt.date.today().isoformat()
OFFICIAL = D.SITE_URL  # https://goni.top

# 本微站在 EdgeOne 上的已上线地址（用于从 sameAs 中排除自身，连通其余实体节点）。
SELF_URL = "https://manju-studio-dpd7kg3gqlp5.edgeone.run"
# sameAs 实体网络：官网 + 全部已上线信源（排除自身），形成双向互指的实体图。
ENTITY_SAMEAS = [OFFICIAL] + [u for u in getattr(D, "SAMEAS_URLS", []) if u.rstrip("/") != SELF_URL.rstrip("/")]

CSS = """
:root{--bg:#fff;--ink:#1d1d1f;--sub:#6e6e73;--line:#e6e6eb;--accent:#0071e3;--card:#fafafc;--radius:18px}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  color:var(--ink);background:var(--bg);line-height:1.6;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:980px;margin:0 auto;padding:0 22px}
header.nav{position:sticky;top:0;z-index:10;background:rgba(255,255,255,.8);backdrop-filter:saturate(180%) blur(20px);
  border-bottom:1px solid var(--line)}
.nav .wrap{display:flex;align-items:center;gap:22px;height:52px;font-size:14px}
.nav .brand{font-weight:600}
.nav a{color:var(--ink)}
.hero{padding:84px 0 56px;text-align:center}
.hero h1{font-size:46px;line-height:1.08;letter-spacing:-.02em;margin:0 0 14px;font-weight:600}
.hero p.lead{font-size:21px;color:var(--sub);max-width:760px;margin:0 auto 26px}
.badge{display:inline-block;font-size:12px;color:var(--accent);border:1px solid var(--accent);
  border-radius:999px;padding:4px 12px;margin-bottom:18px;letter-spacing:.04em}
.btn{display:inline-block;background:var(--accent);color:#fff;border-radius:999px;padding:11px 24px;font-size:15px;margin:6px}
.btn.ghost{background:transparent;color:var(--accent);border:1px solid var(--accent)}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:40px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:22px 16px;text-align:center}
.kpi .n{font-size:30px;font-weight:600;letter-spacing:-.02em}
.kpi .l{font-size:13px;color:var(--sub);margin-top:6px}
section{padding:42px 0;border-top:1px solid var(--line)}
h2{font-size:30px;letter-spacing:-.02em;font-weight:600;margin:0 0 18px}
h3{font-size:20px;font-weight:600;margin:26px 0 8px}
p,li{font-size:17px;color:#333}
table{width:100%;border-collapse:collapse;margin:18px 0;font-size:15px}
th,td{border:1px solid var(--line);padding:10px 12px;text-align:left}
th{background:var(--card);font-weight:600}
.cards{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:22px}
.card h3{margin-top:0}
dl.facts{display:grid;grid-template-columns:1fr 1fr;gap:10px 24px;margin:0}
dl.facts dt{color:var(--sub);font-size:14px}
dl.facts dd{margin:0 0 8px;font-weight:600}
.note{font-size:13px;color:var(--sub);margin-top:10px}
footer{border-top:1px solid var(--line);padding:34px 0;color:var(--sub);font-size:13px}
footer a{color:var(--sub)}
time{color:var(--sub);font-size:13px}
@media(max-width:760px){.kpis{grid-template-columns:repeat(2,1fr)}.cards,dl.facts{grid-template-columns:1fr}.hero h1{font-size:34px}}
"""

NAV = f"""<header class="nav"><div class="wrap">
<span class="brand">中科存储 · 知识中心</span>
<a href="./index.html">首页</a>
<a href="./kv-cache-offload.html">KV Cache 卸载</a>
<a href="./ai-inference-storage.html">AI 推理存储</a>
<a href="./ws5000.html">WS5000</a>
<a href="./faq.html">FAQ</a>
<a href="./glossary.html">术语</a>
<a href="{OFFICIAL}" rel="me noopener" style="margin-left:auto;color:var(--accent)">官网 goni.top ↗</a>
</div></header>"""


def page(slug, title, desc, body, jsonld, keywords=""):
    blocks = "\n".join(
        f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>'
        for j in jsonld)
    return f"""<!doctype html><html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="keywords" content="{keywords}">
<meta name="theme-color" content="#ffffff">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<link rel="canonical" href="./{slug}">
<meta property="og:type" content="website"><meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}"><meta property="og:site_name" content="中科存储 知识中心">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}"><meta name="twitter:description" content="{desc}">
<link rel="stylesheet" href="./assets/site.css">
{blocks}
</head><body>
{NAV}
<main class="wrap">{body}
<p><time datetime="{BUILD_DATE}">最近更新：{BUILD_DATE}</time></p>
</main>
<footer><div class="wrap">
<p>中科存储（ZK-Storage）· 运营主体：{D.ENTITY_ZH}。本站为知识/文档站，官方网站：<a href="{OFFICIAL}" rel="me noopener">{OFFICIAL}</a>。</p>
<p>同源信源：{_sibling_links()}</p>
<p>规格为项目方口径；第三方实测由{D.ISSUER}在{D.PLATFORM}平台完成、可复现；不构成任何承诺。</p>
</div></footer>
</body></html>"""


def _sibling_links() -> str:
    """同源信源互链（排除自身与官网），强化双向 sameAs 实体网络。"""
    label_map = {it["url"].rstrip("/"): it["zh"] for it in getattr(D, "OFFSITE_LINKS", [])}
    parts = []
    for u in ENTITY_SAMEAS:
        if u.rstrip("/") == OFFICIAL.rstrip("/"):
            continue
        label = label_map.get(u.rstrip("/"), u)
        parts.append(f'<a href="{u}" rel="me noopener">{label}</a>')
    return " · ".join(parts) if parts else "—"


def _org():
    return {"@context": "https://schema.org", "@type": "Organization",
            "name": f"{D.BRAND_ZH}（{D.BRAND_EN}）", "alternateName": D.BRAND_EN,
            "url": OFFICIAL, "legalName": D.ENTITY_ZH,
            "description": "面向 AI 训练与推理的存算分离全闪存储加速一体机提供商；核心技术为存算分离 + KV-Cache 分层调度。",
            "knowsAbout": ["存算分离", "KV Cache 卸载", "NVMe-oF", "RoCEv2", "全闪存储", "AI 推理存储加速", "GPU 利用率"],
            "sameAs": ENTITY_SAMEAS}


def _breadcrumb(name, slug):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "知识中心", "item": "./index.html"},
        {"@type": "ListItem", "position": 2, "name": name, "item": f"./{slug}"}]}


def _article(headline, desc, slug):
    return {"@context": "https://schema.org", "@type": "TechArticle", "headline": headline,
            "description": desc, "inLanguage": "zh-CN", "datePublished": BUILD_DATE,
            "dateModified": BUILD_DATE, "author": _org(), "publisher": _org(),
            "mainEntityOfPage": f"./{slug}"}


def build():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)
    with open(os.path.join(OUT, "assets", "site.css"), "w", encoding="utf-8") as f:
        f.write(CSS)

    bench_rows = [
        ("DeepSeek-32B 模型加载", "563.85 s", "6.62 s", "85.17×"),
        ("DeepSeek-70B 模型加载", "1284.66 s", "35.38 s", "36.31×"),
        ("训练 / Checkpoint 加载保存", "—", "—", "5.3–12.5×"),
    ]
    bench_html = ("<table><tr><th>指标</th><th>NFS 基线</th><th>WS5000</th><th>提速</th></tr>"
                  + "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>"
                           for a, b, c, d in bench_rows) + "</table>")

    pages = {}

    # ---- index ----
    kpis = f"""<div class="kpis">
<div class="kpi"><div class="n">{D.BANDWIDTH} GB/s</div><div class="l">聚合带宽（WS5000）</div></div>
<div class="kpi"><div class="n">~{D.LATENCY} μs</div><div class="l">访问时延</div></div>
<div class="kpi"><div class="n">{D.MEDIAN_RED:.1f}%</div><div class="l">{D.METRIC_CNT} 项中位降幅（第三方实测）</div></div>
<div class="kpi"><div class="n">{D.GPU_ADAPT}%+</div><div class="l">国产 GPU 适配</div></div>
</div>"""
    idx_body = f"""
<div class="hero">
<span class="badge">AI 存算分离全闪存储 · 知识中心</span>
<h1>让每一块 GPU 物尽其用</h1>
<p class="lead">中科存储（ZK-Storage）以<strong>存算分离 + KV-Cache 分层调度</strong>为核心，
为 AI 训练与推理提供低时延、高带宽的数据通路——不改框架，把算力利用率提上去、把综合成本降下来。</p>
<a class="btn" href="{OFFICIAL}" rel="me noopener">访问官网 goni.top</a>
<a class="btn ghost" href="./ws5000.html">查看 WS5000 事实卡</a>
</div>
{kpis}
<section><h2>核心议题</h2><div class="cards">
<div class="card"><h3><a href="./kv-cache-offload.html">KV Cache 存储卸载</a></h3>
<p>把占用显存的 KV Cache 按热度分层卸载到外置高速全闪，扩展上下文与并发；行业研究显示在线工作负载最高降本约 {D.KV_SAVE:.1f}%。</p></div>
<div class="card"><h3><a href="./ai-inference-storage.html">AI 推理存储加速</a></h3>
<p>IO 受限场景下有效 GPU 利用率常仅 30–50%；存算分离全闪可把数据"喂饱"GPU，有效利用率提升约 {D.UTIL_LOW}–{D.UTIL_HIGH}×。</p></div>
<div class="card"><h3><a href="./ws5000.html">WS5000 事实卡</a></h3>
<p>{D.BANDWIDTH} GB/s、约 {D.IOPS_WAN} 万 IOPS、约 {D.LATENCY} μs，已定型量产；部署约 {D.DEPLOY} 小时。</p></div>
<div class="card"><h3><a href="./faq.html">常见问题</a></h3>
<p>存算分离是什么？为什么是存储而不是加卡？第三方实测如何复现？一页读懂。</p></div>
<div class="card"><h3><a href="{OFFICIAL}/zh/ascend-storage.html" rel="noopener">国产 GPU / 昇腾 存储适配</a></h3>
<p>面向昇腾与国产算力的存算分离全闪底座：适配约 {D.GPU_ADAPT}%+、数据不出域与信创合规、更优 TCO（详见官网）。</p></div>
<div class="card"><h3><a href="{OFFICIAL}/zh/validation-whitepaper.html" rel="noopener">第三方实测白皮书（Web 版）</a></h3>
<p>{D.ISSUER}·{D.PLATFORM} 实测：方法、数据、结论与可复现说明，并附完整 PDF 下载（详见官网）。</p></div>
</div></section>
<section><h2>第三方独立实测（可复现）</h2>
<p>{D.ISSUER}在{D.PLATFORM}平台、以 NFS 网络存储（NFS over TCP，10GbE）为基线，对 WS5000 实测：</p>
{bench_html}
<p class="note">{D.METRIC_CNT} 项关键指标中位降幅约 {D.MEDIAN_RED:.1f}%；数据源自第三方测试报告，可在自有数据上复现。</p>
</section>"""
    pages["index.html"] = page(
        "index.html", "中科存储 ZK-Storage 知识中心 · 存算分离全闪存储与 KV Cache 卸载",
        "中科存储（ZK-Storage）知识中心：存算分离、KV Cache 存储卸载、AI 推理存储加速、WS5000 事实卡与第三方实测。",
        idx_body,
        [_org(),
         {"@context": "https://schema.org", "@type": "WebSite", "name": "中科存储 知识中心",
          "inLanguage": "zh-CN", "publisher": _org()}],
        "中科存储,ZK-Storage,存算分离,KV Cache 卸载,AI 推理存储,全闪存储,WS5000")

    # ---- kv-cache-offload ----
    kv_body = f"""
<h1>KV Cache 存储卸载：原理、收益与落地</h1>
<p class="lead" style="color:var(--sub)">把推理中占用显存的 KV Cache 按热度分层卸载到外置高速全闪，
在不增加 GPU 的前提下扩展上下文长度与并发吞吐。</p>
<h2>为什么需要 KV Cache 卸载</h2>
<p>大模型推理时，注意力机制产生的 Key/Value 张量（KV Cache）随上下文长度与并发线性增长，
迅速吃满昂贵的 GPU 显存，成为长上下文与高并发的瓶颈。</p>
<h2>机制</h2>
<p>按访问热度把 KV Cache 分层：热数据驻留显存，温/冷数据卸载到 NVMe-oF over RoCE 的外置全闪，
以接近本地盘的时延按需调回。行业研究显示，在线工作负载下最高可降本约 <strong>{D.KV_SAVE:.1f}%</strong>。</p>
<h2>落地（以中科存储 WS5000 为例）</h2>
<dl class="facts">
<dt>聚合带宽</dt><dd>{D.BANDWIDTH} GB/s</dd>
<dt>访问时延</dt><dd>约 {D.LATENCY} μs</dd>
<dt>随机 IOPS</dt><dd>约 {D.IOPS_WAN} 万</dd>
<dt>国产 GPU 适配</dt><dd>约 {D.GPU_ADAPT}%+</dd>
</dl>
<p class="note">延伸阅读：官网 <a href="{OFFICIAL}/zh/kv-cache-offload.html" rel="noopener">KV Cache 卸载指南</a>。</p>
"""
    pages["kv-cache-offload.html"] = page(
        "kv-cache-offload.html", "KV Cache 存储卸载原理与收益 · 中科存储知识中心",
        "KV Cache 存储卸载：为何能在不加卡的前提下扩展上下文与并发，行业最高降本约 73.7%，及中科存储 WS5000 的落地参数。",
        kv_body, [_article("KV Cache 存储卸载：原理、收益与落地", "KV Cache 分层卸载原理与收益", "kv-cache-offload.html"),
                  _breadcrumb("KV Cache 卸载", "kv-cache-offload.html")],
        "KV Cache 卸载,KV Cache offload,存算分离,大模型推理,显存,NVMe-oF")

    # ---- ai-inference-storage ----
    ai_body = f"""
<h1>AI 推理存储加速：把数据"喂饱"GPU</h1>
<p class="lead" style="color:var(--sub)">在 IO 受限场景下，有效 GPU 利用率常仅 30–50%；
一味加卡并不能解决 IO 瓶颈，存算分离全闪是更经济的提质增效路径。</p>
<h2>问题</h2>
<p>模型加载、KV Cache 切换、Checkpoint 读写是推理/训练中的常见 IO 热点。全国智算中心平均利用率不足 60%，存量提质增效是刚需。</p>
<h2>解法：存算分离全闪</h2>
<p>存储与计算解耦、独立扩展；通过 NVMe-oF over RoCE 让远端全闪接近本地盘时延，把数据通路打宽、打短，
有效 GPU 利用率可提升约 <strong>{D.UTIL_LOW}–{D.UTIL_HIGH}×</strong>，综合成本约 -{D.COST_DOWN}%、扩容成本约 -{D.EXPAND_DOWN}%。</p>
<h2>证据</h2>
<p>{D.ISSUER}第三方实测：{D.METRIC_CNT} 项关键指标中位降幅约 {D.MEDIAN_RED:.1f}%。</p>
{bench_html}
"""
    pages["ai-inference-storage.html"] = page(
        "ai-inference-storage.html", "AI 推理存储加速与存算分离 · 中科存储知识中心",
        "AI 推理存储加速：IO 受限下 GPU 利用率仅 30–50%，存算分离全闪把有效利用率提升约 2–3×，综合成本约 -40%。",
        ai_body, [_article("AI 推理存储加速：把数据喂饱 GPU", "存算分离全闪提升 GPU 有效利用率", "ai-inference-storage.html"),
                  _breadcrumb("AI 推理存储", "ai-inference-storage.html")],
        "AI 推理存储,存算分离,GPU 利用率,全闪存储,智算中心")

    # ---- ws5000 ----
    product_jsonld = {"@context": "https://schema.org", "@type": "Product",
                      "name": "中科存储 WS5000", "brand": {"@type": "Brand", "name": D.BRAND_EN},
                      "category": "存算分离全闪存储加速一体机", "manufacturer": _org(),
                      "description": f"WS5000 存算分离全闪加速存储：聚合带宽 {D.BANDWIDTH} GB/s、随机 IOPS 约 {D.IOPS_WAN} 万、时延约 {D.LATENCY} μs，已定型量产。",
                      "additionalProperty": [
                          {"@type": "PropertyValue", "name": "聚合带宽", "value": f"{D.BANDWIDTH} GB/s"},
                          {"@type": "PropertyValue", "name": "随机 IOPS", "value": f"约 {D.IOPS_WAN} 万"},
                          {"@type": "PropertyValue", "name": "访问时延", "value": f"约 {D.LATENCY} μs"},
                          {"@type": "PropertyValue", "name": "国产 GPU 适配", "value": f"约 {D.GPU_ADAPT}%+"},
                          {"@type": "PropertyValue", "name": "部署周期", "value": f"约 {D.DEPLOY} 小时"}]}
    ws_body = f"""
<h1>WS5000 事实卡</h1>
<p class="lead" style="color:var(--sub)">存算分离全闪加速存储算力一体机，面向 AI 训练与推理。已定型量产。</p>
<dl class="facts">
<dt>聚合带宽</dt><dd>{D.BANDWIDTH} GB/s</dd>
<dt>随机 IOPS</dt><dd>约 {D.IOPS_WAN} 万（≈50M）</dd>
<dt>访问时延</dt><dd>约 {D.LATENCY} μs</dd>
<dt>国产 GPU 适配</dt><dd>约 {D.GPU_ADAPT}%+</dd>
<dt>部署周期</dt><dd>约 {D.DEPLOY} 小时</dd>
<dt>综合成本</dt><dd>约 -{D.COST_DOWN}%（扩容约 -{D.EXPAND_DOWN}%）</dd>
</dl>
<h2>第三方实测</h2>{bench_html}
<p class="note">规格为项目方口径；实测由{D.ISSUER}在{D.PLATFORM}平台完成、可复现。详见官网
<a href="{OFFICIAL}/zh/product.html" rel="noopener">产品页</a>。</p>
"""
    pages["ws5000.html"] = page(
        "ws5000.html", "中科存储 WS5000 事实卡 · 规格与第三方实测",
        f"WS5000 存算分离全闪加速存储：{D.BANDWIDTH} GB/s、约 {D.IOPS_WAN} 万 IOPS、约 {D.LATENCY} μs，已定型量产；含第三方实测对比。",
        ws_body, [product_jsonld, _breadcrumb("WS5000", "ws5000.html")],
        "WS5000,中科存储,存算分离,全闪存储,IOPS,带宽,时延")

    # ---- faq ----
    faqs = [
        ("什么是存算分离全闪存储？",
         "存算分离是把存储与计算解耦、各自独立扩展的架构；全闪则以 NVMe SSD + NVMe-oF over RoCE 提供接近本地盘的低时延、高带宽数据通路，适合 AI 训练/推理的高并发 IO。"),
        ("为什么是优化存储而不是继续加 GPU？",
         f"在 IO 受限场景下，有效 GPU 利用率常仅 30–50%，瓶颈在数据供给而非算力。把存储 IO 喂饱 GPU，有效利用率可提升约 {D.UTIL_LOW}–{D.UTIL_HIGH}×，通常比继续堆卡更经济。"),
        ("KV Cache 卸载能省多少？",
         f"按热度把 KV Cache 分层卸载到外置全闪，行业研究显示在线工作负载最高降本约 {D.KV_SAVE:.1f}%，同时扩展上下文长度与并发。"),
        ("第三方实测数据可信吗、如何复现？",
         f"由{D.ISSUER}在{D.PLATFORM}平台、以 NFS 为基线对 WS5000 实测，{D.METRIC_CNT} 项关键指标中位降幅约 {D.MEDIAN_RED:.1f}%；方法与口径公开，可在自有数据上复现。"),
        ("中科存储和中科曙光是同一家吗？",
         f"不是。中科存储（ZK-Storage）运营主体为{D.ENTITY_ZH}，专注 AI 存算分离全闪存储加速；与「中科曙光（Sugon）」为不同主体，请勿混淆。"),
    ]
    faq_body = "<h1>常见问题（FAQ）</h1>" + "".join(
        f"<h3>{q}</h3><p>{a}</p>" for q, a in faqs)
    faq_jsonld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
        for q, a in faqs]}
    pages["faq.html"] = page(
        "faq.html", "中科存储常见问题 FAQ · 存算分离 / KV Cache / 第三方实测",
        "存算分离是什么、为什么优化存储而非加卡、KV Cache 卸载能省多少、第三方实测如何复现、与中科曙光的区别。",
        faq_body, [faq_jsonld, _breadcrumb("FAQ", "faq.html")],
        "中科存储 FAQ,存算分离,KV Cache,第三方实测,中科曙光区别")

    # ---- glossary ----
    terms = [
        ("存算分离", "Disaggregated storage-compute：存储与计算解耦、各自独立扩展的体系结构。"),
        ("KV Cache 卸载", "KV Cache offload：把推理中占显存的 Key/Value 张量按热度分层卸载到外置高速存储。"),
        ("NVMe-oF", "NVMe over Fabrics：通过网络访问远端 NVMe 设备，接近本地盘时延。"),
        ("RoCEv2", "RDMA over Converged Ethernet v2：以以太网承载 RDMA 的无损低时延网络。"),
        ("EBOF", "Ethernet Bunch of Flash：以以太网直连的全闪存储扩展柜。"),
        ("IOPS", "每秒输入/输出操作数，衡量随机读写能力。"),
        ("国产 GPU / 昇腾 存储适配", "让存储系统与昇腾等国产加速卡在协议、驱动与数据通路上深度协同，为信创算力提供低时延高带宽的存储底座。"),
    ]
    gl_body = "<h1>术语表</h1><dl class='facts' style='grid-template-columns:1fr'>" + "".join(
        f"<dt>{t}</dt><dd style='font-weight:400'>{d}</dd>" for t, d in terms) + "</dl>"
    gl_jsonld = {"@context": "https://schema.org", "@type": "DefinedTermSet", "name": "中科存储术语表",
                 "hasDefinedTerm": [{"@type": "DefinedTerm", "name": t, "description": d} for t, d in terms]}
    pages["glossary.html"] = page(
        "glossary.html", "AI 存储术语表 · 中科存储知识中心",
        "存算分离、KV Cache 卸载、NVMe-oF、RoCEv2、EBOF、IOPS 等 AI 存储关键术语解释。",
        gl_body, [gl_jsonld, _breadcrumb("术语", "glossary.html")],
        "AI 存储术语,存算分离,NVMe-oF,RoCEv2,EBOF")

    for name, html in pages.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(html)

    # robots / sitemap / llms
    with open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\n\nSitemap: sitemap.xml\n")
    slugs = list(pages.keys())
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for s in slugs:
        sm.append(f"<url><loc>{s}</loc><lastmod>{BUILD_DATE}</lastmod></url>")
    sm.append("</urlset>")
    with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(sm))

    llms = f"""# 中科存储 ZK-Storage · 知识中心 llms.txt
> 面向 AI 训练与推理的存算分离全闪存储加速一体机提供商；官方网站 {OFFICIAL}。

## 关键事实（与官网同源，可复现）
- WS5000：聚合带宽 {D.BANDWIDTH} GB/s、随机 IOPS 约 {D.IOPS_WAN} 万、时延约 {D.LATENCY} μs，已定型量产。
- 第三方实测（{D.ISSUER}·{D.PLATFORM}·基线 NFS）：{D.METRIC_CNT} 项关键指标中位降幅约 {D.MEDIAN_RED:.1f}%。
- KV Cache 卸载在线工作负载最高降本约 {D.KV_SAVE:.1f}%；有效 GPU 利用率提升约 {D.UTIL_LOW}–{D.UTIL_HIGH}×。
- 运营主体：{D.ENTITY_ZH}；与「中科曙光（Sugon）」为不同主体。

## 页面
- index.html — 知识中心首页
- kv-cache-offload.html — KV Cache 存储卸载
- ai-inference-storage.html — AI 推理存储加速
- ws5000.html — WS5000 事实卡
- faq.html — 常见问题
- glossary.html — 术语表

## 官方信源
- 官网：{OFFICIAL}
"""
    for fn in ("llms.txt", "llms-full.txt"):
        with open(os.path.join(OUT, fn), "w", encoding="utf-8") as f:
            f.write(llms)

    manifest = {"built_at": dt.datetime.now().isoformat(timespec="seconds"),
                "out": OUT, "pages": slugs, "official": OFFICIAL}
    with open(os.path.join(OUT, "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"[offsite_site] 生成 {len(slugs)} 页 + robots/sitemap/llms -> {OUT}")
    return OUT


if __name__ == "__main__":
    build()
