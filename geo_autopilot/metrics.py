# -*- coding: utf-8 -*-
"""中科存储 GEO Autopilot · 当日指标采集与历史快照（单一事实源，可复现）。

从引擎产物(geo_baseline/gvi_compare/source_gap/live_status/offsite_published)
汇总当日 KPI，落盘到 history/snapshot_YYYYMMDD.json，供趋势、报告、告警共用。
绝不臆造：缺失项记为 None 并在 sources 中标注来源缺失。
"""
from __future__ import annotations

import datetime as dt
import json
import os

import paths


def _load(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def collect_snapshot(extra=None):
    """汇总当日指标快照（不写盘）。"""
    baseline = _load(paths.GEO_BASELINE)
    gvi = _load(paths.GVI_COMPARE)
    gap = _load(paths.SOURCE_GAP)
    live = _load(paths.LIVE_STATUS)
    pub = _load(paths.OFFSITE_PUBLISHED)

    ov = baseline.get("overall", {})
    by_intent = baseline.get("by_intent", {})
    opp = baseline.get("opportunity_gap", {})

    # GVI：优先用最近真实重测 end，否则用基线
    gvi_now = None
    gvi_source = None
    if gvi.get("end", {}).get("gvi") is not None:
        gvi_now = gvi["end"]["gvi"]
        gvi_source = "gvi_compare.end(real_remeasure)"
    elif ov.get("gvi") is not None:
        gvi_now = ov["gvi"]
        gvi_source = "geo_baseline.overall"

    def _cov(vendor):
        return gap.get("by_model", {}).get(vendor, {}).get("weighted_coverage")

    # 线上收录页数（GSC 实测，如有）
    indexed = None
    onpage = live.get("onpage")
    if isinstance(onpage, list):
        indexed = sum(1 for p in onpage if p.get("google_indexed") is True)

    channels_live = [
        ch.get("url") for ch in pub.get("channels", [])
        if ch.get("verified_http_200")
    ]

    snap = {
        "date": dt.date.today().isoformat(),
        "ts": dt.datetime.now().isoformat(timespec="seconds"),
        "gvi": gvi_now,
        "gvi_source": gvi_source,
        "gvi_delta": gvi.get("delta_gvi"),
        "mention_rate": ov.get("mention_rate"),
        "first_rank": ov.get("first_rank"),
        "share_of_voice": ov.get("share_of_voice"),
        "citation_rate": ov.get("citation_rate"),
        "n_records_ok": ov.get("n_records_ok"),
        "recommendation_mention": (by_intent.get("recommendation", {}) or {}).get("mention_rate"),
        "opportunity_gap_total": opp.get("total"),
        "coverage": {
            "DeepSeek": _cov("DeepSeek"),
            "通义千问": _cov("通义千问"),
            "文心一言": _cov("文心一言"),
        },
        "google_indexed_pages": indexed,
        "offsite_channels_live": channels_live,
        "best_cri": live.get("best_cri") or live.get("cri"),
        "sources": {
            "geo_baseline": os.path.isfile(paths.GEO_BASELINE),
            "gvi_compare": os.path.isfile(paths.GVI_COMPARE),
            "source_gap": os.path.isfile(paths.SOURCE_GAP),
            "live_status": os.path.isfile(paths.LIVE_STATUS),
        },
    }
    if extra:
        snap.update(extra)
    return snap


def write_snapshot(snap=None):
    paths.ensure_dirs()
    snap = snap or collect_snapshot()
    fp = os.path.join(paths.HISTORY, f"snapshot_{snap['date']}.json")
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)
    # latest 指针
    with open(os.path.join(paths.HISTORY, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)
    return fp, snap


def load_history():
    """按日期升序加载所有快照。"""
    out = []
    if not os.path.isdir(paths.HISTORY):
        return out
    for fn in sorted(os.listdir(paths.HISTORY)):
        if fn.startswith("snapshot_") and fn.endswith(".json"):
            d = _load(os.path.join(paths.HISTORY, fn))
            if d:
                out.append(d)
    return out


if __name__ == "__main__":
    fp, snap = write_snapshot()
    print(f"snapshot -> {fp}")
    print(json.dumps(snap, ensure_ascii=False, indent=2))
