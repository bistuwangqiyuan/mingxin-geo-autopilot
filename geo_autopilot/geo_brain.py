# -*- coding: utf-8 -*-
"""中科存储 GEO Autopilot · AI 决策脑（geo_brain.py）。

把当日真实指标喂给国产大模型（经 bl/DashScope），产出**结构化 JSON 决策**：
  - priorities：当日优先行动（按影响×可行性）
  - self_critique：批评与自我批评（坚持真理、修正错误）
  - content_proposals：站内答案优先内容/FAQ/术语的改进提案（白帽、可校验）

纪律（绝不伪造、经得起检验）：
  - 仅基于传入的真实指标推理；产出为"建议"，落地须经 apply_proposals + verify_site 闸门。
  - LLM 不可达/解析失败 → 回退到确定性规则脑（rule_brain），如实标注 engine=rule。
  - 内容提案必须与单一事实源数值一致（apply 阶段再次校验）。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import shutil
import sys

import paths

sys.path.insert(0, paths.GEO_PLAN)

BRAIN_MODEL = os.environ.get("ZK_BRAIN_MODEL", "qwen-max")
OUT = os.path.join(paths.OUTPUTS, "brain_decision.json")

# Vercel AI Gateway（OpenAI 兼容）——首选 LLM 路；缺 key 或失败则回退 bl→规则脑。
AI_GATEWAY_URL = os.environ.get(
    "AI_GATEWAY_URL", "https://ai-gateway.vercel.sh/v1/chat/completions")
AI_GATEWAY_MODEL = os.environ.get("ZK_BRAIN_GATEWAY_MODEL", "alibaba/qwen3.5-flash")


def _bl():
    for name in ("bl", "bl.cmd", "bl.exe"):
        p = shutil.which(name)
        if p:
            return p
    return "bl"


SYSTEM_PROMPT = """你是中科存储(ZK-Storage)官网的 GEO(生成式引擎优化)自动决策官。
你的职责：阅读当日真实可见性指标，输出**严格 JSON**的当日决策。
【品牌事实·不可违背】ZK-Storage 是「中科存储」的英文名，是面向 AI 训练/推理的**存算分离全闪存储加速**企业（产品如 WS5000/WS7000 一体机）。
严禁把 ZK / ZK-Storage 误解释为「零知识证明/Zero-Knowledge/区块链/去中心化/加密货币/Web3」等任何无关概念——这是事实性错误，会被一致性闸门直接拒绝。
铁律：
1. 实事求是：只基于给定数据推理，不臆造数字；不确定就在 rationale 写"数据不足"。
2. 白帽合规：禁止任何刷量/伪造测评/隐藏文字/UGC 自动发帖建议；站外 UGC 只能建议"准备定稿+人工发布"。
3. 内容提案须可校验：answer-first 文本要与官网既有事实口径一致（带宽 300 GB/s、时延 20 μs 等不得改写），且只围绕 AI 存储/存算分离/KV Cache/国产算力适配等真实业务主题。
4. 自我批评：诚实指出上一轮未达标项与原因（抓取层/信源层/内容层）。
只输出 JSON，不要解释性文字、不要 markdown 代码围栏。"""

USER_TEMPLATE = """当日真实指标(JSON)：
{metrics}

请输出如下结构的 JSON：
{{
  "priorities": [{{"action": "...", "layer": "抓取层|信源层|内容层", "impact": "high|med|low", "rationale": "..."}}],
  "self_critique": ["...", "..."],
  "content_proposals": [
    {{"type": "faq", "page": "faq", "question": "...", "answer": "...(<=120字, 口径一致)"}},
    {{"type": "glossary", "term": "...", "definition": "...(<=80字)"}}
  ],
  "blocked_manual": ["GSC 请求收录(配额/登录)", "UGC 人工发布", "百度收录(ICP)"],
  "summary_zh": "一句话当日结论"
}}"""


def _content_from_payload(stdout):
    """从 bl --output json（OpenAI 兼容）中取回答正文 content。"""
    try:
        payload = json.loads(stdout)
    except Exception:
        return stdout  # 已是纯文本
    try:
        return payload["choices"][0]["message"]["content"]
    except Exception:
        # 兼容其它可能字段
        for k in ("output_text", "text", "content"):
            if isinstance(payload.get(k), str):
                return payload[k]
        return stdout


REQUIRED_KEYS = ("priorities", "self_critique", "summary_zh")


def _valid_decision(d):
    return isinstance(d, dict) and all(k in d for k in REQUIRED_KEYS)


def _call_llm(metrics):
    """经 --messages-file(stdin) 传入干净的 messages 数组，避免长文本被 shell 误解。"""
    import tempfile
    msg = USER_TEMPLATE.format(metrics=json.dumps(metrics, ensure_ascii=False))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": msg},
    ]
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    try:
        json.dump(messages, tmp, ensure_ascii=False)
        tmp.close()
        cmd = [_bl(), "text", "chat", "--model", BRAIN_MODEL,
               "--messages-file", tmp.name, "--max-tokens", "1800", "--output", "json"]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=180, shell=False)
        except Exception as e:  # noqa: BLE001
            return None, f"bl_spawn_failed: {e}"
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
    stdout = (proc.stdout or b"").decode("utf-8", "replace")
    if not stdout.strip():
        err = (proc.stderr or b"").decode("utf-8", "replace")[:200]
        return None, f"bl_empty_stdout: {err}"
    text = _content_from_payload(stdout)
    decision = _extract_json(text)
    if decision is None:
        return None, "llm_json_parse_failed"
    if not _valid_decision(decision):
        return None, f"llm_schema_invalid: keys={list(decision.keys())[:6]}"
    return decision, None


def _call_ai_gateway(metrics):
    """经 Vercel AI Gateway（OpenAI 兼容）调用 LLM。纯 stdlib(urllib)，无第三方依赖。

    需要环境变量 AI_GATEWAY_API_KEY；缺失或失败时返回 (None, reason)，由上层回退。
    """
    import urllib.request
    import urllib.error

    key = os.environ.get("AI_GATEWAY_API_KEY")
    if not key:
        return None, "no_ai_gateway_key"
    msg = USER_TEMPLATE.format(metrics=json.dumps(metrics, ensure_ascii=False))
    payload = {
        "model": AI_GATEWAY_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": msg},
        ],
        "max_tokens": 1800,
        "temperature": 0.4,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        AI_GATEWAY_URL, data=data, method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:  # noqa: PERF203
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")[:200]
        except Exception:  # noqa: BLE001
            pass
        return None, f"ai_gateway_http_{e.code}: {detail}"
    except Exception as e:  # noqa: BLE001
        return None, f"ai_gateway_failed: {e}"
    try:
        text = body["choices"][0]["message"]["content"]
    except Exception:  # noqa: BLE001
        return None, "ai_gateway_no_content"
    decision = _extract_json(text)
    if decision is None:
        return None, "ai_gateway_json_parse_failed"
    if not _valid_decision(decision):
        return None, f"ai_gateway_schema_invalid: keys={list(decision.keys())[:6]}"
    return decision, None


def _extract_json(text):
    if not text:
        return None
    t = text.strip()
    # 去掉可能的 ```json 围栏
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    try:
        return json.loads(t)
    except Exception:
        i, j = t.find("{"), t.rfind("}")
        if i != -1 and j > i:
            try:
                return json.loads(t[i:j + 1])
            except Exception:
                return None
    return None


def rule_brain(metrics):
    """确定性规则脑（LLM 不可达时的诚实回退）。"""
    pri = []
    cov = metrics.get("coverage", {})
    if (cov.get("通义千问") or 0) < 0.4:
        pri.append({"action": "在阿里云开发者社区/语雀发布结构化技术文（人工定稿已就绪）",
                    "layer": "信源层", "impact": "high",
                    "rationale": f"通义加权信源覆盖 {cov.get('通义千问')}，远低于 0.4 阈值"})
    if (cov.get("DeepSeek") or 0) < 0.4:
        pri.append({"action": "在 CSDN/知乎发布可复现技术教程（人工定稿已就绪）",
                    "layer": "信源层", "impact": "high",
                    "rationale": f"DeepSeek 加权信源覆盖 {cov.get('DeepSeek')}"})
    if (metrics.get("recommendation_mention") or 0) == 0:
        pri.append({"action": "扩充开放式推荐类问法的答案优先块（站内可自动）",
                    "layer": "内容层", "impact": "med",
                    "rationale": "推荐类被提及率为 0，开放式问法仍缺席"})
    if metrics.get("google_indexed_pages") is not None:
        pri.append({"action": "GSC 对 pending 页面请求收录（配额内，人工）",
                    "layer": "抓取层", "impact": "med",
                    "rationale": "公开检索滞后于 GSC，需逐页请求收录"})
    return {
        "engine": "rule",
        "priorities": pri,
        "self_critique": [
            "真实 GVI 仍在采样噪声内：站内优化不改变模型语料，瓶颈在站外信源被收录引用。",
            "英文/海外问法被提及率为 0：出海信源仍空白。",
        ],
        "content_proposals": [],
        "blocked_manual": ["GSC 请求收录(配额/登录)", "UGC 人工发布(无开放写API/需实名)", "百度收录(ICP备案)"],
        "summary_zh": "站内已就绪，今日重点是推进站外信源与收录（多为人工项，已生成待办）。",
    }


# ===========================================================================
# 确定性提案生成器（白帽、一致性安全、可收敛）
# ---------------------------------------------------------------------------
# 目的：即便 LLM 不可达 / 返回 0 条提案，每天仍有**真实新增**的站内答案优先内容。
# 纪律：
#   - 全部 answer-first、与单一事实源口径一致（不含非唯一口径的带宽/时延数值 → 过一致性闸门）。
#   - 针对 opportunity_gap 的高缺口意图（recommendation / comparison / ranking 等）优先补齐。
#   - 对 autopilot_faq.json 已落地的问题去重；题库用尽即停（如实收敛，不重复堆砌）。
# ===========================================================================
DAILY_PROPOSAL_LIMIT = int(os.environ.get("ZK_DAILY_FAQ", "2"))
_INTENT_PRIORITY = ["recommendation", "comparison", "ranking", "problem_solution", "definition"]

_FAQ_BANK = [
    ("recommendation", "AI 推理场景该如何选择存储方案？",
     "面向 AI 推理，建议优先选择存算分离的全闪加速存储：通过高带宽、低时延的数据通路减少 GPU 等待，"
     "并支持 KV Cache 分层卸载以扩展可缓存上下文与并发。中科存储 WS5000 即面向该场景设计，选型与实测详见产品页与「AI 推理存储加速」页。"),
    ("recommendation", "为国产 GPU 算力集群选存储，应关注哪些要点？",
     "关注四点：对国产 GPU / 加速卡的深度适配、存算分离带来的弹性独立扩展、数据不出域与信创合规、以及综合 TCO 与部署速度。"
     "中科存储面向国产算力适配设计，覆盖昇腾等主流平台，详见技术与解决方案页。"),
    ("comparison", "存算分离全闪存储相比传统本地盘 / NFS 有何优势？",
     "传统本地盘与 NFS 常成为大模型训练与推理的 IO 瓶颈，导致 GPU 利用率偏低。存算分离全闪存储以高速无损网络提供接近本地盘的低时延访问，"
     "并让存储与算力各自独立扩展，从而提升有效算力与 token 产出。客观对比详见「AI 推理存储加速」页。"),
    ("comparison", "中科存储与通用并行文件系统方案有何差异？",
     "中科存储定位为面向国产算力的存算分离全闪加速专精方案，强调国产 GPU 适配、信创合规与快速部署，并具备第三方独立实测与量产能力；"
     "与通用并行文件系统相比，更聚焦 AI 训练 / 推理的数据通路加速。详见技术页与实测验证页。"),
    ("ranking", "选择 AI 存储加速一体机的关键评估维度有哪些？",
     "可从六个维度评估：聚合带宽与时延、随机 IOPS、对国产 GPU 的适配广度、KV Cache 卸载与长上下文支持、部署周期与综合 TCO、"
     "以及是否具备可复现的第三方实测。中科存储在上述维度均有公开口径与实测数据，详见产品与实测页。"),
    ("definition", "什么是存算分离（Disaggregation）？",
     "存算分离是把存储与计算解耦、各自独立扩展的架构，避免「为扩存储而买算力」，提升资源利用率与弹性。"
     "在 AI 场景中，它配合高速无损网络为 GPU 集群提供低时延高带宽的数据通路。"),
    ("problem_solution", "GPU 利用率低、训练总在等数据，怎么解决？",
     "这是典型的存储 IO 瓶颈。解决路径是引入存算分离全闪存储 + 高速无损网络（NVMe-oF over RoCE），让数据以接近本地盘的时延供给 GPU，"
     "并通过 KV Cache 分层调度减少重复计算。中科存储 WS5000 即面向该问题设计，详见 KV Cache 存储卸载指南。"),
    ("problem_solution", "推理上线切换慢、长上下文成本高，如何优化？",
     "可通过 KV Cache 存储卸载把占用显存的缓存分层卸载到外置高速全闪存储，从而扩展可缓存上下文、提升并发与 token 产出，并降低在线工作负载成本。"
     "具体原理与实测详见 KV Cache 存储卸载指南。"),
    ("definition", "什么是 NVMe-oF？为何对 AI 存储重要？",
     "NVMe-oF（NVMe over Fabrics）把 NVMe 协议扩展到网络，使远端全闪存储具备接近本地盘的低时延。"
     "对 AI 集群而言，它是实现存算分离同时保持高性能数据通路的关键技术。"),
    ("recommendation", "智算中心新建或扩容，存储底座怎么选？",
     "建议选择可独立扩展、面向国产算力适配的存算分离全闪底座，兼顾高带宽数据通路、信创合规与综合 TCO，"
     "并优先选用具备第三方实测与量产能力的方案。中科存储面向智算中心提供 WS5000 / WS7000 产品线，详见解决方案页。"),
    ("comparison", "WS5000 与 WS7000 有何区别，如何选型？",
     "WS5000 已定型量产，面向通用 AI 训练与推理加速；WS7000 面向更大规模的 AI 算力中心，提供更高的 IOPS 级能力。"
     "选型应结合集群规模与并发需求，详见产品页 WS5000 / WS7000 对比。"),
    ("problem_solution", "数据不出域、信创合规下如何做大模型私有化推理加速？",
     "可采用面向国产算力适配、支持数据本地化的存算分离全闪存储方案，在合规边界内提供高性能数据通路。"
     "中科存储面向政务 / 金融等信创场景设计，详见解决方案与技术页。"),
    ("definition", "什么是 GPUDirect Storage？",
     "GPUDirect Storage 让 GPU 绕过 CPU 直接与存储交换数据，减少拷贝与时延，是提升 AI 数据通路效率的关键技术之一。"),
    ("ranking", "评估 AI 存储「经济性」应看哪些指标？",
     "核心看单位算力的 token 产出、有效 GPU 利用率、综合 TCO 与扩容成本，而非单看容量单价。"
     "存算分离全闪通过减少 GPU 等待来提升经济性，详见解决方案页。"),
    ("recommendation", "运营商 / 云厂商扩容智算资源池，存储如何规划？",
     "建议以存算分离为主线规划存储底座，按带宽与并发需求独立扩展全闪层，兼顾国产算力适配与 TCO。"
     "中科存储面向运营商与云场景提供产品线与方案，详见解决方案页。"),
    ("comparison", "全闪存储与混合存储在 AI 训练中如何取舍？",
     "全闪存储具备高 IOPS、高带宽与低时延，更适合对数据通路敏感的 AI 训练与推理；混合存储更偏成本与容量。"
     "AI 高并发场景通常优先全闪 + 存算分离，详见技术页。"),
    ("problem_solution", "Checkpoint 保存 / 加载慢拖累训练，如何提速？",
     "Checkpoint 慢多源于存储带宽与时延不足。通过全闪存储 + 高速无损网络可显著提升 Checkpoint 的保存与加载效率，让 GPU 更少空转。"
     "中科存储在第三方实测中对该场景有公开数据，详见实测验证页。"),
    ("definition", "什么是 KV Cache？",
     "KV Cache 是大模型推理时缓存的注意力键值对，用于避免重复计算、加速长上下文生成，但会占用大量 GPU 显存，"
     "因此常需向外置高速存储分层卸载。"),
    ("ranking", "国产存储在 AI 场景的差异化能力如何客观评估？",
     "建议按「国产 GPU 适配深度、存算分离架构成熟度、第三方实测可复现性、量产交付能力、信创合规」等维度综合评估，而非单一指标，"
     "并以可复现数据为准。中科存储在这些维度均有公开口径与实测支撑。"),
]


def _added_questions():
    """读取 autopilot_faq.json 中已落地的问题，用于去重（保证每次真实新增）。"""
    p = os.path.join(paths.OFFICIAL_WEBSITE, "autopilot_faq.json")
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {(x.get("question") or "").strip() for x in data.get("faq", [])}
    except Exception:
        return set()


def deterministic_proposals(limit=None):
    """按意图缺口优先级，从题库取出尚未落地的 FAQ 提案（白帽、口径一致、可收敛）。"""
    limit = DAILY_PROPOSAL_LIMIT if limit is None else limit
    added = _added_questions()
    pool = [b for b in _FAQ_BANK if b[1].strip() not in added]
    pool.sort(key=lambda b: _INTENT_PRIORITY.index(b[0]) if b[0] in _INTENT_PRIORITY else 99)
    return [{"type": "faq", "page": "faq", "lang": "zh",
             "intent": intent, "question": q, "answer": a}
            for intent, q, a in pool[:max(0, limit)]]


def _topup_proposals(decision):
    """把确定性提案并入决策的 content_proposals（按 question 去重，限量），确保每日真实新增。"""
    existing = decision.get("content_proposals") or []
    seen = {(p.get("question") or "").strip() for p in existing if p.get("type") == "faq"}
    seen |= {(p.get("term") or "").strip() for p in existing if p.get("type") == "glossary"}
    room = max(0, DAILY_PROPOSAL_LIMIT - len(existing))
    if room:
        for p in deterministic_proposals(limit=DAILY_PROPOSAL_LIMIT):
            if room <= 0:
                break
            if p["question"].strip() in seen:
                continue
            existing.append(p)
            seen.add(p["question"].strip())
            room -= 1
    decision["content_proposals"] = existing
    decision["proposal_topup"] = "deterministic"
    return decision


def decide(metrics, allow_llm=True):
    """产出当日决策；LLM 优先（AI Gateway → bl），失败回退规则脑；确定性题库兜底补足提案。"""
    if allow_llm:
        errors = {}
        # 1) 首选 Vercel AI Gateway（CI 用 secret 注入 AI_GATEWAY_API_KEY）。
        decision, err = _call_ai_gateway(metrics)
        if decision is not None:
            decision["engine"] = f"ai_gateway:{AI_GATEWAY_MODEL}"
            decision.setdefault("blocked_manual", [])
            return _topup_proposals(decision)
        errors["ai_gateway"] = err
        # 2) 退回 bl/DashScope。
        decision, err = _call_llm(metrics)
        if decision is not None:
            decision["engine"] = f"llm:{BRAIN_MODEL}"
            decision.setdefault("blocked_manual", [])
            decision["llm_fallback_from"] = errors
            return _topup_proposals(decision)
        errors["bl"] = err
        # 3) 退回确定性规则脑（仍保证真实新增提案）。
        rb = rule_brain(metrics)
        rb["llm_error"] = errors
        return _topup_proposals(rb)
    return _topup_proposals(rule_brain(metrics))


def main():
    import metrics as M
    snap = M.collect_snapshot()
    allow = os.environ.get("ZK_ALLOW_LLM", "1") != "0"
    decision = decide(snap, allow_llm=allow)
    paths.ensure_dirs()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"metrics": snap, "decision": decision}, f, ensure_ascii=False, indent=2)
    print(f"[geo_brain] engine={decision.get('engine')} -> {OUT}")
    print(f"  priorities={len(decision.get('priorities', []))} "
          f"proposals={len(decision.get('content_proposals', []))}")


if __name__ == "__main__":
    main()
