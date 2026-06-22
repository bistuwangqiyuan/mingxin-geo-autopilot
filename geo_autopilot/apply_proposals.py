# -*- coding: utf-8 -*-
"""中科存储 GEO Autopilot · 提案确定性应用器（apply_proposals.py）。

把 geo_brain 的 content_proposals 安全落地到官网内容数据源，并经 verify_site.py 闸门：
  - 仅接受 schema 合法、口径一致(关键数值不被改写)的提案。
  - 写入前**备份**目标文件；构建+校验失败则**自动回滚**，绝不带病部署（自我净化）。

白帽纪律：
  - 只动站内"答案优先/FAQ/术语"等可被抽取内容；UGC 草稿仅由 make_offsite_kit 刷新，不在此发布。
  - 一致性检查复用 geo_plan/source_audit.check_consistency。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time

import paths

sys.path.insert(0, paths.GEO_PLAN)
sys.path.insert(0, paths.OFFICIAL_WEBSITE)

APPLIED_LOG = os.path.join(paths.OUTPUTS, "applied_proposals.json")
EXTRA_FAQ = os.path.join(paths.OFFICIAL_WEBSITE, "autopilot_faq.json")


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
            if len(a) > 200:
                rejected.append({**p, "reason": "answer 过长(>200)"})
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
    """把接受的提案累积写入 autopilot_faq.json（官网构建可选读取）。
    设计为**附加产物**：即便官网构建未消费它，也不会破坏现有站点。"""
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
        if p["type"] == "faq" and p.get("question") not in seen_q:
            existing.setdefault("faq", []).append(
                {"question": p["question"], "answer": p["answer"]})
            added += 1
        elif p["type"] == "glossary" and p.get("term") not in seen_t:
            existing.setdefault("glossary", []).append(
                {"term": p["term"], "definition": p["definition"]})
            added += 1
    existing["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    bak = _backup(EXTRA_FAQ)
    with open(EXTRA_FAQ, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    return added, bak


def _run(cmd, cwd):
    return subprocess.run([sys.executable, *cmd], cwd=cwd,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def build_and_verify():
    """重建官网并校验；返回 (ok, log)。"""
    b = _run(["build_site.py"], paths.OFFICIAL_WEBSITE)
    if b.returncode != 0:
        return False, "build_site 失败:\n" + (b.stdout or "") + (b.stderr or "")
    v = _run(["verify_site.py"], paths.OFFICIAL_WEBSITE)
    ok = v.returncode == 0
    return ok, (v.stdout or "") + (v.stderr or "")


def apply(decision, dry_run=False):
    """应用决策中的内容提案，经 verify 闸门；失败回滚。"""
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
        "note": "",
    }

    if not accepted:
        result["note"] = "无可接受提案（或全部被一致性/schema 拦截）"
        _save(result)
        return result

    if dry_run:
        result["note"] = "dry-run：仅校验提案，不写盘不构建"
        _save(result)
        return result

    added, bak = _write_extra_faq(accepted)
    result["added"] = added
    result["backup"] = bak

    ok, log = build_and_verify()
    result["verify_ok"] = ok
    if ok:
        result["applied"] = True
        result["note"] = f"已应用 {added} 条提案并通过 verify_site 闸门"
    else:
        # 回滚
        if bak and os.path.isfile(bak):
            shutil.copy2(bak, EXTRA_FAQ)
        elif os.path.isfile(EXTRA_FAQ) and bak is None:
            os.remove(EXTRA_FAQ)
        build_and_verify()  # 回滚后重建，恢复干净站点
        result["note"] = "verify 失败，已回滚并重建干净站点（自我净化，未部署）"
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
