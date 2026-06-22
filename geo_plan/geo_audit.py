# -*- coding: utf-8 -*-
"""中科存储 GEO 基线采集器（geo_audit.py）。

职责：对 queries.json 中的标准问法，在"可编程真测"的大模型上（经 bl /
DashScope OpenAI 兼容接口）逐条采样，原始回答全部落盘，标注数据等级 A（API 真测）。
对"无法直连"的模型（文心/豆包/元宝/Kimi/海外）不臆造数据，改为产出标准化人工
取证协议与模板，标注数据等级 B（人工取证，pending）。

复现：
  python geo_audit.py --probe            # 仅探测哪些模型可用
  python geo_audit.py                     # 全量真测（4 模型 × 全部查询，可断点续跑）
  python geo_audit.py --models qwen-max deepseek-v3 --limit 8 --workers 4
  python geo_audit.py --emit-manual       # 仅生成人工取证协议/模板

设计要点：
  - 通过 subprocess 调 bl，避免 PowerShell 引号地狱；输出按 utf-8 容错解码。
  - 断点续跑：已存在的 raw/{model}/{qid}.json 默认跳过（--force 重跑）。
  - 线程池并发（默认 4），每次调用记录时延、用量、错误。
  - 绝不编造：模型不可用或调用失败时，如实记录 error，不填充虚假回答。
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import threading
import time

import geo_config as C

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "outputs")
RAW = os.path.join(OUT, "raw")
MANUAL = os.path.join(OUT, "manual")
QUERIES = os.path.join(BASE, "queries.json")

_print_lock = threading.Lock()


def log(*a):
    with _print_lock:
        print(*a, flush=True)


def _bl_path():
    """定位 bl 可执行文件（Windows 下多为 bl.cmd）。"""
    for name in ("bl", "bl.cmd", "bl.exe"):
        p = shutil.which(name)
        if p:
            return p
    return "bl"


BL = _bl_path()


def load_queries():
    with open(QUERIES, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_text(payload):
    """从 bl --output json 的返回里尽量稳健地取出回答正文。"""
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, dict):
        return ""
    # OpenAI 兼容 choices[].message.content
    try:
        ch = payload.get("choices")
        if ch and isinstance(ch, list):
            msg = ch[0].get("message") or {}
            if msg.get("content"):
                return msg["content"]
            if ch[0].get("text"):
                return ch[0]["text"]
    except Exception:
        pass
    for k in ("content", "text", "output_text", "result", "answer"):
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v
    out = payload.get("output")
    if isinstance(out, dict):
        for k in ("text", "content"):
            if isinstance(out.get(k), str):
                return out[k]
        ch = out.get("choices")
        if ch and isinstance(ch, list):
            msg = ch[0].get("message") or {}
            if msg.get("content"):
                return msg["content"]
    return ""


def _usage(payload):
    if isinstance(payload, dict):
        u = payload.get("usage") or (payload.get("output") or {}).get("usage")
        if isinstance(u, dict):
            return u
    return {}


def call_model(model_id, message, max_tokens=600, timeout=180):
    """调用一次 bl text chat，返回 (ok, text, raw_stdout, meta)。"""
    cmd = [
        BL, "text", "chat",
        "--model", model_id,
        "--message", message,
        "--max-tokens", str(max_tokens),
        "--output", "json",
        "--non-interactive",
    ]
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd, capture_output=True, timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return False, "", "", {"error": "timeout", "elapsed": time.time() - t0}
    except Exception as e:  # noqa: BLE001
        return False, "", "", {"error": f"spawn_failed: {e}", "elapsed": time.time() - t0}

    elapsed = time.time() - t0
    stdout = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
    stderr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""

    # 提取首个 JSON 对象（bl 可能带少量非 JSON 杂讯）
    payload = None
    s = stdout.strip()
    if s:
        try:
            payload = json.loads(s, strict=False)
        except Exception:
            i, j = s.find("{"), s.rfind("}")
            if i != -1 and j != -1 and j > i:
                try:
                    payload = json.loads(s[i:j + 1], strict=False)
                except Exception:
                    payload = None

    text = _extract_text(payload) if payload is not None else ""
    if not text and not s and stderr:
        return False, "", stdout, {"error": stderr[:500], "elapsed": elapsed}
    ok = bool(text.strip())
    meta = {
        "elapsed": round(elapsed, 2),
        "usage": _usage(payload),
        "returncode": proc.returncode,
    }
    if not ok:
        meta["error"] = (stderr[:500] or "empty_response")
    return ok, text, stdout, meta


def probe_models(candidates):
    """对候选 API 模型做一次极小调用，返回可用清单。"""
    available = []
    for m in candidates:
        ok, text, _, meta = call_model(m["model"], "ping：请回复'ok'。", max_tokens=16, timeout=90)
        status = "OK" if ok else f"UNAVAILABLE ({meta.get('error', '')[:80]})"
        log(f"  [probe] {m['key']:14s} ({m['model']}) -> {status}  {meta.get('elapsed','')}s")
        if ok:
            available.append(m)
    return available


def run_one(m, q, max_tokens, force):
    mdir = os.path.join(RAW, m["key"])
    os.makedirs(mdir, exist_ok=True)
    fp = os.path.join(mdir, f"{q['id']}.json")
    if os.path.exists(fp) and not force:
        return ("skip", m["key"], q["id"])
    ok, text, raw, meta = call_model(m["model"], q["text"], max_tokens=max_tokens)
    rec = {
        "query_id": q["id"], "tier": q["tier"], "persona": q["persona"],
        "intent": q["intent"], "lang": q["lang"], "query": q["text"],
        "model_key": m["key"], "vendor": m["vendor"], "model_id": m["model"],
        "grade": "A",  # API 真测
        "ok": ok, "response": text, "meta": meta,
        "collected_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    return ("ok" if ok else "err", m["key"], q["id"])


def emit_manual_protocol(queries):
    """生成标准化人工取证协议 + 模板（B 级，pending，不臆造）。"""
    os.makedirs(MANUAL, exist_ok=True)
    proto = f"""# 中科存储 GEO · 标准化人工取证协议（B 级数据）

> 适用模型：{', '.join(m['vendor'] for m in C.MODELS_MANUAL)}
> 原则：无法经 API 直连的模型，用统一流程人工取证，**截图 + 文本 + 双人复核**，
> 绝不臆造。每条记录须填入 `manual_template.json` 对应字段，留档于 outputs/manual/。

## 取证步骤（每个模型 × 每条查询）
1. 全新会话（清除上下文/记忆），关闭"个性化推荐"，统一使用 Web 版默认设置。
2. 原样粘贴 queries.json 中的 query 文本，提交。
3. 记录首次完整回答（不追问），保存：
   - 截图（命名：`{{model_key}}__{{query_id}}.png`，存 outputs/manual/shots/）
   - 纯文本回答（填入模板 response 字段）
4. 追问一句："请给出你上述回答所依据的参考来源链接。"
   - 记录其给出的来源域名/链接（填 citations 字段）。
5. 由第二人独立复核截图与文本是否一致，勾选 verified=true。

## 打分对齐
人工取证完成后，将 manual_template.json 填好的记录与 API 数据一并喂给
geo_scoring.py（脚本对 grade=B 的记录同口径打分），即可得到全模型 GVI。

## 采集节奏
- 基线：一次性完成全部查询。
- 复测：每月同协议重采，结果追加，便于趋势对比（见 governance/changelog.md）。
"""
    with open(os.path.join(MANUAL, "manual_protocol.md"), "w", encoding="utf-8") as f:
        f.write(proto)

    template = []
    for m in C.MODELS_MANUAL:
        for q in queries["queries"]:
            template.append({
                "query_id": q["id"], "tier": q["tier"], "persona": q["persona"],
                "intent": q["intent"], "lang": q["lang"], "query": q["text"],
                "model_key": m["key"], "vendor": m["vendor"], "model_id": m["key"],
                "grade": "B", "ok": None, "response": "", "citations": [],
                "screenshot": f"shots/{m['key']}__{q['id']}.png",
                "verified": False, "collected_at": None,
            })
    with open(os.path.join(MANUAL, "manual_template.json"), "w", encoding="utf-8") as f:
        json.dump({"note": "B 级人工取证模板；response 为空=未采集(pending)，不计入已采集统计。",
                   "records": template}, f, ensure_ascii=False, indent=2)
    os.makedirs(os.path.join(MANUAL, "shots"), exist_ok=True)
    log(f"  已生成人工取证协议与模板：{len(template)} 条占位（{len(C.MODELS_MANUAL)} 模型 × {len(queries['queries'])} 查询）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="仅探测可用模型")
    ap.add_argument("--emit-manual", action="store_true", help="仅生成人工取证协议/模板")
    ap.add_argument("--models", nargs="*", default=None, help="限定 model key（默认全部 API 模型）")
    ap.add_argument("--limit", type=int, default=0, help="每模型最多跑前 N 条查询（0=全部）")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=600)
    ap.add_argument("--force", action="store_true", help="重跑已存在的记录")
    args = ap.parse_args()

    os.makedirs(RAW, exist_ok=True)
    queries = load_queries()
    qlist = queries["queries"]

    if args.emit_manual:
        emit_manual_protocol(queries)
        return

    candidates = C.MODELS_API
    if args.models:
        candidates = [m for m in C.MODELS_API if m["key"] in args.models]

    log(f"bl = {BL}")
    log("探测可用模型 ...")
    available = probe_models(candidates)
    if not available:
        log("没有可用的 API 模型；仅生成人工取证协议。")
        emit_manual_protocol(queries)
        return
    log(f"可用 API 模型：{[m['key'] for m in available]}")

    if args.probe:
        with open(os.path.join(OUT, "models_available.json"), "w", encoding="utf-8") as f:
            json.dump({"available": [m["key"] for m in available],
                       "checked_at": dt.datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
        return

    use_q = qlist[:args.limit] if args.limit else qlist
    tasks = [(m, q) for m in available for q in use_q]
    log(f"待采集任务：{len(tasks)}（{len(available)} 模型 × {len(use_q)} 查询）")

    counts = {"ok": 0, "err": 0, "skip": 0}
    done = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(run_one, m, q, args.max_tokens, args.force) for m, q in tasks]
        for fut in cf.as_completed(futs):
            status, mk, qid = fut.result()
            counts[status] = counts.get(status, 0) + 1
            done += 1
            if done % 10 == 0 or status == "err":
                log(f"  [{done}/{len(tasks)}] {status:4s} {mk} {qid}  (ok={counts['ok']} err={counts['err']} skip={counts['skip']})")

    # 同时确保人工取证协议存在
    emit_manual_protocol(queries)

    manifest = {
        "compiled_at": dt.datetime.now().isoformat(timespec="seconds"),
        "available_api_models": [m["key"] for m in available],
        "manual_models": [m["key"] for m in C.MODELS_MANUAL],
        "n_queries": len(use_q), "n_tasks": len(tasks),
        "counts": counts, "seed": C.SEED,
    }
    with open(os.path.join(OUT, "run_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    log(f"完成：{counts}；manifest 写入 outputs/run_manifest.json")


if __name__ == "__main__":
    main()
