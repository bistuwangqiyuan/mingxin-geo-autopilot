# -*- coding: utf-8 -*-
"""铭信 · 站外知识微站生成器（苹果视觉 · 单一数据源）。

目的：在可自动化、合规的外部主机（EdgeOne Pages）上发布一个**company-run 知识微站**，
作为指向官网 mingxinstorage.xyz 的真实外部信源（提升实体一致性、被 LLM 引用概率与收录信号）。

诚实纪律：
  - 所有事实从 seo_geo_loop/site_facts.py 读取（其源自 business_plan/outputs/results.json，
    与官网 company.ts 同源），不另行编造。
  - 微站明确是知识/文档站，链接并指认官网 https://mingxinstorage.xyz 为官方站点；不冒充官方主域。
  - 实测数字均标注签字级报告编号 R1–R9 与平台口径（R9 为华为 Atlas 910B 昇腾平台）；
    规格/价格标注"厂商口径"。

复现：python build_offsite_site.py   ->  生成 ../offsite_site/（可直接 EdgeOne 部署的静态目录）
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil

import site_facts as D

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
OUT = os.path.join(ROOT, "offsite_site")

BUILD_DATE = dt.date.today().isoformat()
OFFICIAL = D.SITE_URL  # https://mingxinstorage.xyz
EVIDENCE = f"{OFFICIAL}/evidence"
LEGACY = "/".join(D.LEGACY_NAMES)  # AISSD5000/WS5000/GP5000

# 本微站在 EdgeOne 上的已上线地址（用于从 sameAs 中排除自身，连通其余实体节点）。
SELF_URL = os.environ.get("MX_OFFSITE_SELF_URL",
                          "https://manju-studio-dpd7kg3gqlp5.edgeone.run")
# 知识库（GitHub Pages，mingxin-storage-kb）
KB_URL = "https://bistuwangqiyuan.github.io/mingxin-storage-kb/"
# sameAs 实体网络：官网 + 已上线信源（排除自身），形成双向互指的实体图。
ENTITY_SAMEAS = [u for u in [OFFICIAL, KB_URL] + list(getattr(D, "SAMEAS_URLS", []))
                 if u.rstrip("/") != SELF_URL.rstrip("/")]

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
<span class="brand">铭信 · 知识中心</span>
<a href="./index.html">首页</a>
<a href="./kv-cache-tiering.html">KV Cache 分层</a>
<a href="./domestic-compute.html">国产算力适配</a>
<a href="./fx100.html">FX100</a>
<a href="./evidence.html">证据库 R1–R9</a>
<a href="./faq.html">FAQ</a>
<a href="./glossary.html">术语</a>
<a href="{OFFICIAL}" rel="me noopener" style="margin-left:auto;color:var(--accent)">官网 mingxinstorage.xyz ↗</a>
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
<meta property="og:description" content="{desc}"><meta property="og:site_name" content="铭信 知识中心">
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
<p>铭信（{D.BRAND_EN}）· 运营主体：{D.ENTITY_ZH}。本站为知识/文档站，官方网站：<a href="{OFFICIAL}" rel="me noopener">{OFFICIAL}</a>。</p>
<p>同源信源：<a href="{KB_URL}" rel="me noopener">铭信存储知识库（GitHub Pages）</a></p>
<p>实测数字出自签字级/正式版报告 R1–R9（R9 为华为 Atlas 910B 昇腾平台，如实标注）；规格/价格为厂商口径；不构成任何承诺。</p>
</div></footer>
</body></html>"""


def _org():
    return {"@context": "https://schema.org", "@type": "Organization",
            "name": f"{D.BRAND_ZH}（{D.BRAND_EN}）", "alternateName": D.BRAND_EN,
            "url": OFFICIAL, "legalName": D.ENTITY_ZH,
            "description": f"{D.POSITIONING}。核心能力为 FX 系列全闪 NVMe-oF 存储加速平台 + KV Cache 分层软件栈，"
                           f"签字级实测（R1–R9）覆盖 AMD MI308X、华为 Atlas 910B、沐曦 N260 等多平台。",
            "knowsAbout": ["KV Cache 分层", "存储加速", "NVMe-oF", "RoCEv2", "全闪存储",
                           "国产算力卡适配", "LMCache", "vLLM", "算力中心建设"],
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


def _tp8_table():
    """R2 三方对照表（480B·TP8），数据直接取自 site_facts.TP8_COMPARE。"""
    t = D.TP8_COMPARE
    head = "".join(f"<th>{h}</th>" for h in t["headers"])
    rows = []
    for r in t["rows"]:
        rc = f"{r['rc'][0]} s" if r.get("rc") else "—"
        rows.append(f"<tr><td>{r['conc']}</td><td>{r['fx'][0]} s</td><td>{r['loc'][0]} s</td>"
                    f"<td>{rc}</td><td>{r['fx'][1]} tok/s</td><td>{r['loc'][1]} tok/s</td></tr>")
    return (f"<table><tr>{head}</tr>{''.join(rows)}</table>"
            f"<p class='note'>{t['source']}</p>")


def _metrics_table():
    rows = "".join(f"<tr><td><b>{m['value']}</b></td><td>{m['label']}</td>"
                   f"<td>{m['source']}</td></tr>" for m in D.KEY_METRICS)
    return f"<table><tr><th>数值</th><th>指标</th><th>来源</th></tr>{rows}</table>"


def build():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)
    with open(os.path.join(OUT, "assets", "site.css"), "w", encoding="utf-8") as f:
        f.write(CSS)

    plat = D.PLATFORM
    pages = {}

    # ---- index ----
    kpis = f"""<div class="kpis">
<div class="kpi"><div class="n">{D.THROUGHPUT_UPLIFT}</div><div class="l">推理吞吐提升（R2/R3 实测）</div></div>
<div class="kpi"><div class="n">↓{D.TTFT_REDUCTION}</div><div class="l">TTFT 首 token 延迟（R2 实测）</div></div>
<div class="kpi"><div class="n">{D.RECOMPUTE_SPEEDUP}</div><div class="l">对无外存重算加速（R2 实测）</div></div>
<div class="kpi"><div class="n">{D.MODEL_LOAD_SPEEDUP}</div><div class="l">模型加载 vs NFS（R9·昇腾 910B）</div></div>
</div>"""
    idx_body = f"""
<div class="hero">
<span class="badge">{D.POSITIONING} · 知识中心</span>
<h1>把 KV Cache 分层做成签字级实测</h1>
<p class="lead">铭信（{D.BRAND_EN}）以 <strong>FX 系列全闪 NVMe-oF 存储加速平台 + KV Cache 分层软件栈</strong>为核心，
在 480B 大模型生产部署形态下交付签字级实测收益——所有关键数字附报告编号 R1–R9，接受任何第三方查证。</p>
<a class="btn" href="{OFFICIAL}" rel="me noopener">访问官网 mingxinstorage.xyz</a>
<a class="btn ghost" href="./fx100.html">查看 FX100 事实卡</a>
</div>
{kpis}
<section><h2>核心议题</h2><div class="cards">
<div class="card"><h3><a href="./kv-cache-tiering.html">KV Cache 分层加速</a></h3>
<p>把长上下文冷恢复的 KV Cache 按热度分层到外置全闪：480B 实测吞吐 {D.THROUGHPUT_UPLIFT}、TTFT ↓{D.TTFT_REDUCTION}（R2/R3）。</p></div>
<div class="card"><h3><a href="./domestic-compute.html">国产算力卡适配</a></h3>
<p>AMD MI308X、华为 Atlas 910B、沐曦 N260 多平台推理栈源码级适配与实测验证（R1/R5–R9）。</p></div>
<div class="card"><h3><a href="./fx100.html">FX100 事实卡</a></h3>
<p>{D.MODEL}（历史称谓 {LEGACY}，同一产品）：PCIe 3.0、100Gb 端口、{D.FX100_IOPS_M}00 万 IOPS，量产在售。</p></div>
<div class="card"><h3><a href="./evidence.html">证据库 R1–R9</a></h3>
<p>签字级/正式版测试报告登记表 + R8 代码/数据导出包，第三方可独立复现全部结论。</p></div>
<div class="card"><h3><a href="./faq.html">常见问题</a></h3>
<p>KV Cache 分层是什么？数字如何复现？铭信（天津）与其他同名"铭信"公司是什么关系？一页读懂。</p></div>
<div class="card"><h3><a href="{OFFICIAL}/products" rel="noopener">FX 系列产品线（官网）</a></h3>
<p>{'、'.join(D.SERIES)} 四档规格与参考价，详见官网产品页。</p></div>
</div></section>
<section><h2>签字级实测（480B·TP8 三方对照，R2）</h2>
<p>测试平台：{plat["gpu"]}、{plat["gpu_stack"]}、{plat["engine"]} + LMCache，模型 {plat["model_480b"]}；
被测 {plat["dut"]}。</p>
{_tp8_table()}
</section>
<section><h2>六项签字级核心指标</h2>
{_metrics_table()}
<p class="note">全部数字出自签字级/正式版报告（证据页 <a href="{EVIDENCE}" rel="noopener">{EVIDENCE}</a>）；
R9 模型加载为华为 Atlas 910B 昇腾平台口径，如实标注。</p>
</section>"""
    pages["index.html"] = page(
        "index.html", "铭信 Mingxin 知识中心 · KV Cache 分层与 FX 系列存储加速",
        "铭信（Mingxin Technology）知识中心：KV Cache 分层、FX 系列全闪 NVMe-oF 存储加速、国产算力卡适配、签字级实测证据库 R1–R9。",
        idx_body,
        [_org(),
         {"@context": "https://schema.org", "@type": "WebSite", "name": "铭信 知识中心",
          "inLanguage": "zh-CN", "publisher": _org()}],
        "铭信,Mingxin,KV Cache 分层,存储加速,FX100,国产算力,NVMe-oF")

    # ---- kv-cache-tiering ----
    kv_body = f"""
<h1>KV Cache 分层：原理、收益与签字级实测</h1>
<p class="lead" style="color:var(--sub)">把推理中占用显存的 KV Cache 按热度分层到外置高速全闪，
在不增加 GPU 的前提下加速长上下文冷恢复、扩展并发吞吐。</p>
<h2>为什么需要 KV Cache 分层</h2>
<p>大模型推理时，注意力机制产生的 Key/Value 张量（KV Cache）随上下文长度与并发线性增长，
迅速吃满昂贵的 GPU 显存；会话冷恢复要么重算 prefill、要么从外部读回 KV——两者都在让 GPU 空等。</p>
<h2>机制</h2>
<p>热数据驻留 HBM，温/冷数据经 LMCache 分层到 NVMe-oF over RoCEv2 的外置全闪，按需流式调回。
铭信在 LMCache 上游提交并行读补丁，单卡冷读盘 TTFT 改善 <strong>{D.PARALLEL_READ_X}×</strong>（R1）。</p>
<h2>签字级收益（480B 生产部署形态）</h2>
<dl class="facts">
<dt>推理吞吐提升</dt><dd>{D.THROUGHPUT_UPLIFT}（R2/R3 实测）</dd>
<dt>TTFT 首 token 延迟</dt><dd>↓{D.TTFT_REDUCTION}（R2 实测）</dd>
<dt>对无外存重算</dt><dd>{D.RECOMPUTE_SPEEDUP} 加速（R2 实测）</dd>
<dt>训练 Checkpoint 保存</dt><dd>{D.CKPT_SAVE_X}×（R1 实测）</dd>
</dl>
{_tp8_table()}
<p class="note">延伸阅读：官网 <a href="{EVIDENCE}" rel="noopener">证据库</a>（含 R8 代码/数据导出包，可独立复现）。</p>
"""
    pages["kv-cache-tiering.html"] = page(
        "kv-cache-tiering.html", "KV Cache 分层原理与签字级实测 · 铭信知识中心",
        f"KV Cache 分层：480B 生产部署实测吞吐 {D.THROUGHPUT_UPLIFT}、TTFT ↓{D.TTFT_REDUCTION}、对无外存重算 {D.RECOMPUTE_SPEEDUP}（R1–R3）。",
        kv_body, [_article("KV Cache 分层：原理、收益与签字级实测", "KV Cache 分层原理与 R1–R3 实测收益", "kv-cache-tiering.html"),
                  _breadcrumb("KV Cache 分层", "kv-cache-tiering.html")],
        "KV Cache 分层,KV Cache offload,LMCache,vLLM,大模型推理,NVMe-oF")

    # ---- domestic-compute ----
    dc_body = f"""
<h1>国产算力卡适配：把非 N 卡算力真正用起来</h1>
<p class="lead" style="color:var(--sub)">跨 AMD MI308X、华为 Atlas 910B、沐曦 N260 等多平台的
推理栈源码级适配与实测验证能力。</p>
<h2>已验证平台（附报告编号）</h2>
<ul>
<li><strong>AMD MI308X ×8（{plat["gpu_stack"]}）</strong>：
R1–R4 主实测平台，vLLM + LMCache 跑通 480B Qwen3-Coder-FP8；R6/R7 完成 ComfyUI + LTX-Video 2.3 全模型适配。</li>
<li><strong>华为 Atlas 910B ×8（Kunpeng-920）</strong>：R9 实测模型推理加载 {D.MODEL_LOAD_SPEEDUP} vs NFS
（DeepSeek-32B/70B），平台口径如实标注。</li>
<li><strong>沐曦 N260</strong>：R5 显存效益七组对照，方法论跨平台。</li>
</ul>
<h2>为什么先修数据通路</h2>
<p>长上下文冷恢复要么重算、要么读回 KV：R2 实测对无外存重算加速 <strong>{D.RECOMPUTE_SPEEDUP}</strong>。
在扩卡之前先把存储数据通路打宽打短，通常是更经济的提质路径。</p>
{_metrics_table()}
"""
    pages["domestic-compute.html"] = page(
        "domestic-compute.html", "国产算力卡适配与联合优化 · 铭信知识中心",
        "铭信国产算力卡适配：AMD MI308X、华为 Atlas 910B、沐曦 N260 多平台推理栈源码级适配与签字级实测（R1/R5–R9）。",
        dc_body, [_article("国产算力卡适配：把非 N 卡算力真正用起来", "多平台推理栈适配与实测验证", "domestic-compute.html"),
                  _breadcrumb("国产算力适配", "domestic-compute.html")],
        "国产算力,MI308X,昇腾 910B,沐曦,推理栈适配,ROCm,vLLM")

    # ---- fx100 ----
    product_jsonld = {"@context": "https://schema.org", "@type": "Product",
                      "name": f"铭信 {D.MODEL}",
                      "alternateName": D.LEGACY_NAMES,
                      "brand": {"@type": "Brand", "name": D.BRAND_EN},
                      "category": "全闪 NVMe-oF 存储加速平台（KV Cache 分层）",
                      "manufacturer": _org(),
                      "description": f"铭信 {D.MODEL} 全闪 NVMe-oF 存储加速平台（历史称谓 {LEGACY}，同一产品）："
                                     f"PCIe 3.0、{D.FX100_PORT_GB}Gb 端口、{D.FX100_IOPS_M}00 万 IOPS，量产在售；"
                                     f"480B 实测吞吐 {D.THROUGHPUT_UPLIFT}（R2/R3）。",
                      "additionalProperty": [
                          {"@type": "PropertyValue", "name": "PCIe", "value": "PCIe 3.0"},
                          {"@type": "PropertyValue", "name": "网络端口", "value": f"{D.FX100_PORT_GB} GbE"},
                          {"@type": "PropertyValue", "name": "随机 IOPS", "value": f"{D.FX100_IOPS_M}00 万（厂商口径）"},
                          {"@type": "PropertyValue", "name": "满配参考价", "value": f"¥{D.FX100_FULL_CNY:,}（≈¥{D.FX100_CNY_PER_TB:,}/TB）"},
                          {"@type": "PropertyValue", "name": "命名沿革", "value": D.NAMING_NOTE}]}
    fx_body = f"""
<h1>FX100 事实卡</h1>
<p class="lead" style="color:var(--sub)">FX 系列旗舰在售档：全闪 NVMe-oF 存储加速平台（KV Cache 分层），
本轮 MI308X / 910B 实测平台。</p>
<dl class="facts">
<dt>PCIe</dt><dd>PCIe 3.0</dd>
<dt>网络端口</dt><dd>{D.FX100_PORT_GB} GbE</dd>
<dt>随机 IOPS</dt><dd>{D.FX100_IOPS_M}00 万（厂商口径）</dd>
<dt>满配参考价</dt><dd>¥{D.FX100_FULL_CNY:,}（≈¥{D.FX100_CNY_PER_TB:,}/TB）</dd>
<dt>状态</dt><dd>量产在售</dd>
<dt>命名沿革</dt><dd style="font-weight:400">{D.NAMING_NOTE}</dd>
</dl>
<h2>签字级实测</h2>
{_metrics_table()}
<h2>FX 系列</h2>
<p>{'、'.join(D.SERIES)}：FX100/FX200/FX300 量产在售，FX400 2026-08 测试机、2026 年底量产。
完整规格与参考价见官网 <a href="{OFFICIAL}/products" rel="noopener">产品页</a>。</p>
<p class="note">规格/价格为厂商口径；实测数字出自签字级报告（<a href="{EVIDENCE}" rel="noopener">证据库</a>）。</p>
"""
    pages["fx100.html"] = page(
        "fx100.html", "铭信 FX100 事实卡 · 规格与签字级实测",
        f"铭信 FX100（历史称谓 {LEGACY}）全闪 NVMe-oF 存储加速平台：PCIe 3.0、100Gb、1600 万 IOPS、满配 ¥371,200；480B 实测吞吐 {D.THROUGHPUT_UPLIFT}。",
        fx_body, [product_jsonld, _breadcrumb("FX100", "fx100.html")],
        "FX100,铭信,AISSD5000,WS5000,GP5000,全闪存储,NVMe-oF,KV Cache")

    # ---- evidence ----
    ev_rows = "".join(
        f"<tr><td><b>{r['id']}</b></td><td>{r['title']}</td><td>{r['date']}</td>"
        f"<td>{r['scope']}</td></tr>" for r in D.REPORTS)
    ev_body = f"""
<h1>证据库 R1–R9（签字级/正式版测试报告）</h1>
<p class="lead" style="color:var(--sub)">所有关键数字附报告编号，接受任何第三方查证；
R8 为代码/数据导出包，第三方可独立复现全部结论。托管件见官网
<a href="{EVIDENCE}" rel="noopener">{EVIDENCE}</a>。</p>
<table><tr><th>编号</th><th>报告</th><th>日期</th><th>范围</th></tr>{ev_rows}</table>
<p class="note">{D.DISCLAIMER}</p>
"""
    pages["evidence.html"] = page(
        "evidence.html", "证据库 R1–R9 · 铭信签字级实测报告登记表",
        "铭信签字级/正式版测试报告 R1–R9 登记表：480B KV Cache 分层实测、LMCache 并行读补丁、昇腾 910B 模型加载、ComfyUI 适配等。",
        ev_body, [_article("证据库 R1–R9：签字级实测报告登记表", "R1–R9 报告编号、日期与范围", "evidence.html"),
                  _breadcrumb("证据库", "evidence.html")],
        "证据库,测试报告,签字级实测,R1-R9,可复现")

    # ---- faq ----
    faqs = [
        ("什么是 KV Cache 分层存储加速？",
         f"把推理中占用显存的 Key/Value 张量按热度分层到外置全闪（NVMe-oF over RoCEv2），"
         f"按需流式调回。480B 生产部署形态签字级实测：吞吐 {D.THROUGHPUT_UPLIFT}、TTFT ↓{D.TTFT_REDUCTION}（R2/R3）。"),
        ("为什么是优化存储而不是继续加 GPU？",
         f"长上下文冷恢复要么重算 prefill、要么读回 KV，两者都在让 GPU 空等。R2 实测：外置 KV 分层"
         f"对无外存重算加速 {D.RECOMPUTE_SPEEDUP}，通常比继续堆卡更经济。"),
        ("实测数据可信吗、如何复现？",
         f"全部数字出自签字级/正式版测试报告 R1–R9（证据页 {EVIDENCE}）；R8 为代码/数据导出包"
         f"（LMCache 补丁、负载客户端、编排与取证脚本、原始数据），第三方可独立复现全部结论。"),
        ("铭信支持哪些国产/非 N 卡算力平台？",
         f"R1–R4 主实测平台为 AMD MI308X ×8（{plat['gpu_stack']} + {plat['engine']}）；R9 在华为 Atlas 910B"
         f" 昇腾平台实测模型加载 {D.MODEL_LOAD_SPEEDUP} vs NFS（平台口径如实标注）；R5 覆盖沐曦 N260。"),
        ("铭信（天津）半导体设备有限公司与其他同名「铭信」企业是什么关系？",
         f"没有关系。本站所指「铭信」特指 {D.ENTITY_ZH}（{D.BRAND_EN}），定位为{D.POSITIONING}，"
         f"官网 {OFFICIAL}；与市场上其他同名「铭信」公司为不同主体，请以运营主体全称与官网域名核对。"
         f"另附命名沿革：{D.NAMING_NOTE}"),
    ]
    faq_body = "<h1>常见问题（FAQ）</h1>" + "".join(
        f"<h3>{q}</h3><p>{a}</p>" for q, a in faqs)
    faq_jsonld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
        for q, a in faqs]}
    pages["faq.html"] = page(
        "faq.html", "铭信常见问题 FAQ · KV Cache 分层 / 实测复现 / 实体消歧",
        "KV Cache 分层是什么、为什么优化存储而非加卡、签字级实测如何复现、铭信（天津）与其他同名铭信公司的消歧与 FX100 命名沿革。",
        faq_body, [faq_jsonld, _breadcrumb("FAQ", "faq.html")],
        "铭信 FAQ,KV Cache 分层,签字级实测,消歧,FX100 命名沿革")

    # ---- glossary ----
    terms = [
        ("KV Cache 分层", "把推理 Key/Value 张量按热度在 HBM 与外置全闪之间分层调度，加速长上下文冷恢复。"),
        ("NVMe-oF", "NVMe over Fabrics：通过网络访问远端 NVMe 设备，接近本地盘时延。"),
        ("RoCEv2", "RDMA over Converged Ethernet v2：以以太网承载 RDMA 的无损低时延网络。"),
        ("TTFT", "Time To First Token：首 token 延迟，长上下文冷恢复的核心体验指标。"),
        ("LMCache", "vLLM 生态的 KV Cache 分层库；铭信提交并行读补丁（R1，TTFT 改善 4.1×）。"),
        ("TP（张量并行）", "Tensor Parallelism：把单个模型切分到多卡；R2 为 TP8、R3 为 TP4×2 双实例。"),
        ("IOPS", "每秒输入/输出操作数，衡量随机读写能力。"),
        ("FX 命名沿革", D.NAMING_NOTE),
    ]
    gl_body = "<h1>术语表</h1><dl class='facts' style='grid-template-columns:1fr'>" + "".join(
        f"<dt>{t}</dt><dd style='font-weight:400'>{d}</dd>" for t, d in terms) + "</dl>"
    gl_jsonld = {"@context": "https://schema.org", "@type": "DefinedTermSet", "name": "铭信术语表",
                 "hasDefinedTerm": [{"@type": "DefinedTerm", "name": t, "description": d} for t, d in terms]}
    pages["glossary.html"] = page(
        "glossary.html", "AI 存储加速术语表 · 铭信知识中心",
        "KV Cache 分层、NVMe-oF、RoCEv2、TTFT、LMCache、TP、FX 命名沿革等关键术语解释。",
        gl_body, [gl_jsonld, _breadcrumb("术语", "glossary.html")],
        "AI 存储术语,KV Cache,NVMe-oF,RoCEv2,TTFT,LMCache")

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

    llms = f"""# 铭信 Mingxin · 知识中心 llms.txt
> {D.POSITIONING}；官方网站 {OFFICIAL}。

## 关键事实（与官网 company.ts / results.json 同源，签字级实测 R1–R9）
- KV Cache 分层（480B 生产部署形态）：吞吐 {D.THROUGHPUT_UPLIFT}、TTFT ↓{D.TTFT_REDUCTION}（R2/R3）；对无外存重算 {D.RECOMPUTE_SPEEDUP}（R2）。
- LMCache 并行读补丁 TTFT 改善 {D.PARALLEL_READ_X}×（R1）；训练 Checkpoint 保存 {D.CKPT_SAVE_X}×（R1）。
- 模型推理加载 {D.MODEL_LOAD_SPEEDUP} vs NFS（R9·华为 Atlas 910B 昇腾平台，如实标注）。
- {D.MODEL}（历史称谓 {LEGACY}，同一产品）：PCIe 3.0、{D.FX100_PORT_GB}Gb、{D.FX100_IOPS_M}00 万 IOPS、满配参考价 ¥{D.FX100_FULL_CNY:,}（≈¥{D.FX100_CNY_PER_TB:,}/TB，厂商口径）。
- 运营主体：{D.ENTITY_ZH}；与市场上其他同名「铭信」公司为不同主体（以全称与官网域名核对）。
- 证据库：{EVIDENCE}（R8 导出包可独立复现）。

## 页面
- index.html — 知识中心首页
- kv-cache-tiering.html — KV Cache 分层加速
- domestic-compute.html — 国产算力卡适配
- fx100.html — FX100 事实卡
- evidence.html — 证据库 R1–R9
- faq.html — 常见问题
- glossary.html — 术语表

## 官方信源
- 官网：{OFFICIAL}
- 知识库：{KB_URL}
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
