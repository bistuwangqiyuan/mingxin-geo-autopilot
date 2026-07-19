# -*- coding: utf-8 -*-
"""铭信官网 · 线上真实现状测评（收录 / 排名 / 在线技术 SEO / 性能 / GEO 汇总）。

诚实纪律：
  - 收录与排名:无第三方付费 SERP API,沿用本仓既有方法(agent/人工 web_search 实查),
    把当日真实观测(日期/引擎/查询/结果/证据域名)落盘到 seo/data/serp_observations.csv
    与 live_status.json,如实标注"尚未收录、未进榜"。绝不编造名次。
  - 在线技术 SEO:对**线上** mingxinstorage.xyz 页面抓原始 HTML 做确定性核对
    (JSON-LD/canonical/hreflang/og/twitter/答案块等),据此判断线上部署版本。
  - 性能:读取 lighthouse.py 的真实测量(PSI 或 Playwright 实验室),标注 method。
  - GEO/CRI:汇总 gvi_compare.json 与最新 CRI 快照。

复现：python live_audit.py
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
OUT = os.path.join(BASE, "outputs")
SERP_CSV = os.path.join(ROOT, "seo", "data", "serp_observations.csv")
TODAY = dt.date.today().isoformat()

SITE = os.environ.get("MX_SITE_URL", "https://mingxinstorage.xyz").rstrip("/")
HOST = SITE.split("://", 1)[-1]

LIVE_PAGES = [
    f"{SITE}/",
    f"{SITE}/products",
    f"{SITE}/evidence",
    f"{SITE}/en",
]

# 真实 web_search 实查结果（与既有 serp_observations.csv 方法一致）。
# 证据域名为实际返回的头部结果；我方未出现即 not_ranked，site: 无结果即 not_indexed。
# 首轮铭信基线观测待跑（用 agent web_search 实查后回填），此处仅登记待办口径。
SERP_OBSERVATION_DATE = "pending"
SERP_OBSERVATIONS = [
    {"engine": "google", "query": f"site:{HOST}", "our_position": "pending",
     "observed_top_domains": "(待实查)", "source": "pending",
     "notes": "铭信基线首轮 site: 实查待做（agent web_search）；结果如实回填。"},
    {"engine": "google", "query": "铭信 FX100 KV Cache 分层 存储加速", "our_position": "pending",
     "observed_top_domains": "(待实查)", "source": "pending",
     "notes": "品牌+产品词首轮实查待做；注意与其他『铭信』同名主体的消歧观察。"},
    {"engine": "bing", "query": f"site:{HOST}", "our_position": "pending",
     "observed_top_domains": "(待实查)", "source": "pending",
     "notes": "站点自带 /api/seo/ping 持续推送 IndexNow；公开收录进度待实查。"},
    {"engine": "baidu", "query": "铭信 存储加速", "our_position": "pending",
     "observed_top_domains": "(待实查)", "source": "pending",
     "notes": "站点已接百度主动推送（配额小、只推新文章 URL）；收录进度待实查。"},
]


def _fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Mingxin SEO audit)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace"), r.status


def _onpage(html):
    def has(p):
        return bool(re.search(p, html, re.I | re.S))
    types = []
    for raw in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            o = json.loads(raw)
            for it in (o if isinstance(o, list) else [o]):
                if isinstance(it, dict) and isinstance(it.get("@type"), str):
                    types.append(it["@type"])
        except Exception:
            pass
    return {
        "title": (re.search(r"<title>(.*?)</title>", html, re.S | re.I).group(1).strip()
                  if has(r"<title>") else ""),
        "has_description": has(r'<meta\s+name="description"'),
        "canonical": has(r'rel="canonical"'),
        "hreflang_count": len(re.findall(r'rel="alternate"\s+hreflang', html, re.I)),
        "h1_count": len(re.findall(r"<h1\b", html, re.I)),
        "jsonld_count": html.count("application/ld+json"),
        "jsonld_types": sorted(set(types)),
        "og": has(r'property="og:'),
        "twitter_title": has(r'name="twitter:'),
        "theme_color": has(r'name="theme-color"'),
        "brand_entity": ("铭信" in html and ("Mingxin" in html or "FX100" in html)),
        "naming_note": ("WS5000" in html or "AISSD5000" in html),
        "last_updated_time": bool(re.search(r"<time\s+datetime=", html, re.I)),
        "html_len": len(html),
    }


def _append_serp_csv():
    os.makedirs(os.path.dirname(SERP_CSV), exist_ok=True)
    exists = os.path.exists(SERP_CSV)
    rows = []
    if exists:
        with open(SERP_CSV, "r", encoding="utf-8") as f:
            rows = list(csv.reader(f))
    header = ["date", "engine", "query", "our_position", "observed_top_domains", "source", "notes"]
    if not rows:
        rows = [header]
    have = {(r[0], r[1], r[2]) for r in rows[1:] if len(r) >= 3}
    added = 0
    for o in SERP_OBSERVATIONS:
        if o.get("source") == "pending":
            continue  # 未实查的不落盘，避免污染观测记录
        key = (TODAY, o["engine"], o["query"])
        if key in have:
            continue
        rows.append([TODAY, o["engine"], o["query"], o["our_position"],
                     o["observed_top_domains"], o["source"], o["notes"]])
        added += 1
    with open(SERP_CSV, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(rows)
    return added


def run():
    os.makedirs(OUT, exist_ok=True)
    live = []
    for u in LIVE_PAGES:
        try:
            html, status = _fetch(u)
            live.append({"url": u, "status": status, "onpage": _onpage(html)})
        except Exception as e:  # noqa: BLE001
            live.append({"url": u, "status": None, "error": str(e)})

    added = _append_serp_csv()

    # 汇总既有真实结果
    def _read(p):
        return json.load(open(p, "r", encoding="utf-8")) if os.path.exists(p) else None
    gvi = _read(os.path.join(OUT, "gvi_compare.json"))
    final = _read(os.path.join(OUT, "snapshots", "final_best.json"))
    final_v2 = _read(os.path.join(OUT, "snapshots", "final_best_v2.json"))
    lh = _read(os.path.join(OUT, "lighthouse.json"))
    indexnow = _read(os.path.join(OUT, "indexnow_submit.json"))
    prior = _read(os.path.join(OUT, "live_status.json")) or {}

    home = next((x for x in live if x["url"].rstrip("/") == SITE), {})
    op = home.get("onpage", {})
    live_ok = bool(op.get("jsonld_count") and op.get("brand_entity"))

    google_idx = (prior.get("indexing", {}) or {}).get("google_site") or "pending"

    cri_best = None
    if final_v2 and isinstance(final_v2, dict):
        cri_best = final_v2.get("cri")
    if cri_best is None and final and isinstance(final, dict):
        cri_best = final.get("cri")
    if cri_best is None:
        cri_best = prior.get("cri_local_best")

    status = {
        "computed_at": dt.datetime.now().isoformat(timespec="seconds"),
        "site": SITE,
        "method_note": ("收录/排名为 agent web_search 实查(无付费 SERP API);在线技术 SEO 为线上 HTML "
                        "确定性核对;性能见 lighthouse.json(method=psi/lab)。"),
        "indexing": {"google_site": google_idx,
                     "bing_site": prior.get("indexing", {}).get("bing_site") or "pending",
                     "baidu": prior.get("indexing", {}).get("baidu") or "pending"},
        "ranking_summary": prior.get("ranking_summary") or "铭信基线首轮 SERP 实查待做；结果如实回填，绝不编造名次。",
        "serp_observation_date": SERP_OBSERVATION_DATE,
        "serp_observations_today": SERP_OBSERVATIONS,
        "serp_rows_appended": added,
        "live_onpage": live,
        "live_deploy_ok": live_ok,
        "deploy_note": ("mingxinstorage.xyz 为 Next.js 站点（Vercel mingxin-site），自带内容引擎与 "
                        "robots/llms.txt/sitemap/JSON-LD；本审计对线上 HTML 做确定性核对以确认部署版本。"),
        "gvi": ({"start": gvi["start"]["gvi"], "end": gvi["end"]["gvi"]} if gvi else prior.get("gvi")),
        "cri_local_best": cri_best,
        "lighthouse": lh,
        "indexnow": ({"submitted_at": indexnow.get("submitted_at"),
                      "url_count": indexnow.get("sitemap", {}).get("url_count"),
                      "seo_ping_status": (indexnow.get("seo_ping") or {}).get("status"),
                      "endpoints": {k: v.get("status") for k, v in (indexnow.get("indexnow", {}) or {}).items()}}
                     if indexnow else prior.get("indexnow")),
        "index_acceleration_checklist": [
            "开通并验证 Google Search Console / 百度站长 / Bing Webmaster,提交 sitemap.xml",
            "常态化调用站点 /api/seo/ping（IndexNow + 百度主动推送 + WebSub，需 CRON_SECRET）",
            "确保 robots.txt 放行 AI 爬虫（GPTBot/ClaudeBot/PerplexityBot 等，站点已具备）",
            "通过站外高权重信源(GitHub 知识库/EdgeOne 微站/百科/媒体)建立指向 mingxinstorage.xyz 的真实外链",
            "强化『铭信 Mingxin / FX100（历史称谓 WS5000/AISSD5000/GP5000）』实体词与 sameAs 实体锚点",
        ],
    }
    # 保留浏览器人工取证的 GSC 字段（API 不可得,不可由脚本复算,故合并保留并标注来源日期）。
    for k in ("gsc_account", "gsc_url_inspection"):
        if prior.get(k):
            status[k] = prior[k]
    with open(os.path.join(OUT, "live_status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

    print(f"[live_audit] 站点 {SITE}: 线上核对 {sum(1 for x in live if x.get('status') == 200)}/{len(live)} 页 200。")
    print(f"  首页 JSON-LD 数: {op.get('jsonld_count')}; 品牌实体在页: {op.get('brand_entity')}")
    print(f"  GVI: {status['gvi']}; 本地最佳 CRI: {status['cri_local_best']}")
    print(f"  SERP 追加 {added} 行 -> {SERP_CSV}")
    print(f"  写出 -> {os.path.join(OUT, 'live_status.json')}")


if __name__ == "__main__":
    run()
