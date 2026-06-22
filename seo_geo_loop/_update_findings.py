# -*- coding: utf-8 -*-
import json, time

p = "outputs/gsc_request_index_browser.json"
d = json.load(open(p, encoding="utf-8"))
d["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
d["quota_blocked"] = 1
d["quota_note"] = (
    "Google Request Indexing daily quota is ACCOUNT-LEVEL, not per-property. "
    "Exhausted today after goni.top (yesterday) + emoney.pw + aamerica.icu. "
    "No further request-index possible until the quota resets (~24h)."
)
d["request_attempts_today"] = {
    "emoney.pw": "REJECTED - live test could not fetch (site unreachable, SSL EOF)",
    "aamerica.icu": "QUOTA_EXCEEDED dialog - and it is already indexed anyway",
}
d["index_status_audit"] = {
    "method": "URL Inspection read-only (no quota consumed)",
    "sampled": ["aamerica.icu", "ab2b.icu", "abest.icu", "abot.pw", "acash.icu", "acomputers.icu"],
    "result": "6/6 already INDEXED (网址已收录到 Google)",
    "conclusion": "Live domains are already indexed by Google natural crawl; manual request-indexing is largely unnecessary.",
}
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("updated", p)
