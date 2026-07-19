# -*- coding: utf-8 -*-
"""铭信 GEO · 评分与合成层。

读取 outputs/measurements_raw.json，计算：
- 每引擎 × {总体/窄类目/宽类目} 的：被提及率、被推荐率、排名得分、引用率、
  声量份额(SoV)，合成 0–100 的 GEO 指数（权重见 geo_data.SCORING_WEIGHTS）。
- GEO 指数 bootstrap 90% 置信区间（对记录重采样）。
- 竞品声量份额表（铭信 vs 竞品）。
- 杠杆就绪度（自审清单）、分阶段目标（T0 由实测窄/宽 GEO 指数填入）。

输出：outputs/geo_results.json。绝不为‘待密钥’引擎编造任何分数。

复现：python scoring.py
"""
from __future__ import annotations

import json
import os

import numpy as np

import geo_data as G

RAW_PATH = os.path.join(G.OUT_DIR, "measurements_raw.json")
OUT_PATH = os.path.join(G.OUT_DIR, "geo_results.json")

W = G.SCORING_WEIGHTS
RANK_CAP = G.RANK_CAP


def _rank_to_score(rank):
    if rank is None:
        return 0.0
    return max(0.0, 1.0 - (rank - 1) / RANK_CAP)


def _metrics(records):
    """对一组 ok 记录计算各项指标（不含 GEO 指数合成）。"""
    recs = [r for r in records if r.get("ok")]
    n = len(recs)
    if n == 0:
        return None
    mention = [1 if r["self_mention"] else 0 for r in recs]
    mention_rate = float(np.mean(mention))

    rec_recs = [r for r in recs if r.get("recommended") is not None]
    recommendation_rate = (float(np.mean([1 if r["recommended"] else 0 for r in rec_recs]))
                           if rec_recs else 0.0)

    rank_scores = [_rank_to_score(r.get("rank")) for r in recs]
    rank_score = float(np.mean(rank_scores))

    citation_rate = float(np.mean([1 if r.get("cited") else 0 for r in recs]))

    self_mentions = sum(mention)
    comp_mentions = sum(r.get("n_competitors_mentioned", 0) for r in recs)
    denom = self_mentions + comp_mentions
    sov = (self_mentions / denom) if denom > 0 else 0.0

    return {
        "n": n,
        "mention_rate": round(mention_rate, 4),
        "recommendation_rate": round(recommendation_rate, 4),
        "rank_score": round(rank_score, 4),
        "citation_rate": round(citation_rate, 4),
        "sov": round(sov, 4),
        "self_mentions": self_mentions,
        "competitor_mentions": comp_mentions,
        "n_recommendation_queries": len(rec_recs),
    }


def _geo_index_from_metrics(m):
    if m is None:
        return 0.0
    val = (W["mention_rate"] * m["mention_rate"]
           + W["recommendation_rate"] * m["recommendation_rate"]
           + W["sov"] * m["sov"]
           + W["rank_score"] * m["rank_score"]
           + W["citation_rate"] * m["citation_rate"])
    return round(100.0 * val, 2)


def _geo_index_records(records):
    return _geo_index_from_metrics(_metrics(records))


def _bootstrap_ci(records, B=2000, seed=20260621):
    recs = [r for r in records if r.get("ok")]
    if len(recs) < 2:
        gi = _geo_index_records(recs)
        return [gi, gi]
    rng = np.random.default_rng(seed)
    idx = np.arange(len(recs))
    vals = []
    for _ in range(B):
        sample = [recs[i] for i in rng.choice(idx, size=len(recs), replace=True)]
        vals.append(_geo_index_records(sample))
    lo, hi = np.percentile(vals, [5, 95])
    return [round(float(lo), 2), round(float(hi), 2)]


def _funnel(records):
    """转化漏斗计数：回答数 → 被提及 → 被推荐 → 排名第一。"""
    recs = [r for r in records if r.get("ok")]
    responses = len(recs)
    mentioned = sum(1 for r in recs if r.get("self_mention"))
    recommended = sum(1 for r in recs if r.get("recommended"))
    top1 = sum(1 for r in recs if r.get("rank") == 1)
    return {"responses": responses, "mentioned": mentioned,
            "recommended": recommended, "ranked_top1": top1}


def _competitor_sov(records):
    """竞品声量份额：各厂商被提及次数 / 全部厂商被提及次数（含铭信）。"""
    recs = [r for r in records if r.get("ok")]
    counts = {"__self__": 0}
    for k in G.COMPETITORS:
        counts[k] = 0
    for r in recs:
        if r.get("self_mention"):
            counts["__self__"] += 1
        for k in r.get("competitor_hits", {}):
            counts[k] = counts.get(k, 0) + 1
    total = sum(counts.values())
    rows = []
    label_map = {"__self__": f"{G.BRAND_ZH}（自家）"}
    for k, c in G.COMPETITORS.items():
        label_map[k] = c["name_zh"]
    for k, c in sorted(counts.items(), key=lambda x: -x[1]):
        rows.append({
            "key": k, "label": label_map.get(k, k), "mentions": c,
            "sov": round(c / total, 4) if total > 0 else 0.0,
            "is_self": k == "__self__",
        })
    return {"total_mentions": total, "rows": rows}


def compute():
    with open(RAW_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    records = raw["records"]
    meta = raw["meta"]

    # 区分对话引擎与检索探针（以实测数据中实际出现的引擎为准，兼容任意 provider 组合）
    measured = {r["engine"] for r in records}
    chat_keys = [e["key"] for e in G.ENGINES
                 if e["key"] in measured and e["adapter"] != "bl_search"]
    search_keys = [e["key"] for e in G.ENGINES
                   if e["key"] in measured and e["adapter"] == "bl_search"]
    engine_label = {e["key"]: e["label"] for e in G.ENGINES}

    per_engine = {}
    for ek in chat_keys + search_keys:
        erecs = [r for r in records if r["engine"] == ek]
        ok_erecs = [r for r in erecs if r.get("ok")]
        status = meta.get("engine_status", {}).get(ek, "ok")
        if not ok_erecs:
            per_engine[ek] = {"label": engine_label.get(ek, ek),
                              "available": False, "status": status}
            continue
        block = {"label": engine_label.get(ek, ek), "available": True, "status": status}
        for cat in ("overall", "narrow", "broad"):
            sub = ok_erecs if cat == "overall" else [r for r in ok_erecs if r["category"] == cat]
            m = _metrics(sub)
            block[cat] = {
                "metrics": m,
                "geo_index": _geo_index_records(sub),
                "ci90": _bootstrap_ci(sub),
                "funnel": _funnel(sub),
            }
        block["competitor_sov"] = _competitor_sov(ok_erecs)
        per_engine[ek] = block

    # 对话引擎聚合（用于‘各 AI 大模型’总体 GEO 指数）
    chat_records = [r for r in records if r["engine"] in chat_keys and r.get("ok")]
    aggregate = {}
    for cat in ("overall", "narrow", "broad"):
        sub = chat_records if cat == "overall" else [r for r in chat_records if r["category"] == cat]
        m = _metrics(sub)
        aggregate[cat] = {
            "metrics": m,
            "geo_index": _geo_index_records(sub),
            "ci90": _bootstrap_ci(sub),
            "funnel": _funnel(sub),
            "competitor_sov": _competitor_sov(sub),
        }
    aggregate["competitor_sov"] = _competitor_sov(chat_records)

    # 分阶段目标：T0 用实测窄/宽 GEO 指数填入
    stages = dict(G.STAGE_TARGETS)
    narrow_t0 = aggregate["narrow"]["geo_index"]
    broad_t0 = aggregate["broad"]["geo_index"]
    narrow_targets = list(stages["narrow"]); narrow_targets[0] = narrow_t0
    broad_targets = list(stages["broad"]); broad_targets[0] = broad_t0

    results = {
        "meta": {
            "run_at": meta.get("run_at"),
            "survey_date": meta.get("survey_date"),
            "repeats": meta.get("repeats"),
            "n_queries": meta.get("n_queries"),
            "weights": W,
            "rank_cap": RANK_CAP,
            "chat_engines": chat_keys,
            "search_engines": search_keys,
            "engine_status": meta.get("engine_status", {}),
            "pending_engines": meta.get("pending_engines", []),
        },
        "brand": {"zh": G.BRAND_ZH, "en": G.BRAND_EN, "entity": G.ENTITY_ZH,
                  "model": G.PRODUCT_MODEL},
        "facts": G.ground_truth_facts(),
        "categories": G.CATEGORIES,
        "per_engine": per_engine,
        "aggregate": aggregate,
        "lever_scores": G.lever_scores(),
        "levers": G.LEVERS,
        "stage_targets": {
            "stages": stages["stages"],
            "narrow": narrow_targets,
            "broad": broad_targets,
            "milestones": stages["milestones"],
        },
        "query_basket": G.QUERY_BASKET,
        # 落盘时冻结可达性快照（reachable_now），供报告构建器展示
        "engines": [dict(e, reachable_now=G._engine_reachable(e)) for e in G.ENGINES],
        "competitors": G.COMPETITORS,
        "sources": G.SOURCES,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved: {OUT_PATH}")
    print(f"  Aggregate GEO Index — narrow={aggregate['narrow']['geo_index']} "
          f"(CI {aggregate['narrow']['ci90']}), broad={aggregate['broad']['geo_index']} "
          f"(CI {aggregate['broad']['ci90']})")
    for ek in chat_keys + search_keys:
        b = per_engine.get(ek, {})
        if b.get("available"):
            print(f"  [{b['label']}] overall GEO={b['overall']['geo_index']} "
                  f"mention={b['overall']['metrics']['mention_rate']}")
        else:
            print(f"  [{b.get('label', ek)}] 不可用/无数据（status={b.get('status')}）")
    return results


if __name__ == "__main__":
    compute()
