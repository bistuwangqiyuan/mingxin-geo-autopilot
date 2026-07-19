"""Honest IndexNow + sitemap submission for mingxinstorage.xyz.

Strategy (in order):
  1) Preferred: call the site's own POST /api/seo/ping (Bearer CRON_SECRET).
     The Next.js site holds its INDEXNOW_KEY server-side and fans out to
     IndexNow + Baidu push + WebSub in one call. Requires env CRON_SECRET.
  2) Fallback: direct IndexNow consortium submit, only if env MX_INDEXNOW_KEY
     is provided AND the key file is verifiably live at the site root.

- Parses the LIVE sitemap.xml to obtain the canonical URL list (single source of truth).
- Writes outputs/indexnow_submit.json with timestamps, payloads and raw responses.

Honesty: we only claim what the endpoints actually return. Google has no public
ping/submit without Search Console; we record that truthfully and do not fake success.
"""
from __future__ import annotations

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

HOST = os.environ.get("MX_SITE_HOST", "mingxinstorage.xyz")
SITE = f"https://{HOST}"
SITEMAP = f"{SITE}/sitemap.xml"
SEO_PING = f"{SITE}/api/seo/ping"
CRON_SECRET = os.environ.get("CRON_SECRET", "")

# Direct-submit fallback: the IndexNow key belongs to the site (Vercel env INDEXNOW_KEY).
# Provide it here only if you also host {KEY}.txt at the site root.
KEY = os.environ.get("MX_INDEXNOW_KEY", "")
KEY_LOCATION = f"{SITE}/{KEY}.txt" if KEY else ""

OUT = Path(__file__).resolve().parent / "outputs" / "indexnow_submit.json"

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

_UA = f"Mozilla/5.0 (compatible; Mingxin-IndexNow/1.0; +{SITE}/)"


def _get(url: str, timeout: int = 25) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        r = urllib.request.urlopen(req, timeout=timeout, context=_CTX)
        return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")[:500]
    except Exception as e:  # noqa: BLE001
        return -1, f"{type(e).__name__}: {e}"


def _post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": _UA,
                 **(headers or {})},
    )
    t = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=timeout, context=_CTX)
        return {"status": r.status, "body": r.read().decode("utf-8", "ignore")[:1000], "elapsed": round(time.time() - t, 2)}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": e.read().decode("utf-8", "ignore")[:1000], "elapsed": round(time.time() - t, 2)}
    except Exception as e:  # noqa: BLE001
        return {"status": -1, "body": f"{type(e).__name__}: {e}", "elapsed": round(time.time() - t, 2)}


def parse_sitemap_urls(xml_text: str) -> list[str]:
    urls: list[str] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return urls
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    for loc in root.findall(".//sm:url/sm:loc", ns):
        if loc.text:
            urls.append(loc.text.strip())
    if not urls:  # namespace fallback
        for loc in root.iter():
            if loc.tag.endswith("loc") and loc.text:
                urls.append(loc.text.strip())
    return urls


def main() -> int:
    now = datetime.now(timezone.utc).astimezone()
    result: dict = {
        "host": HOST,
        "submitted_at": now.isoformat(timespec="seconds"),
    }

    # 1) get canonical URL list from live sitemap
    ss, sbody = _get(SITEMAP)
    urls = parse_sitemap_urls(sbody) if ss == 200 else []
    for extra in [f"{SITE}/", f"{SITE}/en"]:
        if extra not in urls:
            urls.append(extra)
    urls = sorted(set(urls))
    result["sitemap"] = {"status": ss, "url_count": len(urls)}
    result["url_list"] = urls

    # 2) preferred path: the site's own /api/seo/ping (site holds INDEXNOW_KEY)
    submitted = False
    if CRON_SECRET:
        resp = _post_json(SEO_PING, {"urls": urls},
                          headers={"Authorization": f"Bearer {CRON_SECRET}"})
        result["seo_ping"] = resp
        submitted = resp.get("status") == 200
    else:
        result["seo_ping"] = {"status": None,
                              "note": "CRON_SECRET 未配置，跳过站点 /api/seo/ping（首选通道）"}

    # 3) fallback: direct IndexNow consortium submit (requires our own key file live)
    if not submitted and KEY:
        ks, kbody = _get(KEY_LOCATION)
        result["key_file_check"] = {"status": ks, "matches": kbody.strip() == KEY}
        if ks == 200 and result["key_file_check"]["matches"]:
            payload = {"host": HOST, "key": KEY, "keyLocation": KEY_LOCATION, "urlList": urls}
            endpoints = {
                "indexnow.org": "https://api.indexnow.org/indexnow",
                "bing": "https://www.bing.com/indexnow",
                "yandex": "https://yandex.com/indexnow",
            }
            result["indexnow"] = {}
            for name, ep in endpoints.items():
                result["indexnow"][name] = _post_json(ep, payload)
                time.sleep(1.0)
            submitted = any(v.get("status") == 200 for v in result["indexnow"].values())
        else:
            result["indexnow_note"] = "MX_INDEXNOW_KEY 提供但 key 文件不在线/不匹配，如实跳过直连提交。"
    elif not submitted:
        result["indexnow_note"] = ("直连 IndexNow 需 MX_INDEXNOW_KEY 且站点根托管 {KEY}.txt；"
                                   "未配置则依赖站点 /api/seo/ping（其自持 INDEXNOW_KEY）。")

    # 4) honest note about Google
    result["submitted"] = submitted
    result["google_note"] = (
        "Google 无公开免认证提交/ping 接口（ping 已于 2023 弃用）。收录需 Search Console "
        "提交 sitemap 或自然抓取；此处如实记录各端点真实响应，Google 侧依赖 "
        "sitemap.xml + 自然抓取 + 站外信源积累。"
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "url_list"}, ensure_ascii=False, indent=2))
    print(f"\n[{'OK' if submitted else 'SKIP'}] {len(urls)} URLs; written {OUT}")
    return 0 if submitted or not (CRON_SECRET or KEY) else 1


if __name__ == "__main__":
    sys.exit(main())
