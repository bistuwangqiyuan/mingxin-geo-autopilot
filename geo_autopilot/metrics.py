# -*- coding: utf-8 -*-
"""铭信 GEO Autopilot · 当日指标采集与历史快照（单一事实源，可复现）。

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


def answerable_coverage():
    """统计站内 answer-first 单元数（诚实的"可被回答"覆盖度）。

    铭信站为 Next.js（amd 仓库 site/ 子目录），无本地静态 HTML 可数：
    口径改为统计内容自进化的落地文件 outputs/autopilot_faq.json 中的
    FAQ/术语条目数（按 lang 分中英）。文件不存在时如实记 0，绝不臆造。
    这是真正由站内内容自进化驱动、可逐日累计且可现场核验的指标，
    不同于 GVI(站外语料/时间驱动) 与 CRI(站内就绪度，已收敛)。

    2026-08-08：文件从官网仓移到本仓 outputs/。口径未变（同一份内容、同一种计数），
    变的只是它存在哪儿——本仓的副本随每次运行提交，比过去那份从未被 clone 成功、
    因而恒为 0 的官网仓路径可核验得多。
    """
    p = paths.AUTOPILOT_FAQ
    exists = os.path.isfile(p)
    faq_zh = faq_en = gl_zh = gl_en = 0
    if exists:
        doc = _load(p)
        for x in doc.get("faq", []) or []:
            if x.get("lang") == "en":
                faq_en += 1
            else:
                faq_zh += 1
        for x in doc.get("glossary", []) or []:
            if x.get("lang") == "en":
                gl_en += 1
            else:
                gl_zh += 1
    return {
        "faq_zh": faq_zh, "faq_en": faq_en,
        "glossary_zh": gl_zh, "glossary_en": gl_en,
        "total": faq_zh + faq_en + gl_zh + gl_en,
        "file_present": exists,
        "source": "geo_autopilot/outputs/autopilot_faq.json（上线副本在站点库 autopilot_faq 表）",
    }


def keyword_bank_stats():
    """热词台账统计（四步法第 1 步产物；缺失记 None，不臆造）。"""
    bank = _load(os.path.join(paths.HISTORY, "keyword_bank.json"))
    kws = bank.get("keywords")
    if not isinstance(kws, list):
        return {"total": None, "done": None, "pending": None}
    done = sum(1 for k in kws if k.get("status") == "done")
    return {"total": len(kws), "done": done, "pending": len(kws) - done}


def geo_referral_signals():
    """GA4 流量信号（四步法第 4 步产物；未配置/未运行如实标注）。"""
    doc = _load(os.path.join(paths.OUTPUTS, "traffic_signals.json"))
    if not doc:
        return {"status": "not_run"}
    return {"status": doc.get("status"),
            "reddit_referral": doc.get("reddit_referral"),
            "ai_engine_sources": doc.get("ai_engine_sources"),
            "geo_signal_present": doc.get("geo_signal_present")}


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

    # GVI：优先用最近真实重测 end，否则用基线。
    # 质量闸门：小样本重测（如 --gvi-limit 控成本时 n 仅为个位数）噪声极大、
    # 会产出 0.0 之类的假信号污染趋势与告警——样本不足时如实回退基线并标注。
    gvi_now = None
    gvi_source = None
    end = gvi.get("end") or {}
    start_n = (gvi.get("start") or {}).get("n_records_ok") or 0
    end_n = end.get("n_records_ok") or 0
    min_n = max(30, int(start_n * 0.5)) if start_n else 30
    if end.get("gvi") is not None and end_n >= min_n:
        gvi_now = end["gvi"]
        gvi_source = f"gvi_compare.end(real_remeasure, n={end_n})"
    elif ov.get("gvi") is not None:
        gvi_now = ov["gvi"]
        gvi_source = ("geo_baseline.overall"
                      + (f"(重测样本不足 n={end_n}<{min_n}，已忽略)" if end.get("gvi") is not None else ""))

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
        # 小样本重测的 delta 同样是噪声，不足额时记 None（告警/日报只看可信 delta）
        "gvi_delta": gvi.get("delta_gvi") if end_n >= min_n else None,
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
        "answerable_coverage": answerable_coverage(),
        "keyword_bank": keyword_bank_stats(),
        "geo_referral_signals": geo_referral_signals(),
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
