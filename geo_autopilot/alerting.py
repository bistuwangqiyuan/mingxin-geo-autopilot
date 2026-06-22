# -*- coding: utf-8 -*-
"""中科存储 GEO Autopilot · 告警（alerting.py）。

回归(GVI 跌破阈值 / 部署失败 / verify 失败)或存在待人工项时，
经 gh 开/更新一个固定标题的 GitHub Issue（无 gh 或无权限则本地落盘告警，不阻断主流程）。
绝不伪造：只报告真实运行结果。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess

import paths

ALERT_FILE = os.path.join(paths.OUTPUTS, "alert.json")
ISSUE_TITLE = "[GEO Autopilot] 每日运行告警与待人工事项"
# 默认在 autopilot 仓库开 Issue；可用环境变量指定（如官网仓库）
ALERT_REPO = os.environ.get("ZK_ALERT_REPO", "")

GVI_REGRESSION_DROP = float(os.environ.get("ZK_GVI_REGRESSION_DROP", "1.0"))


def _gh():
    return shutil.which("gh")


def evaluate(snap, runlog, applied, decision):
    """汇总当日告警级别与内容。返回 dict。"""
    alerts = []
    level = "ok"

    # 1. 部署/步骤失败
    for s in runlog.get("steps", []):
        if s.get("critical") and not s.get("ok"):
            alerts.append(f"关键步骤失败：{s.get('name')} — {s.get('note','')}")
            level = "error"

    # 2. verify 闸门失败（内容自进化被拦截回滚）
    if applied.get("verify_ok") is False:
        alerts.append("内容提案未通过 verify_site 闸门，已自动回滚（站点未带病部署）。")
        level = "error" if level != "error" else level

    # 3. GVI 回归
    hist_drop = snap.get("gvi_delta")
    if hist_drop is not None and hist_drop <= -GVI_REGRESSION_DROP:
        alerts.append(f"GVI 回归：Δ={hist_drop}（阈值 -{GVI_REGRESSION_DROP}）。"
                      "注：站内改动不改变模型语料，多为采样噪声，需结合趋势判断。")
        if level == "ok":
            level = "warn"

    # 4. 待人工项（始终如实列出）
    blocked = decision.get("blocked_manual", [])
    if blocked:
        if level == "ok":
            level = "warn"

    return {"level": level, "alerts": alerts, "blocked_manual": blocked}


def _issue_body(snap, ev, decision):
    lines = [
        f"自动生成于 {snap.get('ts','')}（GEO Autopilot 每日运行）。",
        "",
        f"- 当日 GVI: **{snap.get('gvi')}**（{snap.get('gvi_source','')}），Δ={snap.get('gvi_delta')}",
        f"- 品牌被提及率: {snap.get('mention_rate')}",
        f"- DeepSeek/通义 信源覆盖: {(snap.get('coverage') or {}).get('DeepSeek')} / {(snap.get('coverage') or {}).get('通义千问')}",
        f"- Google 已收录页: {snap.get('google_indexed_pages')}",
        "",
        f"## 告警级别: `{ev['level']}`",
    ]
    if ev["alerts"]:
        lines.append("### 触发项")
        lines += [f"- {a}" for a in ev["alerts"]]
    lines.append("")
    lines.append("### 受客观约束、需人工处理（不伪造）")
    lines += [f"- [ ] {b}" for b in ev.get("blocked_manual", [])] or ["- 无"]
    lines += [
        "",
        "### 人工 SOP",
        "- UGC 发布：见 `geo_plan/offsite/SOP_manual_publish.md`",
        "- GSC 请求收录：见 `seo_geo_loop/outputs/live_status.json` 的 `gsc_url_inspection.pending_next_day`",
        "- 百度收录：需 ICP 备案，见 `seo_geo_loop/outputs/external_actions_status.json`",
        "",
        f"决策引擎：{decision.get('engine','')} · 摘要：{decision.get('summary_zh','')}",
    ]
    return "\n".join(lines)


def dispatch(snap, ev, decision, dry_run=False):
    body = _issue_body(snap, ev, decision)
    payload = {"title": ISSUE_TITLE, "level": ev["level"], "body": body,
               "alerts": ev["alerts"], "blocked_manual": ev.get("blocked_manual", [])}
    paths.ensure_dirs()
    with open(ALERT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    if dry_run or not ALERT_REPO:
        payload["delivery"] = "local_file_only(无 ZK_ALERT_REPO 或 dry-run)"
        return payload
    gh = _gh()
    if not gh:
        payload["delivery"] = "gh_not_found_local_only"
        return payload

    # 查找已存在的同名 open issue
    try:
        q = subprocess.run([gh, "issue", "list", "--repo", ALERT_REPO, "--state", "open",
                            "--search", ISSUE_TITLE, "--json", "number,title"],
                           capture_output=True, text=True, encoding="utf-8")
        existing = json.loads(q.stdout or "[]")
        num = next((it["number"] for it in existing if it.get("title") == ISSUE_TITLE), None)
        if num:
            subprocess.run([gh, "issue", "comment", str(num), "--repo", ALERT_REPO, "--body", body],
                           capture_output=True, text=True, encoding="utf-8")
            payload["delivery"] = f"commented_issue_{num}"
        else:
            subprocess.run([gh, "issue", "create", "--repo", ALERT_REPO,
                            "--title", ISSUE_TITLE, "--body", body],
                           capture_output=True, text=True, encoding="utf-8")
            payload["delivery"] = "created_issue"
    except Exception as e:  # noqa: BLE001
        payload["delivery"] = f"gh_error_local_only: {e}"
    with open(ALERT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def main():
    import metrics as M
    snap = M.collect_snapshot()
    brain = {}
    bp = os.path.join(paths.OUTPUTS, "brain_decision.json")
    if os.path.isfile(bp):
        with open(bp, "r", encoding="utf-8") as f:
            brain = json.load(f)
    decision = brain.get("decision", {})
    runlog = {}
    rp = os.path.join(paths.OUTPUTS, "run_log.json")
    if os.path.isfile(rp):
        with open(rp, "r", encoding="utf-8") as f:
            runlog = json.load(f)
    applied = {}
    appp = os.path.join(paths.OUTPUTS, "applied_proposals.json")
    if os.path.isfile(appp):
        with open(appp, "r", encoding="utf-8") as f:
            applied = json.load(f)
    ev = evaluate(snap, runlog, applied, decision)
    res = dispatch(snap, ev, decision, dry_run=os.environ.get("ZK_ALERT_DRYRUN") == "1")
    print(f"[alerting] level={ev['level']} delivery={res.get('delivery')} "
          f"alerts={len(ev['alerts'])} blocked={len(ev.get('blocked_manual', []))}")


if __name__ == "__main__":
    main()
