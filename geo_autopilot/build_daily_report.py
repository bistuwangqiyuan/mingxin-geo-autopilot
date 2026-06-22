# -*- coding: utf-8 -*-
"""中科存储 GEO Autopilot · 苹果视觉日报（build_daily_report.py）。

读取当日 snapshot + brain_decision + applied_proposals + run_log，
产出《中科存储 · GEO 自动驾驶日报》HTML（苹果视觉），数据全部来自单一事实源，绝不臆造。
"""
from __future__ import annotations

import datetime as dt
import json
import os

import paths
import metrics as M
import trend

HTML_OUT = os.path.join(paths.REPORTS, "中科存储-GEO自动驾驶日报.html")


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

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>中科存储 · GEO 自动驾驶日报 {today}</title>
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
  <div class="big">中科存储 GEO 系统<br/>每日自动运行报告</div>
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
    <div class="kpi"><div class="v">{pct((snap.get('coverage') or {}).get('DeepSeek'))}</div><div class="k">DeepSeek 信源覆盖</div></div>
    <div class="kpi"><div class="v">{pct((snap.get('coverage') or {}).get('通义千问'))}</div><div class="k">通义 信源覆盖</div></div>
    <div class="kpi"><div class="v">{snap.get('google_indexed_pages') if snap.get('google_indexed_pages') is not None else '—'}</div><div class="k">Google 已收录页</div></div>
    <div class="kpi"><div class="v">{len(snap.get('offsite_channels_live') or [])}</div><div class="k">站外信源（实测 200）</div></div>
  </div>
</div></section>

<section class="section"><div class="wrap">
  <div class="eyebrow">趋势看板（可复盘）</div>
  <h2>关键指标随时间变化</h2>
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
  <h2>可复现 · 单一事实源</h2>
  <p class="mut">GVI 由 4 个国产大模型 × 查询集真实 API 采样(grade A)按公开权重合成；信源覆盖仅计实测 HTTP 200 渠道；
  预测标注「规划假设、非承诺」。复现：autopilot.py（dry-run/once/ci）。</p>
</div></section>
</body></html>"""

    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html)
    meta = {"header": f"中科存储 · GEO 自动驾驶日报 {today}", "footer": "中科存储 ZK-Storage · 全自动 GEO 系统"}
    with open(os.path.join(paths.REPORTS, "daily_report_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"Saved: {HTML_OUT}")
    return HTML_OUT


if __name__ == "__main__":
    build()
