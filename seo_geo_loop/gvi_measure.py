# -*- coding: utf-8 -*-
"""铭信 GEO 可见性指数(GVI) · 真实重测与诚实对照（复用 geo_plan 真测/打分管线）。

品牌/竞品别名词表统一取自 geo_plan/geo_config.py（BRAND_ALIASES/COMPETITORS，
铭信/Mingxin/FX 系列及历史称谓），打分由 geo_scoring 同口径完成；本脚本不改测量协议。

设计（实事求是）：
  - 起点 gvi_start：直接复用 geo_plan/outputs/geo_baseline.json —— 那是此前对 4 个
    DashScope 模型 × 全部查询的真实 API 采样(280 条, grade A)，是真实的历史测量。
  - 终点 gvi_end：站内全部就绪后，用 bl 对同样的 4 个模型 × 同一查询集**重新真实采样**，
    原始回答落盘到 seo_geo_loop/outputs/gvi_end/raw/，再用 geo_scoring 同口径打分。
  - 二者诚实对照：站内改动不改变模型训练语料，故预期 gvi_end 与 gvi_start 在采样噪声内，
    这恰恰证明"真实 GVI 阶跃需站外信源随时间积累"，本脚本绝不粉饰、不臆造。

复现：python gvi_measure.py                 # 4 模型 × 全部查询（真实 API，较慢）
      python gvi_measure.py --limit 8       # 每模型前 8 条查询（快速验证管线）
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
GEO = os.path.join(os.path.dirname(BASE), "geo_plan")
OUT = os.path.join(BASE, "outputs")
END_RAW = os.path.join(OUT, "gvi_end", "raw")

sys.path.insert(0, GEO)
import geo_config as C          # noqa: E402
import geo_audit as GA          # noqa: E402
import geo_scoring as GS        # noqa: E402

# 与基线一致的 4 个可真测模型（不含 qwen3.6-plus，保持口径可比）。
BASELINE_MODELS = ["qwen-max", "qwen-plus", "deepseek-v3", "deepseek-r1"]


def _load_start():
    p = os.path.join(GEO, "outputs", "geo_baseline.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _collect_end(models, limit, workers, max_tokens, force):
    queries = GA.load_queries()["queries"]
    if limit:
        queries = queries[:limit]
    mdefs = [m for m in C.MODELS_API if m["key"] in models]
    tasks = [(m, q) for m in mdefs for q in queries]
    os.makedirs(END_RAW, exist_ok=True)
    print(f"[gvi_end] 真实采样任务：{len(tasks)}（{len(mdefs)} 模型 × {len(queries)} 查询）")

    def one(m, q):
        mdir = os.path.join(END_RAW, m["key"])
        os.makedirs(mdir, exist_ok=True)
        fp = os.path.join(mdir, f"{q['id']}.json")
        if os.path.exists(fp) and not force:
            with open(fp, "r", encoding="utf-8") as f:
                return json.load(f)
        ok, text, _raw, meta = GA.call_model(m["model"], q["text"], max_tokens=max_tokens)
        rec = {"query_id": q["id"], "tier": q["tier"], "persona": q["persona"],
               "intent": q["intent"], "lang": q["lang"], "query": q["text"],
               "model_key": m["key"], "vendor": m["vendor"], "model_id": m["model"],
               "grade": "A", "ok": ok, "response": text, "meta": meta,
               "collected_at": dt.datetime.now().isoformat(timespec="seconds")}
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
        return rec

    recs, done = [], 0
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(one, m, q) for m, q in tasks]
        for fut in cf.as_completed(futs):
            recs.append(fut.result())
            done += 1
            if done % 20 == 0:
                print(f"  [{done}/{len(tasks)}] ...")
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=BASELINE_MODELS)
    ap.add_argument("--limit", type=int, default=0, help="每模型前 N 条查询（0=全部）")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=600)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    start = _load_start()
    recs_end = _collect_end(args.models, args.limit, args.workers, args.max_tokens, args.force)
    agg_end = GS.aggregate(recs_end)
    agg_end.pop("scored", None)

    s_ov, e_ov = start["overall"], agg_end["overall"]
    compare = {
        "computed_at": dt.datetime.now().isoformat(timespec="seconds"),
        "method": "GVI = 100·(0.30·mention + 0.25·first_rank + 0.20·SoV + 0.15·citation + 0.10·accuracy)；"
                  "geo_scoring 同口径；4 模型 × 查询集真实 API 采样(grade A)。",
        "models": args.models,
        "honest_note": ("站内 CRI 优化不改变模型训练语料，故 gvi_end 与 gvi_start 预期落在采样噪声内；"
                        "真实 GVI 阶跃需站外多信源随时间被收录/引用（见 geo_plan 预测 P10/P50/P90 与站外内容包）。"),
        "start": {"source": "geo_plan/outputs/geo_baseline.json",
                  "n_records_ok": s_ov["n_records_ok"], "gvi": s_ov["gvi"],
                  "mention_rate": s_ov["mention_rate"], "first_rank": s_ov["first_rank"],
                  "share_of_voice": s_ov["share_of_voice"], "citation_rate": s_ov["citation_rate"],
                  "by_model": {m: v["gvi"] for m, v in start["by_model"].items()}},
        "end": {"source": "seo_geo_loop/outputs/gvi_end/raw/**（本次真实重测）",
                "n_records_ok": e_ov["n_records_ok"], "gvi": e_ov["gvi"],
                "mention_rate": e_ov["mention_rate"], "first_rank": e_ov["first_rank"],
                "share_of_voice": e_ov["share_of_voice"], "citation_rate": e_ov["citation_rate"],
                "by_model": {m: v["gvi"] for m, v in agg_end["by_model"].items()}},
        "delta_gvi": round(e_ov["gvi"] - s_ov["gvi"], 2),
        "delta_mention_rate": round(e_ov["mention_rate"] - s_ov["mention_rate"], 4),
    }
    with open(os.path.join(OUT, "gvi_compare.json"), "w", encoding="utf-8") as f:
        json.dump(compare, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUT, "gvi_end_aggregate.json"), "w", encoding="utf-8") as f:
        json.dump(agg_end, f, ensure_ascii=False, indent=2)
    print("-" * 60)
    print(f"gvi_start={compare['start']['gvi']}  (n={compare['start']['n_records_ok']})")
    print(f"gvi_end  ={compare['end']['gvi']}  (n={compare['end']['n_records_ok']})  "
          f"Δ={compare['delta_gvi']:+.2f}")
    print(f"写出：{os.path.join(OUT, 'gvi_compare.json')}")


if __name__ == "__main__":
    main()
