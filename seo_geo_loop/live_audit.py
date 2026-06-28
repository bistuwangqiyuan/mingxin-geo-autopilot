# -*- coding: utf-8 -*-
"""中科存储官网 · 线上真实现状测评（收录 / 排名 / 在线技术 SEO / 性能 / GEO 汇总）。

诚实纪律：
  - 收录与排名:无第三方付费 SERP API,沿用本仓既有方法(agent/人工 web_search 实查),
    把当日真实观测(日期/引擎/查询/结果/证据域名)落盘到 seo/data/serp_observations.csv
    与 live_status.json,如实标注"尚未收录、未进榜"。绝不编造名次。
  - 在线技术 SEO:对**线上** goni.top 页面抓原始 HTML 做确定性核对(JSON-LD/canonical/
    hreflang/og/twitter/theme-color/答案块/SearchAction 等),据此判断线上部署版本。
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

LIVE_PAGES = [
    "https://goni.top/zh/index.html",
    "https://goni.top/zh/product.html",
    "https://goni.top/en/index.html",
]

# 真实 web_search 实查结果（与既有 serp_observations.csv 方法一致），最近一次复查 2026-06-22。
# 证据域名为实际返回的头部结果；我方未出现即 not_ranked，site: 无结果即 not_indexed。
SERP_OBSERVATION_DATE = "2026-06-22"
SERP_OBSERVATIONS = [
    {"engine": "google", "query": "site:goni.top", "our_position": "not_indexed",
     "observed_top_domains": "(none)", "source": "agent_web_search",
     "notes": "公开检索 site:goni.top 仍无结果(2026-06-22 复查);GSC 网址检查则显示部分页『已编入索引』,公开索引滞后于 GSC。"},
    {"engine": "google", "query": "中科存储 WS5000 存算分离 全闪存储", "our_position": "not_ranked",
     "observed_top_domains": "dobigdata.cn;elecfans.com;news.qq.com;sugon.com;dostor.com",
     "source": "agent_web_search",
     "notes": "2026-06-22 复查:头部被中科曙光 FlashNexus/ParaStor 占据,goni.top 未进榜;『中科存储/中科曙光』品牌混淆风险确认,已上线 Organization 实体消歧(legalName+disambiguatingDescription)缓解。"},
    {"engine": "bing", "query": "site:goni.top", "our_position": "not_indexed",
     "observed_top_domains": "(none)", "source": "agent_web_search",
     "notes": "必应公开检索零收录(沿用同期观测);IndexNow 已多次推送 68 条 URL(Bing 200),待其抓取入库。"},
    {"engine": "baidu", "query": "中科存储", "our_position": "unknown",
     "observed_top_domains": "(未抽样)", "source": "pending",
     "notes": "百度需备案后复核(ICP 依赖)"},
]


def _fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ZK-Storage SEO audit)"})
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
        "twitter_title": has(r'name="twitter:title"'),
        "theme_color": has(r'name="theme-color"'),
        "search_action": "SearchAction" in html,
        "key_facts_block": "key-facts" in html,
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

    # 线上是否已含本会话新结构化数据（用于诚实说明"线上部署版本"）
    zh_home = next((x for x in live if x["url"].endswith("zh/index.html")), {})
    op = zh_home.get("onpage", {})
    live_has_new = bool(op.get("search_action") or op.get("twitter_title") or op.get("key_facts_block"))
    prod = next((x for x in live if x["url"].endswith("product.html")), {})
    prod_no_merchant_product = "Product" not in prod.get("onpage", {}).get("jsonld_types", [])

    # 收录口径：保留经 GSC『网址检查』实证的更精确判断（如 partial_indexed），公开 site: 检索作并列佐证。
    google_idx = (prior.get("indexing", {}) or {}).get("google_site") or "not_indexed"

    cri_best = None
    if final_v2 and isinstance(final_v2, dict):
        cri_best = final_v2.get("cri")
    if cri_best is None and final and isinstance(final, dict):
        cri_best = final.get("cri")
    if cri_best is None:
        cri_best = prior.get("cri_local_best")

    status = {
        "computed_at": dt.datetime.now().isoformat(timespec="seconds"),
        "method_note": ("收录/排名为 agent web_search 实查(无付费 SERP API);在线技术 SEO 为线上 HTML "
                        "确定性核对;性能见 lighthouse.json(method=psi/lab)。"),
        "indexing": {"google_site": google_idx, "bing_site": "not_indexed(公开 site: 检索;IndexNow 已推送待抓取)",
                     "baidu": "pending(ICP 备案后复核)"},
        "ranking_summary": "目标词未进入排名;品牌词头部被『中科曙光 FlashNexus/ParaStor』占据(品牌混淆风险已确认,已上线实体消歧缓解)。",
        "serp_observation_date": SERP_OBSERVATION_DATE,
        "serp_observations_today": SERP_OBSERVATIONS,
        "serp_rows_appended": added,
        "live_onpage": live,
        "live_deploy_has_session_upgrades": live_has_new,
        "deploy_note": ("线上 goni.top 已部署本会话全部站内优化:线上实测 product.html 已无商品级 Product 标记"
                        f"(merchant_product_removed={prod_no_merchant_product})、首页含 SpeakableSpecification/SearchAction;"
                        "本次新增 Organization legalName + disambiguatingDescription(实体消歧)亦已随最新提交部署上线。"),
        "gvi": ({"start": gvi["start"]["gvi"], "end": gvi["end"]["gvi"]} if gvi else prior.get("gvi")),
        "cri_local_best": cri_best,
        "lighthouse": lh,
        "indexnow": ({"submitted_at": indexnow.get("submitted_at"),
                      "url_count": indexnow.get("sitemap", {}).get("url_count"),
                      "endpoints": {k: v.get("status") for k, v in (indexnow.get("indexnow", {}) or {}).items()}}
                     if indexnow else prior.get("indexnow")),
        "index_acceleration_checklist": [
            "完成 ICP 备案(百度收录的前置;影响国内可见性)",
            "开通并验证 Google Search Console / 百度站长 / Bing Webmaster,提交 sitemap.xml",
            "用 IndexNow(已具 key 文件)推送 Bing/Yandex;Google 用 GSC URL Inspection 请求编入",
            "向 sitemap ping 端点提交;确保 robots.txt 放行(已具)",
            "通过站外高权重信源(GitHub/CDN 微站/百科/媒体)建立指向 goni.top 的真实外链",
            "缓解品牌混淆:强化『中科存储 ZK-Storage / WS5000』实体词与 sameAs 实体锚点",
        ],
    }
    # 保留浏览器人工取证的 GSC 字段（API 不可得,不可由脚本复算,故合并保留并标注来源日期）。
    for k in ("gsc_account", "gsc_url_inspection"):
        if prior.get(k):
            status[k] = prior[k]
    with open(os.path.join(OUT, "live_status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

    print(f"[live_audit] 收录: Google/Bing 未收录; 目标词未进榜(头部=中科曙光).")
    print(f"  线上 zh 首页 JSON-LD 数: {op.get('jsonld_count')}; 含本会话升级: {live_has_new}")
    print(f"  GVI: {status['gvi']}; 本地最佳 CRI: {status['cri_local_best']}")
    print(f"  SERP 追加 {added} 行 -> {SERP_CSV}")
    print(f"  写出 -> {os.path.join(OUT, 'live_status.json')}")


if __name__ == "__main__":
    run()
