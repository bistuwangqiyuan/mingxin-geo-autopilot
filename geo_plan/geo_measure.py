# -*- coding: utf-8 -*-
"""中科存储 GEO · 真实测评采集层（可插拔引擎适配器）。

口径（实事求是、绝不编造）
--------------------------
- 现在可实测：经 bl(DashScope) 调用通义千问 3.6 Plus / Max 两个真实大模型，
  以及 DashScope WebSearch 联网检索可见度探针。每条查询多次重复采样。
- 需密钥后复测：ChatGPT/Claude/Gemini/Perplexity/DeepSeek/豆包/文心/Kimi/智谱/
  元宝——适配器就位，但未配置密钥时优雅跳过并标注 status='pending_key'，
  绝不产生任何编造的排名或被提及数据。

输出：outputs/measurements_raw.json（逐条原始回答 + 结构化判定 + 运行元数据）。

复现：python geo_measure.py            # 跑全部可达引擎
     python geo_measure.py --engine qwen-max
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time

import geo_data as G

RAW_PATH = os.path.join(G.OUT_DIR, "measurements_raw.json")


# ---------------------------------------------------------------------------
# bl 可执行定位（Windows 上优先 .cmd）
# ---------------------------------------------------------------------------
def _find_bl():
    for cand in ("bl.cmd", "bl.exe", "bl"):
        p = shutil.which(cand)
        if p:
            return p
    # 退回 npm 全局默认路径
    guess = os.path.expanduser(r"~\AppData\Roaming\npm\bl.cmd")
    return guess if os.path.exists(guess) else None


BL = _find_bl()


def _run_bl(args, timeout=120):
    """运行一次 bl 命令，返回 (ok, parsed_json_or_None, raw_stdout)。"""
    if not BL:
        return False, None, "bl-not-found"
    try:
        proc = subprocess.run(
            [BL] + args,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, None, "timeout"
    out = proc.stdout or ""
    # bl 的 PowerShell 包装偶有 stderr 噪声；以 stdout JSON 为准。
    start = out.find("{")
    if start < 0:
        return False, None, out[:500]
    try:
        data = json.loads(out[start:])
    except json.JSONDecodeError:
        # 尝试截到最后一个 }
        end = out.rfind("}")
        try:
            data = json.loads(out[start:end + 1])
        except Exception:
            return False, None, out[:500]
    if isinstance(data, dict) and data.get("error"):
        return False, data, json.dumps(data.get("error"), ensure_ascii=False)
    return True, data, out[:200]


# ---------------------------------------------------------------------------
# 适配器
# ---------------------------------------------------------------------------
def adapter_bl_chat(engine, query, max_tokens=1500, timeout=150):
    """通义系真实大模型对话。返回回答正文（content）。"""
    args = ["text", "chat", "--model", engine["model"],
            "--message", query["text"],
            "--max-tokens", str(max_tokens), "--output", "json"]
    ok, data, raw = _run_bl(args, timeout=timeout)
    if not ok or not data:
        return None, raw
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None, raw
    return content, None


def adapter_bl_search(engine, query, count=10, timeout=90):
    """联网检索可见度探针：把检索结果标题/摘要拼为‘可见文本’做提及判定。"""
    args = ["search", "web", "--query", query["text"], "--count", str(count),
            "--output", "json"]
    ok, data, raw = _run_bl(args, timeout=timeout)
    if not ok or not data:
        return None, raw
    # 兼容多种返回结构，抽取文本
    chunks = []
    def _walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("title", "snippet", "content", "url", "link") and isinstance(v, str):
                    chunks.append(v)
                else:
                    _walk(v)
        elif isinstance(o, list):
            for it in o:
                _walk(it)
    _walk(data)
    if not chunks:
        return None, "no-results"
    return "\n".join(chunks), None


ADAPTERS = {
    "bl_chat": adapter_bl_chat,
    "bl_search": adapter_bl_search,
}


# ---------------------------------------------------------------------------
# 采集主流程
# ---------------------------------------------------------------------------
def measure_engine(engine, repeats):
    records = []
    adapter = ADAPTERS.get(engine["adapter"])
    label = engine["label"]
    is_search = engine["adapter"] == "bl_search"
    reps = 1 if is_search else repeats  # 检索同一查询无须重复采样
    print(f"[engine] {label} ({engine['model']}) x{reps} ...", flush=True)
    fail_streak = 0
    for q in G.QUERY_BASKET:
        for r in range(reps):
            t0 = time.time()
            text, err = adapter(engine, q)
            dur = round(time.time() - t0, 1)
            if text is None:
                print(f"  ! {q['id']} rep{r} FAILED ({err}) [{dur}s]", flush=True)
                records.append({
                    "engine": engine["key"], "engine_label": label,
                    "query_id": q["id"], "category": q["category"],
                    "type": q["type"], "lang": q["lang"], "rep": r,
                    "ok": False, "error": str(err)[:200], "response": None,
                })
                fail_streak += 1
                if is_search and fail_streak >= 2:
                    print(f"  -> WebSearch 连续失败，判定服务暂不可用，停止该探针。", flush=True)
                    return records, "unavailable"
                continue
            fail_streak = 0
            det = G.detect_mentions(text, q["type"])
            print(f"  - {q['id']} rep{r}: self={det['self_mention']} "
                  f"rank={det['rank']} comp={det['n_competitors_mentioned']} [{dur}s]", flush=True)
            rec = {
                "engine": engine["key"], "engine_label": label,
                "query_id": q["id"], "category": q["category"],
                "type": q["type"], "lang": q["lang"], "rep": r,
                "ok": True, "duration_s": dur,
                "response": text,
            }
            rec.update(det)
            records.append(rec)
            _save_incremental(records, engine["key"])
    return records, "ok"


_PARTIAL = {}


def _save_incremental(records, engine_key):
    _PARTIAL[engine_key] = records
    tmp = RAW_PATH + ".partial"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_PARTIAL, f, ensure_ascii=False, indent=2)


def run(selected=None, repeats=None):
    repeats = repeats or G.REPEATS
    engines = [e for e in G.reachable_engines()
               if (selected is None or e["key"] in selected)]
    all_records = []
    engine_status = {}
    for e in engines:
        recs, status = measure_engine(e, repeats)
        all_records.extend(recs)
        engine_status[e["key"]] = status

    payload = {
        "meta": {
            "run_at": dt.datetime.now().isoformat(timespec="seconds"),
            "survey_date": G.SURVEY_DATE,
            "repeats": repeats,
            "n_queries": len(G.QUERY_BASKET),
            "bl_path": BL,
            "engine_status": engine_status,
            "reachable_engines": [e["key"] for e in G.reachable_engines()],
            "pending_engines": [{"key": e["key"], "label": e["label"],
                                 "env_key": e.get("env_key"), "note": e["note"]}
                                for e in G.pending_engines()],
        },
        "records": all_records,
    }
    with open(RAW_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    ok_n = sum(1 for r in all_records if r["ok"])
    print(f"\nSaved: {RAW_PATH}  | records={len(all_records)} ok={ok_n} "
          f"engines={list(engine_status.items())}")
    if os.path.exists(RAW_PATH + ".partial"):
        os.remove(RAW_PATH + ".partial")
    return payload


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", action="append", help="只跑指定引擎 key（可重复）")
    ap.add_argument("--repeats", type=int, default=None)
    args = ap.parse_args()
    if not BL:
        print("ERROR: 找不到 bl 可执行文件。请确认已 `npm i -g bailian-cli` 且已登录。",
              file=sys.stderr)
        sys.exit(2)
    run(selected=args.engine, repeats=args.repeats)
