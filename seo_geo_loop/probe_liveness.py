#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe real HTTP status / indexability of all GSC domain properties.

Reads outputs/gsc_properties.json, fetches https://<domain>/ for each domain
(concurrently), and classifies whether the homepage is actually serving an
indexable page. Writes outputs/site_liveness.json.

Pure standard library. No external deps.
"""
import json
import os
import re
import ssl
import socket
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
PROPS = os.path.join(HERE, "outputs", "gsc_properties.json")
OUT = os.path.join(HERE, "outputs", "site_liveness.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 12
WORKERS = 24

_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE


def fetch(domain):
    res = {
        "domain": domain,
        "url": f"https://{domain}/",
        "status": None,
        "final_url": None,
        "redirected": False,
        "bytes": 0,
        "title": None,
        "has_noindex": False,
        "server": None,
        "error": None,
        "klass": None,
        "elapsed_ms": None,
    }
    t0 = time.time()
    url = f"https://{domain}/"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=_ctx) as r:
            res["status"] = r.status
            res["final_url"] = r.geturl()
            res["redirected"] = (r.geturl().rstrip("/") != url.rstrip("/"))
            res["server"] = r.headers.get("Server")
            raw = r.read(200000)
            res["bytes"] = len(raw)
            try:
                html = raw.decode("utf-8", "ignore")
            except Exception:
                html = ""
            m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
            if m:
                res["title"] = re.sub(r"\s+", " ", m.group(1)).strip()[:160]
            if re.search(r'<meta[^>]+name=["\']robots["\'][^>]+noindex', html, re.I):
                res["has_noindex"] = True
    except urllib.error.HTTPError as e:
        res["status"] = e.code
        res["final_url"] = e.url if hasattr(e, "url") else url
        res["error"] = f"HTTP {e.code}"
    except urllib.error.URLError as e:
        res["error"] = f"URLError: {e.reason}"
    except socket.timeout:
        res["error"] = "timeout"
    except Exception as e:
        res["error"] = f"{type(e).__name__}: {e}"
    res["elapsed_ms"] = int((time.time() - t0) * 1000)

    # classify
    st = res["status"]
    if st == 200 and not res["has_noindex"] and res["bytes"] > 500:
        # check for offsite/parking redirect
        fu = (res["final_url"] or "").lower()
        if res["redirected"] and domain not in fu:
            res["klass"] = "redirect_offsite"
        else:
            res["klass"] = "live_indexable"
    elif st == 200 and res["has_noindex"]:
        res["klass"] = "live_noindex"
    elif st == 200:
        res["klass"] = "live_thin"
    elif st in (301, 302, 303, 307, 308):
        res["klass"] = "redirect"
    elif st in (401, 403):
        res["klass"] = "blocked"
    elif st == 404:
        res["klass"] = "not_found"
    elif st and 500 <= st < 600:
        res["klass"] = "server_error"
    elif res["error"]:
        res["klass"] = "unreachable"
    else:
        res["klass"] = "unknown"
    return res


def main():
    with open(PROPS, encoding="utf-8") as f:
        props = json.load(f)
    domains = props["domains"]
    print(f"Probing {len(domains)} domains with {WORKERS} workers...")
    results = []
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fetch, d): d for d in domains}
        for fut in as_completed(futs):
            results.append(fut.result())
            done += 1
            if done % 25 == 0:
                print(f"  ...{done}/{len(domains)}")
    results.sort(key=lambda r: r["domain"])

    summary = {}
    for r in results:
        summary[r["klass"]] = summary.get(r["klass"], 0) + 1

    out = {
        "probed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "total": len(results),
        "timeout_s": TIMEOUT,
        "summary": dict(sorted(summary.items(), key=lambda x: -x[1])),
        "live_indexable_domains": sorted(r["domain"] for r in results if r["klass"] == "live_indexable"),
        "results": results,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\n=== SUMMARY ===")
    for k, v in out["summary"].items():
        print(f"  {k}: {v}")
    print(f"\nlive_indexable: {len(out['live_indexable_domains'])}")
    print(f"written: {OUT}")


if __name__ == "__main__":
    main()
