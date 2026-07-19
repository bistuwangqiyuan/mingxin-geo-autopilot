# -*- coding: utf-8 -*-
"""铭信 GEO Autopilot · 苹果视觉日报（build_daily_report.py）。

读取当日 snapshot + brain_decision + applied_proposals + run_log，
产出《铭信 · GEO 自动驾驶日报》HTML（苹果视觉），数据全部来自单一事实源，绝不臆造。
"""
from __future__ import annotations

import datetime as dt
import json
import os

import paths
import metrics as M
import trend

HTML_OUT = os.path.join(paths.REPORTS, "铭信-GEO自动驾驶日报.html")


def _load(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def pct(v, d=1):
    return "—" if v is None else f"{float(v) * 100:.{d}f}%"


def num(v, d=2):
    return "—" if v is None else f"{float(v):.{d}f}"


def _fig_tag(name, cap):
    p = os.path.join(paths.FIGURES, name)
    if not os.path.isfile(p):
        return ""
    rel = os.path.relpath(p, paths.REPORTS).replace("\\", "/")
    return f'<figure><img src="{rel}" alt="{cap}"/><figcaption>{cap}</figcaption></figure>'


def build():
    paths.ensure_dirs()
    snap = M.collect_snapshot()
    M.write_snapshot(snap)
    trend.make_figures()

    brain = _load(os.path.join(paths.OUTPUTS, "brain_decision.json"))
    decision = brain.get("decision", {})
    applied = _load(os.path.join(paths.OUTPUTS, "applied_proposals.json"))
    runlog = _load(os.path.join(paths.OUTPUTS, "run_log.json"))

    today = snap["date"]
    hist = M.load_history()

    # 优先级行动表
    pri_rows = "".join(
        f"<tr><td>{p.get('action','')}</td><td><span class='tag'>{p.get('layer','')}</span></td>"
        f"<td>{p.get('impact','')}</td><td class='mut'>{p.get('rationale','')}</td></tr>"
        for p in decision.get("priorities", [])
    ) or "<tr><td colspan=4 class='mut'>今日无新增优先行动</td></tr>"

    critique = "".join(f"<li>{c}</li>" for c in decision.get("self_critique", [])) or "<li>无</li>"
    blocked = "".join(f"<li>{b}</li>" for b in decision.get("blocked_manual", [])) or "<li>无</li>"

    # 当日动作（来自 run_log）
    steps = runlog.get("steps", [])
    step_rows = "".join(
        f"<tr><td>{s.get('name','')}</td><td>{'OK' if s.get('ok') else '跳过/失败'}</td>"
        f"<td class='mut'>{s.get('note','')}</td></tr>"
        for s in steps
    ) or "<tr><td colspan=3 class='mut'>本次为离线/dry-run，无联网动作</td></tr>"

    # 内容自进化
    ap_note = applied.get("note", "本次无内容提案应用")
    ap_n = len(applied.get("accepted", []))
    ap_verify = applied.get("verify_ok")

    engine = decision.get("engine", "rule")
    delta = snap.get("gvi_delta")
    delta_cls = "red" if (delta or 0) < 0 else "green"

    # 站内"可回答覆盖度"：真正由内容自进化驱动、可逐日累计、可现场核验。
    ac = snap.get("answerable_coverage") or {}
    ac_total = ac.get("total")
    ac_prev = None
    for h in reversed(hist):
        if h.get("date") == today:
            continue
        pac = (h.get("answerable_coverage") or {}).get("total")
        if isinstance(pac, int):
            ac_prev = pac
            break
    ac_delta = (ac_total - ac_prev) if (isinstance(ac_total, int) and isinstance(ac_prev, int)) else None
    ac_cls = "green" if (ac_delta or 0) > 0 else ""
    ac_delta_txt = ("+" + str(ac_delta)) if (ac_delta or 0) > 0 else (str(ac_delta) if ac_delta is not None else "—")

    # 四步法信号：热词台账 + GA4 流量信号（未配置/未出现如实说明）
    kb = snap.get("keyword_bank") or {}
    sig = snap.get("geo_referral_signals") or {}
    sig_status = sig.get("status")
    if sig_status == "ok":
        ai_src = sig.get("ai_engine_sources") or {}
        sig_v = "已出现" if sig.get("geo_signal_present") else "未出现"
        sig_k = (f"GEO 流量信号（reddit={sig.get('reddit_referral')} · AI来源={len(ai_src)}）")
        sig_note = ("GA4 实测（近 7 天）：GEO 生效信号已出现。" if sig.get("geo_signal_present")
                    else "GA4 实测（近 7 天）：信号尚未出现——GEO 是信号积累过程，继续按四步法迭代，非失效。")
    elif sig_status == "ga4_not_configured":
        sig_v, sig_k = "未配置", "GEO 流量信号（GA4 未配置）"
        sig_note = ("GA4 未配置：提供 MX_GA4_ID（埋码）与 GA4_PROPERTY_ID + GA4_SA_JSON（读数）"
                    "三个 Secrets 后自动激活；未配置前如实报告，绝不编造流量信号。")
    else:
        sig_v, sig_k = "—", f"GEO 流量信号（{sig_status or 'not_run'}）"
        sig_note = f"流量信号检测状态：{sig_status or 'not_run'}（如实记录）。"

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>铭信 · GEO 自动驾驶日报 {today}</title>
<style>
:root{{--ink:#1D1D1F;--ink2:#48484A;--mut:#86868B;--line:#E2E2E7;--line2:#F0F0F3;--blue:#0071E3;--green:#34C759;--red:#FF375F;--bg:#FFF;--card:#FBFBFD;}}
*{{box-sizing:border-box}} html,body{{margin:0;padding:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  line-height:1.65;font-size:15px;}}
.wrap{{max-width:980px;margin:0 auto;padding:0 30px;}}
h2{{font-size:26px;font-weight:650;margin:0 0 6px;letter-spacing:-0.01em;}}
h3{{font-size:18px;font-weight:600;margin:24px 0 8px;}}
p{{margin:9px 0;color:var(--ink2);}} .mut{{color:var(--mut);font-size:13px;}}
.section{{padding:36px 0;border-top:1px solid var(--line2);}}
.eyebrow{{font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--blue);}}
.kpis{{display:flex;flex-wrap:wrap;gap:14px;margin:18px 0;}}
.kpi{{flex:1 1 150px;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px;}}
.kpi .v{{font-size:28px;font-weight:680;letter-spacing:-0.02em;}} .kpi .v.blue{{color:var(--blue);}}
.kpi .v.red{{color:var(--red);}} .kpi .v.green{{color:#1E9E4A;}}
.kpi .k{{font-size:12px;color:var(--mut);margin-top:2px;}}
table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:13.5px;}}
th,td{{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top;}}
th{{font-size:11px;text-transform:uppercase;color:var(--mut);}}
figure{{margin:16px 0;text-align:center;}} figure img{{max-width:100%;border:1px solid var(--line);border-radius:14px;}}
figcaption{{font-size:12px;color:var(--mut);margin-top:6px;}}
.note{{background:#FFF8EC;border:1px solid #F3E2BD;border-radius:14px;padding:14px 18px;margin:14px 0;}}
.note.ok{{background:#EFFaf1;border-color:#CDEBD5;}} .note.crit{{background:#FFF1F3;border-color:#F6CBD4;}}
.tag{{display:inline-block;font-size:11px;font-weight:600;padding:2px 9px;border-radius:999px;background:#EEF;color:#0058B9;}}
.cover{{min-height:780px;display:flex;flex-direction:column;justify-content:center;padding:56px 30px;}}
.cover .big{{font-size:42px;font-weight:700;letter-spacing:-0.03em;line-height:1.1;margin:8px 0;}}
@media print{{.section{{padding:24px 0;}} .cover{{min-height:760px;}}}}
</style></head><body>

<section class="cover"><div class="wrap">
  <div class="eyebrow">GEO Autopilot · 自动驾驶日报</div>
  <div class="big">铭信 GEO 系统<br/>每日自动运行报告</div>
  <p>本报告由全自动 AI GEO 系统于每日云端运行后生成，所有指标源自真实测量与单一事实源，可复现、不臆造。</p>
  <p class="mut">报告日期：{today} · 决策引擎：{engine} · 历史样本：{len(hist)} 天</p>
</div></section>

<section class="section"><div class="wrap">
  <div class="eyebrow">当日核心指标</div>
  <h2>{decision.get('summary_zh','当日 GEO 状态')}</h2>
  <div class="kpis">
    <div class="kpi"><div class="v blue">{num(snap.get('gvi'))}</div><div class="k">总体 GVI（{snap.get('gvi_source','')}）</div></div>
    <div class="kpi"><div class="v {delta_cls}">{('+' if (delta or 0)>=0 else '')+num(delta,2) if delta is not None else '—'}</div><div class="k">Δ GVI（对照基线）</div></div>
    <div class="kpi"><div class="v">{pct(snap.get('mention_rate'))}</div><div class="k">品牌被提及率</div></div>
    <div class="kpi"><div class="v">{pct(snap.get('citation_rate'))}</div><div class="k">带来源引用率</div></div>
  </div>
  <div class="kpis">
    <div class="kpi"><div class="v {ac_cls}">{ac_total if ac_total is not None else '—'}</div><div class="k">站内可回答单元 · 部署实测（FAQ+术语）</div></div>
    <div class="kpi"><div class="v {ac_cls}">{ac_delta_txt}</div><div class="k">较上次净增 · 内容自进化（每日增长）</div></div>
    <div class="kpi"><div class="v">{num(snap.get('best_cri'))}</div><div class="k">CRI 站内就绪度（已收敛=满分维持）</div></div>
    <div class="kpi"><div class="v">{pct(snap.get('recommendation_mention'))}</div><div class="k">推荐类问法被提及</div></div>
  </div>
  <div class="kpis">
    <div class="kpi"><div class="v">{pct((snap.get('coverage') or {}).get('DeepSeek'))}</div><div class="k">DeepSeek 信源覆盖</div></div>
    <div class="kpi"><div class="v">{pct((snap.get('coverage') or {}).get('通义千问'))}</div><div class="k">通义 信源覆盖</div></div>
    <div class="kpi"><div class="v">{snap.get('google_indexed_pages') if snap.get('google_indexed_pages') is not None else '—'}</div><div class="k">Google 已收录页</div></div>
    <div class="kpi"><div class="v">{len(snap.get('offsite_channels_live') or [])}</div><div class="k">站外信源（实测 200）</div></div>
  </div>
  <div class="kpis">
    <div class="kpi"><div class="v">{kb.get('total') if kb.get('total') is not None else '—'}</div><div class="k">热词台账累计（四步法·第1步）</div></div>
    <div class="kpi"><div class="v">{kb.get('done') if kb.get('done') is not None else '—'}</div><div class="k">热词已成文（过 verify 闸门）</div></div>
    <div class="kpi"><div class="v">{kb.get('pending') if kb.get('pending') is not None else '—'}</div><div class="k">热词待成文</div></div>
    <div class="kpi"><div class="v">{sig_v}</div><div class="k">{sig_k}</div></div>
  </div>
  <p class="mut">{sig_note}</p>
</div></section>

<section class="section"><div class="wrap">
  <div class="eyebrow">趋势看板（可复盘）</div>
  <h2>关键指标随时间变化</h2>
  {_fig_tag('trend_answerable.png','站内可回答单元趋势（内容自进化·每日累计）')}
  {_fig_tag('trend_gvi.png','总体 GVI 趋势')}
  {_fig_tag('trend_mention.png','被提及率趋势')}
  {_fig_tag('trend_coverage.png','站外信源加权覆盖趋势')}
</div></section>

<section class="section"><div class="wrap">
  <div class="eyebrow">AI 决策脑 · 当日优先行动</div>
  <h2>按影响×可行性排序</h2>
  <table><thead><tr><th>行动</th><th>层级</th><th>影响</th><th>依据</th></tr></thead><tbody>{pri_rows}</tbody></table>
</div></section>

<section class="section"><div class="wrap">
  <div class="eyebrow">当日自动执行动作</div>
  <h2>无人值守流水线记录</h2>
  <table><thead><tr><th>步骤</th><th>结果</th><th>说明</th></tr></thead><tbody>{step_rows}</tbody></table>
  <div class="note {'ok' if ap_verify else ''}"><h4>内容自进化（经 verify 闸门）</h4>
  <p>本次接受内容提案 {ap_n} 条；verify 闸门：{('通过' if ap_verify else ('未触发' if ap_verify is None else '失败已回滚'))}。{ap_note}</p></div>
</div></section>

<section class="section"><div class="wrap">
  <div class="eyebrow">批评与自我批评 · 坚持真理修正错误</div>
  <h2>诚实复盘</h2>
  <ul>{critique}</ul>
  <div class="note crit"><h4>受客观约束、需人工的待办（不伪造、已告警）</h4>
  <ul>{blocked}</ul>
  <p class="mut">UGC 平台无开放写 API/需实名、GSC 请求收录需登录且有配额、百度收录需 ICP 备案——系统自动开 Issue 告警并附 SOP，绝不自动伪装完成。</p></div>
</div></section>

<section class="section"><div class="wrap">
  <div class="eyebrow">数据纪律</div>
  <h2>可复现 · 单一事实源 · 三类指标如实区分</h2>
  <p class="mut"><b>站内可回答单元（answerable coverage）</b>：每日由内容自进化净增、从已部署 faq.html / glossary.html 现场统计，是本系统"每日自动提升"的真实落点（题库与 LLM 新题用尽时如实收敛，不堆砌）。</p>
  <p class="mut"><b>CRI（站内 GEO/SEO 就绪度）</b>：站内结构化/可抽取就绪度，已达满分并维持——属"已收敛"，不应也不会逐日上涨，持平即健康。</p>
  <p class="mut"><b>GVI（生成式可见性）</b>：由 4 个国产大模型 × 查询集真实 API 采样(grade A)按公开权重合成，主要由<b>站外语料被收录引用</b>与时间驱动，存在采样噪声；站内优化不直接改变模型语料，故 GVI 短期波动属正常，不等于系统未工作。</p>
  <p class="mut">信源覆盖仅计实测 HTTP 200 渠道；预测标注「规划假设、非承诺」。复现：autopilot.py（dry-run/once/ci）。</p>
</div></section>
</body></html>"""

    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html)
    meta = {"header": f"铭信 · GEO 自动驾驶日报 {today}", "footer": "铭信 Mingxin Technology · 全自动 GEO 系统"}
    with open(os.path.join(paths.REPORTS, "daily_report_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"Saved: {HTML_OUT}")
    return HTML_OUT


if __name__ == "__main__":
    build()
