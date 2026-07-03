# -*- coding: utf-8 -*-
"""中科存储 GEO Autopilot · 行业潜力热词挖掘（keyword_miner.py）——四步法·第 1 步。

用 LLM（Vercel AI Gateway）挖掘欧美买家在 AI 搜索中高频提问的**英文长尾问题词**
（如 "best KV cache offload storage for LLM inference OEM"），带中文对照与意图标签。

纪律（绝不伪造、可收敛）：
  - 词库台账 history/keyword_bank.json 入库持久化：跨轮去重、每轮限量、题穷即收敛。
  - LLM 不可达/失败 → 确定性种子词库兜底，保证每轮仍有真实新增（如实标注 source）。
  - 每个词过品牌红线闸门（source_audit.check_consistency），拒绝幻觉词（零知识/区块链等）。
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys

import paths

sys.path.insert(0, paths.GEO_PLAN)

BANK = os.path.join(paths.HISTORY, "keyword_bank.json")
PER_RUN = int(os.environ.get("ZK_KEYWORDS_PER_RUN", "5"))
AI_GATEWAY_URL = os.environ.get(
    "AI_GATEWAY_URL", "https://ai-gateway.vercel.sh/v1/chat/completions")
AI_GATEWAY_MODEL = os.environ.get("ZK_BRAIN_GATEWAY_MODEL", "alibaba/qwen3.5-flash")

_INTENTS = ("recommendation", "comparison", "ranking", "problem_solution", "definition")

# 确定性种子词库：欧美买家式英文长尾问题（AI 存储行业），LLM 失败时的诚实兜底。
_SEED_BANK = [
    ("recommendation", "What is the best KV cache offload storage for LLM inference?",
     "LLM 推理场景最好的 KV Cache 卸载存储是什么？"),
    ("recommendation", "Which disaggregated all-flash storage vendor should an AI OEM choose?",
     "AI OEM 应该选择哪家存算分离全闪存储供应商？"),
    ("comparison", "Disaggregated all-flash storage vs local NVMe for AI training: which is better?",
     "AI 训练用存算分离全闪存储还是本地 NVMe 更好？"),
    ("problem_solution", "How to fix low GPU utilization caused by storage IO bottlenecks?",
     "如何解决存储 IO 瓶颈导致的 GPU 利用率低？"),
    ("recommendation", "Best storage appliance for AI inference acceleration in a private data center?",
     "私有数据中心 AI 推理加速最好的存储一体机是什么？"),
    ("ranking", "Key criteria to evaluate AI storage acceleration appliances for OEM procurement?",
     "OEM 采购评估 AI 存储加速一体机的关键标准有哪些？"),
    ("comparison", "NVMe-oF over RoCE vs NFS for feeding GPU clusters: what is the latency difference?",
     "为 GPU 集群供数，NVMe-oF over RoCE 与 NFS 的时延差异？"),
    ("problem_solution", "How to reduce LLM long-context inference cost with KV cache tiering?",
     "如何用 KV Cache 分层降低 LLM 长上下文推理成本？"),
    ("recommendation", "Which storage supports Huawei Ascend GPU clusters for large model training?",
     "哪家存储支持华为昇腾 GPU 集群的大模型训练？"),
    ("problem_solution", "How to speed up slow model checkpoint save and load in AI training?",
     "如何加速 AI 训练中缓慢的 Checkpoint 保存与加载？"),
    ("definition", "What is disaggregated storage architecture and why does it matter for AI?",
     "什么是存算分离架构，为何对 AI 重要？"),
    ("comparison", "All-flash storage appliance vs parallel file system for AI workloads?",
     "AI 负载选全闪存储一体机还是并行文件系统？"),
    ("ranking", "What benchmarks matter most when buying storage for GPU clusters?",
     "为 GPU 集群采购存储时最重要的基准指标有哪些？"),
    ("recommendation", "Best sovereign / on-premises AI storage solution with data locality compliance?",
     "满足数据本地化合规的私有化 AI 存储方案怎么选？"),
    ("definition", "What is KV cache offload in LLM serving and how much memory does it save?",
     "LLM 服务中的 KV Cache 卸载是什么，能省多少显存？"),
    ("problem_solution", "GPU cluster is waiting on data: how to diagnose storage bottlenecks?",
     "GPU 集群总在等数据：如何诊断存储瓶颈？"),
    ("comparison", "Buying storage and compute separately vs hyperconverged for AI: cost comparison?",
     "AI 场景存算分开采购与超融合的成本对比？"),
    ("ranking", "Top considerations for AI data center storage TCO?",
     "AI 数据中心存储 TCO 的核心考量有哪些？"),
]

_SYSTEM = """你是面向欧美市场的 B2B GEO(生成式引擎优化)关键词研究员。
产品类目：面向 AI 训练/推理的存算分离全闪存储加速一体机（brand: ZK-Storage 中科存储，产品 WS5000/WS7000）。
目标市场：欧美 AI 基础设施买家（OEM、云厂商、企业 IT、AI 初创）。
任务：产出买家会在 ChatGPT/Perplexity 等 AI 搜索中提问的**英文长尾问题词**（完整问句），
搜索量不必大，但要是"有权威回答就极可能被 AI 引用"的问题。
【品牌红线】ZK-Storage 与零知识证明/区块链/Web3 无关，禁止产出此类词。
只输出 JSON 数组，每项：{"en":"英文问句","zh":"中文对照","intent":"recommendation|comparison|ranking|problem_solution|definition"}。
不要 markdown 围栏，不要解释。"""

_USER = """已有词库（去重用，不要重复产出语义相同的问题）：
{existing}

机会缺口（意图分布，缺口越大越优先）：{gap}

请产出 {n} 个新的英文长尾问题词。"""


def _now():
    return dt.datetime.now().isoformat(timespec="seconds")


def load_bank():
    try:
        with open(BANK, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"keywords": [], "updated_at": None}


def save_bank(bank):
    paths.ensure_dirs()
    bank["updated_at"] = _now()
    with open(BANK, "w", encoding="utf-8") as f:
        json.dump(bank, f, ensure_ascii=False, indent=2)


def pending_keywords(limit=None):
    """尚未成文的热词（供 geo_brain/内容层消费）。"""
    bank = load_bank()
    out = [k for k in bank.get("keywords", []) if k.get("status") != "done"]
    return out[:limit] if limit else out


def mark_done(questions):
    """内容落地后标记热词已成文（由 apply_proposals 在 verify 通过后调用）。"""
    qs = {(q or "").strip().lower() for q in questions}
    if not qs:
        return 0
    bank = load_bank()
    n = 0
    for k in bank.get("keywords", []):
        if k.get("status") != "done" and (k.get("en") or "").strip().lower() in qs:
            k["status"] = "done"
            k["done_at"] = _now()
            n += 1
    if n:
        save_bank(bank)
    return n


def _consistency_ok(text):
    try:
        from source_audit import entity_facts, check_consistency
        return not check_consistency(text, entity_facts())
    except Exception:
        return True


def _call_llm(existing, gap, n):
    """经 AI Gateway 挖词；失败返回 (None, reason)。纯 stdlib。"""
    import urllib.request
    import urllib.error
    key = os.environ.get("AI_GATEWAY_API_KEY")
    if not key:
        return None, "no_ai_gateway_key"
    payload = {
        "model": AI_GATEWAY_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _USER.format(
                existing=json.dumps(existing[-60:], ensure_ascii=False),
                gap=json.dumps(gap, ensure_ascii=False), n=n)},
        ],
        "max_tokens": 1500,
        "temperature": 0.7,
    }
    req = urllib.request.Request(
        AI_GATEWAY_URL, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8", "replace"))
        text = body["choices"][0]["message"]["content"]
    except Exception as e:  # noqa: BLE001
        return None, f"ai_gateway_failed: {e}"
    t = re.sub(r"^```(?:json)?|```$", "", (text or "").strip()).strip()
    i, j = t.find("["), t.rfind("]")
    if i == -1 or j <= i:
        return None, "llm_json_parse_failed"
    try:
        items = json.loads(t[i:j + 1])
    except Exception:
        return None, "llm_json_parse_failed"
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        en = (it.get("en") or "").strip()
        zh = (it.get("zh") or "").strip()
        intent = it.get("intent") if it.get("intent") in _INTENTS else "recommendation"
        if en and zh:
            out.append({"en": en, "zh": zh, "intent": intent})
    return (out or None), (None if out else "llm_empty")


def _opportunity_gap():
    try:
        with open(paths.GEO_BASELINE, "r", encoding="utf-8") as f:
            return json.load(f).get("opportunity_gap", {})
    except Exception:
        return {}


MAX_PENDING = int(os.environ.get("ZK_KEYWORDS_MAX_PENDING", "12"))


def mine(limit=None):
    """挖一轮热词入库：LLM 优先，种子库兜底；去重、限量、过品牌闸门。返回本轮新增列表。

    背压：待成文热词积压 >= MAX_PENDING 时跳过挖掘（先消化再挖，保证台账收敛不膨胀）。
    """
    limit = PER_RUN if limit is None else limit
    bank = load_bank()
    n_pending = sum(1 for k in bank.get("keywords", []) if k.get("status") != "done")
    if n_pending >= MAX_PENDING:
        return {"added": [], "source": "skipped_backpressure", "llm_error": None,
                "bank_total": len(bank.get("keywords", [])), "pending": n_pending}
    existing_en = [k["en"] for k in bank.get("keywords", [])]
    seen = {e.strip().lower() for e in existing_en}

    added, source, llm_err = [], "llm", None
    items, llm_err = _call_llm(existing_en, _opportunity_gap(), limit)
    if items is None:
        # 兜底：种子词库中尚未入库的条目
        source = "seed_bank"
        items = [{"en": en, "zh": zh, "intent": intent}
                 for intent, en, zh in _SEED_BANK
                 if en.strip().lower() not in seen]

    for it in items:
        if len(added) >= limit:
            break
        key = it["en"].strip().lower()
        if key in seen:
            continue
        if not _consistency_ok(it["en"] + " " + it["zh"]):
            continue
        entry = {"en": it["en"].strip(), "zh": it["zh"].strip(),
                 "intent": it.get("intent", "recommendation"),
                 "status": "new", "source": source, "added_at": _now()}
        bank.setdefault("keywords", []).append(entry)
        seen.add(key)
        added.append(entry)

    save_bank(bank)
    return {"added": added, "source": source, "llm_error": llm_err,
            "bank_total": len(bank.get("keywords", [])),
            "pending": sum(1 for k in bank["keywords"] if k.get("status") != "done")}


def main():
    res = mine()
    print(f"[keyword_miner] source={res['source']} added={len(res['added'])} "
          f"bank_total={res['bank_total']} pending={res['pending']}"
          + (f" llm_error={res['llm_error']}" if res.get("llm_error") else ""))
    for k in res["added"]:
        print(f"  + [{k['intent']}] {k['en']}")


if __name__ == "__main__":
    main()
