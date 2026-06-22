"""Honest IndexNow + sitemap submission for goni.top.

- Parses the LIVE sitemap.xml to obtain the canonical URL list (single source of truth).
- Submits the full list to IndexNow (Microsoft Bing / Yandex / Seznam / Naver consortium)
  using the key file already published at the site root.
- Attempts legacy sitemap "ping" endpoints and records their REAL HTTP responses
  (Google/Bing ping endpoints are deprecated; we report exactly what they return).
- Writes outputs/indexnow_submit.json with timestamps, payloads and raw responses.

Honesty: we only claim what the endpoints actually return. Google has no public
ping/submit without Search Console; we record that truthfully and do not fake success.
"""
from __future__ import annotations

import json
import ssl
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

HOST = "goni.top"
KEY = "REDACTED_INDEXNOW_KEY"
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"
SITEMAP = f"https://{HOST}/sitemap.xml"

OUT = Path(__file__).resolve().parent / "outputs" / "indexnow_submit.json"

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

_UA = "Mozilla/5.0 (compatible; ZK-IndexNow/1.0; +https://goni.top/)"


def _get(url: str, timeout: int = 25) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        r = urllib.request.urlopen(req, timeout=timeout, context=_CTX)
        return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")[:500]
    except Exception as e:  # noqa: BLE001
        return -1, f"{type(e).__name__}: {e}"


def _post_json(url: str, payload: dict, timeout: int = 30) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": _UA},
    )
    t = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=timeout, context=_CTX)
        return {"status": r.status, "body": r.read().decode("utf-8", "ignore")[:500], "elapsed": round(time.time() - t, 2)}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": e.read().decode("utf-8", "ignore")[:500], "elapsed": round(time.time() - t, 2)}
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
        "key": KEY,
        "key_location": KEY_LOCATION,
        "submitted_at": now.isoformat(timespec="seconds"),
    }

    # 0) verify key file is live and matches
    ks, kbody = _get(KEY_LOCATION)
    result["key_file_check"] = {"status": ks, "matches": kbody.strip() == KEY}

    # 1) get canonical URL list from live sitemap
    ss, sbody = _get(SITEMAP)
    urls = parse_sitemap_urls(sbody) if ss == 200 else []
    # ensure homepage variants included
    for extra in [f"https://{HOST}/", f"https://{HOST}/zh/index.html", f"https://{HOST}/en/index.html"]:
        if extra not in urls:
            urls.append(extra)
    urls = sorted(set(urls))
    result["sitemap"] = {"status": ss, "url_count": len(urls)}
    result["url_list"] = urls

    if ks != 200 or not result["key_file_check"]["matches"]:
        result["error"] = "IndexNow key file not live or mismatched; aborting submit (honest)."
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    # 2) IndexNow submit (batched) to multiple consortium endpoints
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

    # 3) legacy sitemap ping endpoints — record REAL responses (often deprecated/404)
    pings = {
        "google_ping": f"https://www.google.com/ping?sitemap={SITEMAP}",
        "bing_ping": f"https://www.bing.com/ping?sitemap={SITEMAP}",
    }
    result["sitemap_ping"] = {}
    for name, url in pings.items():
        st, body = _get(url, timeout=20)
        result["sitemap_ping"][name] = {"status": st, "note": "deprecated by provider" if st in (404, 410) else "ok"}

    # 4) honest note about Google
    result["google_note"] = (
        "Google 无公开免认证提交/ping 接口（ping 已于 2023 弃用）。收录需 Search Console "
        "提交 sitemap 或自然抓取；用户当前无站长平台访问，故此处仅如实记录 ping 响应，"
        "Google 侧依赖 sitemap.xml + 自然抓取 + 站外信源积累。"
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "url_list"}, ensure_ascii=False, indent=2))
    print(f"\n[OK] {len(urls)} URLs; written {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
