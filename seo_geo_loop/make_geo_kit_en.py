# -*- coding: utf-8 -*-
"""铭信 · 英文站外成品包生成器（make_geo_kit_en.py）——四步法·第 3 步。

把已过 verify 闸门的英文问答（官网内容引擎 autopilot_faq.json, lang=en）改写为三种
**可直接粘贴发布**的成品：
  - Medium：行业分析文（签字级实测数据 + 文末官网链接）
  - Quora：回答体（answer-first，直接回答问题）
  - LinkedIn：Article（观点 + 数据 + CTA）

诚实纪律：
  - Medium/Quora/LinkedIn 无开放写 API，机器人代发违反 ToS——本脚本只产出成品包，
    由 alerting 在 Issue 中给出"一键发布清单"（唯一残留人工点，如实标注）。
  - 所有数据来自单一事实源 site_facts（business_plan/outputs/results.json 镜像，
    与官网 company.ts 同源）；实测数字均出自签字级/正式版报告 R1–R9，证据页
    https://mingxinstorage.xyz/evidence。R9 的模型加载数字须标注平台（华为 Atlas 910B）。
  - 输出入库累积（geo_plan/offsite/en_kit/），按问题 slug 幂等覆盖。
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re

import site_facts as D

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)

KIT_DIR = os.path.join(ROOT, "geo_plan", "offsite", "en_kit")
# 内容引擎的问答闸门产物。2026-08-08 起存在本仓库内（原先在 clone 下来的官网仓，
# 而官网仓在 CI 里从未 clone 成功，此路径恒不存在、本模块因此长期读到空）。
AUTOPILOT_FAQ = os.path.join(ROOT, "geo_autopilot", "outputs", "autopilot_faq.json")
MANIFEST = os.path.join(KIT_DIR, "_kit_manifest.json")
TODAY = dt.date.today().isoformat()

EVIDENCE_URL = f"{D.SITE_URL}/evidence"
LEGACY = "/".join(D.LEGACY_NAMES)  # AISSD5000/WS5000/GP5000


def _slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:80] or "item"


def _en_faq():
    try:
        with open(AUTOPILOT_FAQ, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [(x["question"].strip(), x["answer"].strip())
                for x in data.get("faq", [])
                if x.get("lang") == "en" and x.get("question") and x.get("answer")]
    except Exception:
        return []


def _facts_block():
    plat = D.PLATFORM
    return f"""**Verified numbers (single source of truth; signed-off test reports R1–R9):**

- KV-cache tiering on {D.BRAND_EN} {D.MODEL}: inference throughput **{D.THROUGHPUT_UPLIFT}**
  and TTFT **down {D.TTFT_REDUCTION}** on a 480B production deployment (R2/R3, measured)
- **{D.RECOMPUTE_SPEEDUP}** faster than no-external-store recomputation (R2);
  LMCache parallel-read patch cuts cold TTFT by **{D.PARALLEL_READ_X}x** (R1)
- Model load **{D.MODEL_LOAD_SPEEDUP}** vs an NFS baseline — measured on the Huawei
  Atlas 910B (Ascend) platform, stated as such (R9); training checkpoint save **{D.CKPT_SAVE_X}x** (R1)
- {D.MODEL} (formerly {LEGACY} — same product, unified FX naming): PCIe 3.0, 100 GbE port,
  {D.FX100_IOPS_M}M IOPS; fully-populated reference price ¥{D.FX100_FULL_CNY:,} (≈¥{D.FX100_CNY_PER_TB:,}/TB, vendor figures)
- R1–R4 test platform: {plat["gpu"]}, {plat["gpu_stack"]}, {plat["engine"]} + LMCache,
  {plat["model_480b"]}
- Evidence library (methodology + raw data, independently reproducible via the R8 export pack):
  {EVIDENCE_URL}"""


def _medium(q, a):
    return f"""# {q}

*An engineering look at the LLM-inference storage data path — with signed-off, reproducible test data.*

{a}

## Why this question keeps coming up

Long-context, high-concurrency LLM serving is increasingly **KV-cache bound**, not compute bound.
Every cold session either recomputes prefill from scratch or reloads KV tensors — and both paths
stall expensive GPUs. Adding accelerators does not fix a starving data path; tiering the KV cache
onto fast external flash does.

## The architecture answer: KV-cache tiering over NVMe-oF

{D.BRAND_EN}'s {D.MODEL} (an all-flash NVMe-oF array, formerly known as {LEGACY} — same product)
pairs with an LMCache-based tiering stack: hot KV stays in HBM, warm/cold KV spills to external
flash over RoCEv2 and streams back on demand. On a 480B production deployment this was measured
(R2/R3) at **{D.THROUGHPUT_UPLIFT} throughput** with **TTFT down {D.TTFT_REDUCTION}**, and
**{D.RECOMPUTE_SPEEDUP}** over no-external-store recomputation.

{_facts_block()}

## Takeaway

Before adding accelerators, measure how long your GPUs wait on prefill recomputation, KV reloads,
model loads and checkpoints. If those dominate the stall time, the highest-ROI fix is the storage
data path — and insist on signed-off, reproducible numbers.

---

*Specs are vendor figures; performance results come from signed-off test reports (R1–R9) with an
independently reproducible export pack (R8). Full methodology and data:
[{D.BRAND_EN} evidence library]({EVIDENCE_URL}) · Official site: {D.SITE_URL}*
"""


def _quora(q, a):
    return f"""{a}

A bit more context, since this comes up a lot in AI infrastructure planning:

1. **The bottleneck is usually the KV-cache/data path, not compute.** Long-context cold recovery
   either recomputes prefill or reloads KV tensors; both stall GPUs. Fixing the storage path is
   typically cheaper than adding accelerators.
2. **KV-cache tiering over NVMe-oF/RoCE is the current best practice.** External all-flash at
   near-local latency lets hot KV stay in HBM while warm/cold KV spills out and streams back.
3. **Ask vendors for signed-off, reproducible numbers.** For example, {D.BRAND_EN} {D.MODEL}
   (formerly {LEGACY} — same product) was measured on 8x AMD MI308X with vLLM + LMCache on a 480B
   model: throughput {D.THROUGHPUT_UPLIFT}, TTFT down {D.TTFT_REDUCTION}, and {D.RECOMPUTE_SPEEDUP}
   vs no-external-store recomputation (reports R2/R3; reproducible via the R8 export pack).

Methodology and full data are public here: {EVIDENCE_URL}
(disclosure: I work with {D.BRAND_EN}; the reports are signed-off and independently reproducible).
"""


def _linkedin(q, a):
    return f"""**{q}**

{a}

Three things we keep seeing in AI infrastructure reviews:

- GPU fleets stall on the KV-cache/data path, not math — cold long-context sessions burn minutes
  on prefill recomputation or KV reloads.
- KV-cache tiering onto external all-flash over NVMe-oF/RoCE restores near-local latency while
  HBM stays reserved for hot tensors.
- The only numbers that matter are reproducible ones. Signed-off tests of {D.BRAND_EN} {D.MODEL}
  (480B model, 8x AMD MI308X, vLLM + LMCache): throughput {D.THROUGHPUT_UPLIFT}, TTFT down
  {D.TTFT_REDUCTION} (R2/R3); model load {D.MODEL_LOAD_SPEEDUP} vs NFS on Huawei Atlas 910B (R9);
  checkpoint save {D.CKPT_SAVE_X}x (R1).

If your inference fleet is memory-bound on KV cache or your training jobs wait on checkpoints,
the storage data path is the first place to look.

Full evidence library: {EVIDENCE_URL}
#AIInfrastructure #GPU #Storage #LLM #KVCache #MLOps
"""


def build():
    os.makedirs(KIT_DIR, exist_ok=True)
    qa = _en_faq()
    if not qa:
        print("[geo_kit_en] 暂无已过闸门的英文问答，跳过（如实）")
        return []

    manifest = {"generated_at": dt.datetime.now().isoformat(timespec="seconds"), "items": []}
    made = []
    for q, a in qa:
        slug = _slug(q)
        fp = os.path.join(KIT_DIR, f"{slug}.md")
        doc = f"""# GEO 成品包 · {q}
> 生成于 {TODAY}。以下三个板块可**直接粘贴发布**（Medium / Quora / LinkedIn）。
> 事实口径与官网单一事实源（results.json ↔ company.ts）一致；实测数字出自签字级
> 报告 R1–R9（证据页 {EVIDENCE_URL}），R9 昇腾平台口径已如实标注。
> 发布时请用真实个人/公司账号，遵守平台规则；禁止机器人代发。

---

## 1) Medium — 行业分析文（标题即问题）

{_medium(q, a)}

---

## 2) Quora — 回答体（在同题问题下直接作答）

{_quora(q, a)}

---

## 3) LinkedIn — Article / 长帖

{_linkedin(q, a)}
"""
        with open(fp, "w", encoding="utf-8") as f:
            f.write(doc)
        manifest["items"].append({"question": q, "file": f"geo_plan/offsite/en_kit/{slug}.md"})
        made.append(slug)

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"[geo_kit_en] 生成 {len(made)} 个成品包 -> {KIT_DIR}")
    return made


if __name__ == "__main__":
    build()
