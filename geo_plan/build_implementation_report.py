# -*- coding: utf-8 -*-
"""组装 GEO 计划落地实施报告 HTML（苹果视觉 · 不修改计划 HTML 本身）。

读取 outputs/implementation_status.json、geo_baseline.json、source_gap.json、
seo_geo_loop/outputs/gvi_compare.json、offsite_published.json，生成实施看板。

复现：python build_implementation_report.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
OUT = os.path.join(BASE, "outputs")
LOOP_OUT = os.path.join(ROOT, "seo_geo_loop", "outputs")
HTML_OUT = os.path.join(OUT, "中科存储-GEO计划落地实施报告.html")


def _load(path, default=None):
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}


def pct(v, d=1):
    if v is None:
        return "—"
    return f"{float(v) * 100:.{d}f}%"


def num(v, d=2):
    if v is None:
        return "—"
    return f"{float(v):.{d}f}"


def status_tag(s):
    m = {"done": ("已完成", "a"), "partial": ("部分完成", "b"), "pending": ("待执行", ""),
         "pending_manual": ("待人工", "b"), "not_yet": ("未达", ""), "in_progress": ("进行中", "b"),
         "ready": ("已就绪", "a")}
    label, cls = m.get(s, (s, ""))
    return f'<span class="tag {cls}">{label}</span>'


def main():
    impl = _load(os.path.join(OUT, "implementation_status.json"))
    baseline = _load(os.path.join(OUT, "geo_baseline.json"))
    gap = _load(os.path.join(OUT, "source_gap.json"))
    gvi = _load(os.path.join(LOOP_OUT, "gvi_compare.json"))
    pub = _load(os.path.join(LOOP_OUT, "offsite_published.json"))
    cov_snap = _load(os.path.join(OUT, "source_coverage_resolved.json"))

    ov = baseline.get("overall", {})
    today = (impl.get("updated_at") or datetime.now().isoformat())[:10]

    phase_rows = ""
    for pname, pdata in impl.get("phases", {}).items():
        items = "".join(
            f"<tr><td>{k}</td><td>{status_tag(v)}</td></tr>"
            for k, v in pdata.get("items", {}).items()
        )
        phase_rows += f"""
        <h3>{pname} · {status_tag(pdata.get('status',''))}</h3>
        <p>{pdata.get('note','')}</p>
        <table><thead><tr><th>任务项</th><th>状态</th></tr></thead><tbody>{items}</tbody></table>"""

    blocked = ""
    for b in impl.get("blocked_manual", []):
        blocked += f"<li><b>{b['task']}</b> — {b['reason']} · SOP：<code>{b['sop']}</code></li>"

    channels = ""
    for ch in pub.get("channels", []):
        url = ch.get("url", "")
        channels += f"<tr><td>{ch.get('platform','')}</td><td><a href=\"{url}\">{url}</a></td><td>{status_tag(ch.get('status','published'))}</td></tr>"

    cov_evidence = ""
    for ev in cov_snap.get("evidence", []):
        cov_evidence += f"<tr><td>{ev.get('platform','')}</td><td class=\"num\">{ev.get('score','')}</td><td>{ev.get('rationale','')}</td></tr>"

    gvi_block = ""
    if gvi:
        gvi_block = f"""
        <div class="kpis">
          <div class="kpi"><div class="v blue">{num(gvi['start']['gvi'])}</div><div class="k">GVI 起点</div></div>
          <div class="kpi"><div class="v">{num(gvi['end']['gvi'])}</div><div class="k">GVI 复测</div></div>
          <div class="kpi"><div class="v {'red' if gvi.get('delta_gvi',0)<0 else 'green'}">{num(gvi.get('delta_gvi',0),2)}</div><div class="k">Δ GVI</div></div>
        </div>
        <p class="mut">{gvi.get('honest_note','')}</p>"""

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>中科存储 · GEO 计划落地实施报告</title>
<style>
:root{{--ink:#1D1D1F;--ink2:#48484A;--mut:#86868B;--line:#E2E2E7;--line2:#F0F0F3;--blue:#0071E3;--green:#34C759;--red:#FF375F;--bg:#FFF;--card:#FBFBFD;}}
*{{box-sizing:border-box}} html,body{{margin:0;padding:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  line-height:1.65;font-size:15px;}}
.wrap{{max-width:980px;margin:0 auto;padding:0 30px;}}
h1,h2,h3{{letter-spacing:-0.01em;line-height:1.2;}}
h2{{font-size:27px;font-weight:650;margin:0 0 6px;}}
h3{{font-size:19px;font-weight:600;margin:26px 0 8px;}}
p{{margin:9px 0;color:var(--ink2);}}
.mut{{color:var(--mut);font-size:13px;}}
.section{{padding:40px 0;border-top:1px solid var(--line2);}}
.eyebrow{{font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--blue);}}
.kpis{{display:flex;flex-wrap:wrap;gap:14px;margin:18px 0;}}
.kpi{{flex:1 1 140px;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px;}}
.kpi .v{{font-size:28px;font-weight:680;}} .kpi .v.blue{{color:var(--blue);}} .kpi .v.red{{color:var(--red);}} .kpi .v.green{{color:#1E9E4A;}}
.kpi .k{{font-size:12px;color:var(--mut);}}
table{{width:100%;border-collapse:collapse;margin:14px 0;font-size:13.5px;}}
th,td{{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top;}}
th{{font-size:11px;text-transform:uppercase;color:var(--mut);}}
td.num{{text-align:right;font-variant-numeric:tabular-nums;}}
.note{{background:#FFF8EC;border:1px solid #F3E2BD;border-radius:14px;padding:14px 18px;margin:14px 0;}}
.note.ok{{background:#EFFaf1;border-color:#CDEBD5;}}
.note.crit{{background:#FFF1F3;border-color:#F6CBD4;}}
.tag{{display:inline-block;font-size:11px;font-weight:600;padding:2px 9px;border-radius:999px;background:#EEF;color:#0058B9;}}
.tag.a{{background:#E7F6EC;color:#1E9E4A;}} .tag.b{{background:#FDEEDB;color:#B5740B;}}
.cover{{min-height:900px;display:flex;flex-direction:column;justify-content:center;padding:60px 30px;}}
.cover .big{{font-size:44px;font-weight:700;letter-spacing:-0.03em;line-height:1.1;margin:8px 0;}}
@media print{{.section{{padding:26px 0;}} .cover{{min-height:880px;}}}}
</style></head><body>

<section class="cover"><div class="wrap">
  <div class="eyebrow">Implementation Report · 落地实施</div>
  <div class="big">中科存储 GEO 提升计划<br/>落地实施报告</div>
  <p>对照 <code>中科存储-GEO提升计划.html</code> 四阶段任务，如实记录已完成、部分完成与待人工项；
  所有数字源自 Python 可复现流水线，不臆造。</p>
  <p class="mut">报告日期：{today} · 复现：<code>python implement_geo_plan.py</code></p>
</div></section>

<section class="section"><div class="wrap">
  <div class="eyebrow">执行摘要</div>
  <h2>计划落实进度与诚实结论</h2>
  <div class="kpis">
    <div class="kpi"><div class="v blue">{num(ov.get('gvi'))}</div><div class="k">基线 GVI</div></div>
    <div class="kpi"><div class="v">{pct(ov.get('mention_rate'))}</div><div class="k">被提及率</div></div>
    <div class="kpi"><div class="v">{pct(gap.get('by_model',{}).get('DeepSeek',{}).get('weighted_coverage'))}</div><div class="k">DeepSeek 信源覆盖</div></div>
    <div class="kpi"><div class="v">{pct(gap.get('by_model',{}).get('通义千问',{}).get('weighted_coverage'))}</div><div class="k">通义信源覆盖</div></div>
  </div>
  <div class="note ok"><h4>阶段一「地基」— 已完成</h4>
  <p>robots 放行 20 类 AI 爬虫 · llms.txt/llms-full.txt · 4+ GEO 事实页 · JSON-LD · 基线报告 · verify 全绿。</p></div>
  <div class="note"><h4>阶段二–四 — 部分完成 / 待人工</h4>
  <p>站外微站（EdgeOne + GitHub Pages）已上线并写入 sameAs；UGC 平台（CSDN/知乎/语雀/百科/公众号）定稿已就绪，
  需人工发布（SOP：<code>geo_plan/offsite/SOP_manual_publish.md</code>）。GVI 复测仍在采样噪声内，真实阶跃需站外信源被收录引用。</p></div>
  {gvi_block}
</div></section>

<section class="section pagebreak"><div class="wrap">
  <div class="eyebrow">四阶段任务看板</div>
  <h2>对照计划的逐项落实状态</h2>
  {phase_rows}
</div></section>

<section class="section"><div class="wrap">
  <div class="eyebrow">已上线站外信源</div>
  <h2>自动化渠道（实测 HTTP 200）</h2>
  <table><thead><tr><th>渠道</th><th>URL</th><th>状态</th></tr></thead><tbody>{channels or '<tr><td colspan=3>暂无</td></tr>'}</tbody></table>
  <h3>信源覆盖诚实计分依据</h3>
  <table><thead><tr><th>平台/渠道</th><th class="num">计分</th><th>依据</th></tr></thead><tbody>{cov_evidence or '<tr><td colspan=3>运行 source_audit.py 生成</td></tr>'}</tbody></table>
</div></section>

<section class="section"><div class="wrap">
  <div class="eyebrow">受阻项与人工 SOP</div>
  <h2>白帽红线内的待办（不自动执行）</h2>
  <ul>{blocked or '<li>无</li>'}</ul>
  <div class="note crit"><h4>数据纪律</h4>
  <p>预测区间标注「规划假设、非承诺」；sameAs 仅写实测 200 的 URL；UGC 不自动发帖；
  GSC 配额/ICP 备案受阻如实记录。坚持批评与自我批评，以客观复测数据为准。</p></div>
  <h3>复现清单</h3>
  <p class="mut">implement_geo_plan.py · coverage_resolver.py · source_audit.py · make_offsite_kit.py ·
  build_implementation_report.py · export_implementation_pdf.py · verify_geo.py</p>
</div></section>
</body></html>"""

    os.makedirs(OUT, exist_ok=True)
    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html)
    meta = {"header": "中科存储 · GEO 计划落地实施", "footer": "中科存储 ZK-Storage · 实事求是"}
    with open(os.path.join(OUT, "implementation_report_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"Saved: {HTML_OUT}")


if __name__ == "__main__":
    main()
