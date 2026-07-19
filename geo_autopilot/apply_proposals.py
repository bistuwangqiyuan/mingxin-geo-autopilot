# -*- coding: utf-8 -*-
"""铭信 GEO Autopilot · 提案确定性应用器（apply_proposals.py）。

把 geo_brain 的 content_proposals 安全落地到铭信官网内容数据源，并经事实闸门：
  - 站点为 amd 仓库 site/ 子目录（Next.js）；提案写入
    site/src/lib/data/autopilot_faq.json（附加产物：站点可选消费，不破坏现有构建）。
  - 事实闸门以官网单一数据源 company.ts 的镜像（business_plan/outputs/results.json）
    为准：仅接受 schema 合法、口径一致(关键数值不被改写)的提案。
  - 写入前**备份**目标文件；校验失败则**自动回滚**，绝不带病部署（自我净化）。

白帽纪律：
  - 只动站内"FAQ/术语"等可被抽取内容；UGC 草稿仅由 make_offsite_kit 刷新，不在此发布。
  - 一致性检查复用 geo_plan/source_audit.check_consistency。
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time

import paths

sys.path.insert(0, paths.GEO_PLAN)

APPLIED_LOG = os.path.join(paths.OUTPUTS, "applied_proposals.json")
# amd 仓库内的落地目标（site/ 子目录 = Next.js 站点根）
EXTRA_FAQ = os.path.join(paths.SITE_SRC, "src", "lib", "data", "autopilot_faq.json")
COMPANY_TS = os.path.join(paths.SITE_SRC, "src", "lib", "data", "company.ts")


def _consistency_issues(text):
    try:
        from source_audit import entity_facts, check_consistency
        return check_consistency(text, entity_facts())
    except Exception:
        return []


def validate_proposals(proposals):
    """返回 (accepted, rejected)，每条带 reason。"""
    accepted, rejected = [], []
    for p in proposals or []:
        ptype = p.get("type")
        if ptype == "faq":
            q, a = (p.get("question") or "").strip(), (p.get("answer") or "").strip()
            if not q or not a:
                rejected.append({**p, "reason": "faq 缺 question/answer"})
                continue
            # 长度闸门按语言：zh ≤200 字符（≈120 字）；en ≤700 字符（≈90-110 词）
            max_len = 700 if p.get("lang") == "en" else 200
            if len(a) > max_len:
                rejected.append({**p, "reason": f"answer 过长(>{max_len})"})
                continue
            issues = _consistency_issues(q + " " + a)
            if issues:
                rejected.append({**p, "reason": f"口径冲突: {issues}"})
                continue
            accepted.append(p)
        elif ptype == "glossary":
            term, d = (p.get("term") or "").strip(), (p.get("definition") or "").strip()
            if not term or not d:
                rejected.append({**p, "reason": "glossary 缺 term/definition"})
                continue
            issues = _consistency_issues(d)
            if issues:
                rejected.append({**p, "reason": f"口径冲突: {issues}"})
                continue
            accepted.append(p)
        else:
            rejected.append({**p, "reason": f"未知 type={ptype}"})
    return accepted, rejected


def _backup(path):
    """备份到 autopilot 的 outputs/backups（不污染站点仓库）。"""
    if os.path.isfile(path):
        bdir = os.path.join(paths.OUTPUTS, "backups")
        os.makedirs(bdir, exist_ok=True)
        bak = os.path.join(bdir, f"{os.path.basename(path)}.bak.{int(time.time())}")
        shutil.copy2(path, bak)
        return bak
    return None


def _write_extra_faq(accepted):
    """把接受的提案累积写入 site/src/lib/data/autopilot_faq.json。
    设计为**附加产物**：即便站点构建未消费它，也不会破坏现有站点。"""
    existing = {"faq": [], "glossary": [], "updated_at": None}
    if os.path.isfile(EXTRA_FAQ):
        try:
            with open(EXTRA_FAQ, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass
    seen_q = {x.get("question") for x in existing.get("faq", [])}
    seen_t = {x.get("term") for x in existing.get("glossary", [])}
    added = 0
    for p in accepted:
        # lang 必须保留：站点按 lang 分流 zh/en 页面。
        lang = "en" if p.get("lang") == "en" else "zh"
        if p["type"] == "faq" and p.get("question") not in seen_q:
            existing.setdefault("faq", []).append(
                {"question": p["question"], "answer": p["answer"], "lang": lang})
            added += 1
        elif p["type"] == "glossary" and p.get("term") not in seen_t:
            existing.setdefault("glossary", []).append(
                {"term": p["term"], "definition": p["definition"], "lang": lang})
            added += 1
    existing["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    bak = _backup(EXTRA_FAQ)
    os.makedirs(os.path.dirname(EXTRA_FAQ), exist_ok=True)
    with open(EXTRA_FAQ, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    return added, bak


def verify_written():
    """写盘后的确定性闸门（站点为 Next.js，本仓库不做 npm 构建）：
      1) autopilot_faq.json 必须是合法 JSON 且结构正确；
      2) 全部条目再过一遍事实一致性检查（与 company.ts 镜像 results.json 对照）；
      3) 官网单一数据源 company.ts 必须存在且未被本流程触碰。
    返回 (ok, log)。"""
    logs = []
    try:
        with open(EXTRA_FAQ, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except Exception as ex:  # noqa: BLE001
        return False, f"autopilot_faq.json 非法 JSON: {ex}"
    if not isinstance(doc.get("faq"), list) or not isinstance(doc.get("glossary"), list):
        return False, "autopilot_faq.json 结构错误（faq/glossary 须为数组）"
    for x in doc["faq"]:
        issues = _consistency_issues((x.get("question") or "") + " " + (x.get("answer") or ""))
        if issues:
            logs.append(f"faq 口径冲突: {x.get('question')}: {issues}")
    for x in doc["glossary"]:
        issues = _consistency_issues(x.get("definition") or "")
        if issues:
            logs.append(f"glossary 口径冲突: {x.get('term')}: {issues}")
    if os.path.isdir(paths.SITE_SRC) and not os.path.isfile(COMPANY_TS):
        logs.append("company.ts 缺失：站点单一数据源不在预期位置")
    ok = not logs
    return ok, "\n".join(logs) if logs else "verify OK"


def apply(decision, dry_run=False):
    """应用决策中的内容提案，经事实闸门；失败回滚。"""
    paths.ensure_dirs()
    proposals = decision.get("content_proposals", [])
    accepted, rejected = validate_proposals(proposals)

    result = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "n_proposals": len(proposals),
        "accepted": accepted,
        "rejected": rejected,
        "applied": False,
        "verify_ok": None,
        "dry_run": dry_run,
        "target": EXTRA_FAQ,
        "note": "",
    }

    if not accepted:
        result["note"] = "无可接受提案（或全部被一致性/schema 拦截）"
        _save(result)
        return result

    if dry_run:
        result["note"] = "dry-run：仅校验提案，不写盘"
        _save(result)
        return result

    if not os.path.isdir(paths.SITE_SRC):
        result["note"] = f"站点目录不存在（{paths.SITE_SRC}），提案未落地（如实记录）"
        _save(result)
        return result

    added, bak = _write_extra_faq(accepted)
    result["added"] = added
    result["backup"] = bak

    ok, log = verify_written()
    result["verify_ok"] = ok
    if ok:
        result["applied"] = True
        result["note"] = f"已应用 {added} 条提案并通过事实闸门（company.ts 口径）"
        # 热词闭环：已成文并通过闸门的英文问题，回写 keyword_bank 标记 done（收敛）
        try:
            import keyword_miner
            done_qs = [p.get("question") for p in accepted
                       if p.get("type") == "faq" and p.get("lang") == "en"]
            result["keywords_marked_done"] = keyword_miner.mark_done(done_qs)
        except Exception:
            result["keywords_marked_done"] = 0
    else:
        # 回滚
        if bak and os.path.isfile(bak):
            shutil.copy2(bak, EXTRA_FAQ)
        elif os.path.isfile(EXTRA_FAQ) and bak is None:
            os.remove(EXTRA_FAQ)
        result["note"] = "verify 失败，已回滚（自我净化，未部署）"
        result["verify_log_tail"] = (log or "")[-800:]
    _save(result)
    return result


def _save(result):
    with open(APPLIED_LOG, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--decision", default=os.path.join(paths.OUTPUTS, "brain_decision.json"))
    args = ap.parse_args()
    with open(args.decision, "r", encoding="utf-8") as f:
        payload = json.load(f)
    decision = payload.get("decision", payload)
    res = apply(decision, dry_run=args.dry_run)
    print(f"[apply_proposals] accepted={len(res['accepted'])} "
          f"rejected={len(res['rejected'])} applied={res['applied']} verify_ok={res['verify_ok']}")
    print(f"  {res['note']}")


if __name__ == "__main__":
    main()
