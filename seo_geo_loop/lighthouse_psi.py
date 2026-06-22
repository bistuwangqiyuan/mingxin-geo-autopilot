# -*- coding: utf-8 -*-
"""中科存储官网 · 线上真实性能/质量测量（PSI 优先，Playwright/CDP 兜底）。

诚实纪律：
  - 首选 Google PageSpeed Insights v5（真实 Lighthouse 评分 + Core Web Vitals）。
    无 API key 时共享 IP 常被限流(429)；可用 --key / 环境变量 PSI_API_KEY 提升配额。
  - PSI 不可达时，回退用本地 Playwright(Chromium) 对**线上页面**做实验室测量：
    真实导航计时、FCP、LCP、资源数与传输字节，并对线上 HTML 做与 readiness 同口径的
    在线技术 SEO 核对。所有结果标注 method（psi / lab）与采集时间，绝不臆造分数。

复现：python lighthouse_psi.py                       # 默认测 zh 首页（PSI→lab）
      python lighthouse_psi.py --key <PSI_API_KEY>
      python lighthouse_psi.py --force-lab           # 直接走本地实验室测量
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "outputs")

DEFAULT_URLS = [
    "https://goni.top/zh/index.html",
    "https://goni.top/zh/product.html",
    "https://goni.top/en/index.html",
]


def psi_measure(url, key=None, strategy="mobile", retries=3):
    api = ("https://www.googleapis.com/pagespeedonline/v5/runPagespeed?"
           f"url={urllib.parse.quote(url, safe='')}"
           "&category=performance&category=seo&category=accessibility&category=best-practices"
           f"&strategy={strategy}")
    if key:
        api += f"&key={key}"
    req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0 (ZK-Storage SEO audit)"})
    last = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                d = json.load(r)
            lr = d["lighthouseResult"]
            cats = {k: round(v["score"] * 100) if v.get("score") is not None else None
                    for k, v in lr["categories"].items()}
            audits = lr.get("audits", {})

            def metric(mid):
                a = audits.get(mid, {})
                return {"value": a.get("numericValue"), "display": a.get("displayValue")}

            return {"method": "psi", "ok": True, "url": url, "strategy": strategy,
                    "categories": cats,
                    "cwv": {"LCP": metric("largest-contentful-paint"),
                            "CLS": metric("cumulative-layout-shift"),
                            "TBT": metric("total-blocking-time"),
                            "FCP": metric("first-contentful-paint"),
                            "SI": metric("speed-index")},
                    "collected_at": dt.datetime.now().isoformat(timespec="seconds")}
        except Exception as e:  # noqa: BLE001
            last = str(e)
            time.sleep(10 + i * 8)
    return {"method": "psi", "ok": False, "url": url, "error": last}


_LAB_JS = """
() => {
  const nav = performance.getEntriesByType('navigation')[0] || {};
  const paints = performance.getEntriesByType('paint');
  const fcp = (paints.find(p => p.name === 'first-contentful-paint') || {}).startTime || null;
  const res = performance.getEntriesByType('resource');
  let bytes = (nav.transferSize || 0);
  for (const r of res) bytes += (r.transferSize || 0);
  return {
    ttfb: nav.responseStart || null,
    domContentLoaded: nav.domContentLoadedEventEnd || null,
    load: nav.loadEventEnd || null,
    fcp: fcp,
    lcp: window.__lcp || null,
    cls: window.__cls || 0,
    resourceCount: res.length + 1,
    transferBytes: Math.round(bytes)
  };
}
"""

_OBSERVER_INIT = """
window.__lcp = null; window.__cls = 0;
try {
  new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__lcp = e.startTime; })
    .observe({type:'largest-contentful-paint', buffered:true});
  new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; })
    .observe({type:'layout-shift', buffered:true});
} catch(e) {}
"""


def lab_measure(url):
    from playwright.sync_api import sync_playwright
    out = {"method": "lab", "ok": False, "url": url,
           "collected_at": dt.datetime.now().isoformat(timespec="seconds")}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844},
                                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                                           "AppleWebKit/605.1.15 Mobile/15E148")
        page.add_init_script(_OBSERVER_INIT)
        try:
            page.goto(url, wait_until="load", timeout=60000)
            page.wait_for_timeout(2500)
            m = page.evaluate(_LAB_JS)
            html = page.content()
            out.update({"ok": True, "metrics": m, "html_len": len(html),
                        "onpage": _onpage_audit(html)})
        except Exception as e:  # noqa: BLE001
            out["error"] = str(e)
        finally:
            browser.close()
    return out


def _onpage_audit(html):
    import re
    def has(p):
        return bool(re.search(p, html, re.I | re.S))
    jsonld = re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I)
    types = []
    for raw in jsonld:
        try:
            o = json.loads(raw)
            for it in (o if isinstance(o, list) else [o]):
                t = it.get("@type") if isinstance(it, dict) else None
                if isinstance(t, str):
                    types.append(t)
        except Exception:
            pass
    return {
        "title": has(r"<title>.+?</title>"),
        "meta_description": has(r'<meta\s+name="description"'),
        "canonical": has(r'rel="canonical"'),
        "h1": len(re.findall(r"<h1\b", html, re.I)),
        "hreflang": len(re.findall(r'rel="alternate"\s+hreflang', html, re.I)),
        "og": has(r'property="og:'),
        "jsonld_types": sorted(set(types)),
        "viewport": has(r'name="viewport"'),
    }


def measure(url, key=None, force_lab=False):
    if not force_lab:
        r = psi_measure(url, key=key)
        if r.get("ok"):
            return r
        lab = lab_measure(url)
        lab["psi_error"] = r.get("error")
        return lab
    return lab_measure(url)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls", nargs="*", default=DEFAULT_URLS)
    ap.add_argument("--key", default=os.environ.get("PSI_API_KEY"))
    ap.add_argument("--force-lab", action="store_true")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    results = [measure(u, key=args.key, force_lab=args.force_lab) for u in args.urls]
    payload = {"computed_at": dt.datetime.now().isoformat(timespec="seconds"),
               "results": results}
    with open(os.path.join(OUT, "lighthouse.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    for r in results:
        if r["method"] == "psi" and r.get("ok"):
            print(f"[psi ] {r['url']} {r['categories']}")
        elif r.get("ok"):
            m = r["metrics"]
            print(f"[lab ] {r['url']} LCP={m.get('lcp')}ms FCP={m.get('fcp')}ms "
                  f"load={m.get('load')}ms bytes={m.get('transferBytes')} types={r['onpage']['jsonld_types']}")
        else:
            print(f"[FAIL] {r['url']} {r.get('error') or r.get('psi_error')}")
    print("写出：", os.path.join(OUT, "lighthouse.json"))


if __name__ == "__main__":
    main()
