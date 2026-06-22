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


def _bl():
    for name in ("bl", "bl.cmd", "bl.exe"):
        p = shutil.which(name)
        if p:
            return p
    return "bl"


SYSTEM_PROMPT = """你是中科存储(ZK-Storage)官网的 GEO(生成式引擎优化)自动决策官。
你的职责：阅读当日真实可见性指标，输出**严格 JSON**的当日决策。
铁律：
1. 实事求是：只基于给定数据推理，不臆造数字；不确定就在 rationale 写"数据不足"。
2. 白帽合规：禁止任何刷量/伪造测评/隐藏文字/UGC 自动发帖建议；站外 UGC 只能建议"准备定稿+人工发布"。
3. 内容提案须可校验：answer-first 文本要与官网既有事实口径一致（带宽 300 GB/s、时延 20 μs 等不得改写）。
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


def decide(metrics, allow_llm=True):
    """产出当日决策；优先 LLM，失败回退规则脑。"""
    if allow_llm:
        decision, err = _call_llm(metrics)
        if decision is not None:
            decision["engine"] = f"llm:{BRAIN_MODEL}"
            decision.setdefault("blocked_manual", [])
            return decision
        # 回退
        rb = rule_brain(metrics)
        rb["llm_error"] = err
        return rb
    return rule_brain(metrics)


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
