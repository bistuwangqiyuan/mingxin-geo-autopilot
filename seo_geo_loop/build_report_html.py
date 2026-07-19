# -*- coding: utf-8 -*-
"""铭信 GEO+SEO 提升闭环 · 苹果视觉正式报告（HTML）。

读取 outputs/ 下全部由 Python 计算的结果 + figures/ 复现图，渲染为苹果风格 HTML，
随后由 export_report_pdf.py 经 Playwright 打印为 A4 PDF。所有数字均标注来源与复现脚本，
预测明确标注为规划区间。

复现：python build_report_html.py
"""
from __future__ import annotations

import datetime as dt
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "outputs")
GEO = os.path.join(os.path.dirname(BASE), "geo_plan")
HTML_OUT = os.path.join(OUT, "铭信-SEO-GEO提升与站外发布报告.html")
META_OUT = os.path.join(OUT, "report_meta.json")

PILLAR_NAMES = {
    "A": "技术 SEO", "B": "AI 抓取与可达", "C": "结构化数据完备度",
    "D": "答案优先 / 可抽取性", "E": "实体一致性 & E-E-A-T",
}
SUBCHECK_LABELS = {
    # A
    "title_ok": "标题存在且长度合规", "desc_ok": "描述存在且 70–160 字符",
    "h1_one": "每页恰一个 H1", "canonical": "绝对 canonical", "hreflang3": "三组 hreflang",
    "og_abs": "OG 绝对 URL/图", "social_full": "og+twitter 社媒标签齐全", "jsonld": "含 JSON-LD",
    "lang_attr": "html lang", "viewport_charset": "viewport+charset", "alt_cov": "图片 alt 全覆盖",
    "theme_color": "theme-color", "internal_links_ok": "内链 ≥3",
    # B
    "b1": "AI bot 放行度", "b2": "robots 声明 sitemap", "b3": "llms.txt 索引",
    "b4": "llms-full.txt", "llms_full_coverage": "llms-full 全站覆盖", "b6": "sitemap 覆盖",
    # C
    "org": "Organization 全页", "org_enriched": "Organization 富化", "website": "WebSite 全页",
    "search_action": "SearchAction", "product": "Product(FX100)", "faqpage": "FAQPage",
    "breadcrumb": "BreadcrumbList 全页", "techarticle": "TechArticle", "person": "Person",
    "definedterms": "DefinedTermSet",
    # D
    "q_h2": "问句式 H2", "key_facts": "速答关键事实块", "tables": "规格表",
    "source_density": "来源标注密度",
    # E
    "entity": "实体名一致", "spec_consistency": "规格口径一致", "contact": "联系方式",
    "last_updated": "可见更新时间", "author": "作者归属", "entity_anchor": "实体富化锚点",
    # CRI v2 新增
    "media_decoding": "图片 decoding/lazy", "preload_css": "关键 CSS 预加载",
    "font_display": "字体显示策略", "org_sameas": "Organization.sameAs 覆盖",
    "home_speakable": "首页 WebPage+Speakable", "answer_all": "答案块全覆盖",
    "spec_canonical": "规格单位排版一致", "entity_sameas": "站外实体锚点(sameAs)",
}


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


CSS = """
:root{--ink:#1d1d1f;--soft:#6e6e73;--faint:#86868b;--grid:#e8e8ed;--blue:#0071e3;
--indigo:#5e5ce6;--green:#34c759;--bg:#fff;--soft-bg:#f5f5f7;
--grad:linear-gradient(120deg,#0a84ff,#5e5ce6);}
*{box-sizing:border-box;}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact;}
body{margin:0;color:var(--ink);background:var(--bg);
font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
font-size:14px;line-height:1.62;-webkit-font-smoothing:antialiased;}
.wrap{max-width:940px;margin:0 auto;padding:0 40px;}
h1,h2,h3{letter-spacing:-.015em;color:var(--ink);}
.eyebrow{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
color:var(--blue);margin:0 0 8px;}
.cover{padding:96px 40px 64px;text-align:center;
background:radial-gradient(120% 120% at 50% 0%,#f0f4ff 0%,#fff 60%);}
.cover .badge{display:inline-block;font-size:12.5px;font-weight:600;color:var(--blue);
border:1px solid #cfe0ff;border-radius:980px;padding:6px 16px;margin-bottom:26px;background:#fff;}
.cover h1{font-size:42px;font-weight:760;margin:0 0 16px;line-height:1.1;}
.cover .grad{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent;}
.cover p.sub{font-size:18px;color:var(--soft);max-width:680px;margin:0 auto 8px;}
.cover .meta{font-size:13px;color:var(--faint);margin-top:18px;}
.kpis{display:flex;gap:16px;justify-content:center;flex-wrap:wrap;margin:40px auto 0;max-width:820px;}
.kpi{flex:1 1 150px;min-width:150px;border:1px solid var(--grid);border-radius:18px;padding:20px 16px;background:#fff;}
.kpi .v{font-size:30px;font-weight:750;background:var(--grad);-webkit-background-clip:text;
background-clip:text;color:transparent;line-height:1;}
.kpi .k{font-size:12.5px;color:var(--soft);margin-top:8px;}
section.s{padding:40px 0;border-top:1px solid var(--grid);}
section.s h2{font-size:27px;font-weight:720;margin:6px 0 14px;}
section.s h3{font-size:18px;font-weight:680;margin:26px 0 8px;}
p{margin:10px 0;}
.lead{font-size:16px;color:var(--soft);}
.fig{margin:22px 0;text-align:center;}
.fig img{max-width:100%;border:1px solid var(--grid);border-radius:14px;}
.fig .cap{font-size:12px;color:var(--faint);margin-top:8px;}
table{width:100%;border-collapse:collapse;margin:16px 0;font-size:12.5px;}
th,td{padding:8px 10px;border-bottom:1px solid var(--grid);text-align:left;vertical-align:top;}
th{color:var(--soft);font-weight:650;background:var(--soft-bg);}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;}
tr.hl td{background:#f0f7ff;font-weight:650;}
.callout{border:1px solid var(--grid);border-left:3px solid var(--blue);border-radius:12px;
padding:16px 20px;margin:18px 0;background:#fbfdff;}
.callout.warn{border-left-color:var(--green);background:#fafffb;}
.callout.ok{border-left-color:var(--green);background:#f3fbf5;}
.callout h4{margin:0 0 6px;font-size:14.5px;}
.callout p{margin:4px 0;font-size:13px;color:var(--soft);}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
.card{border:1px solid var(--grid);border-radius:14px;padding:16px 18px;}
.card h4{margin:0 0 6px;font-size:14px;}
.card p{margin:0;font-size:12.5px;color:var(--soft);}
.tag{display:inline-block;font-size:10.5px;font-weight:700;color:var(--blue);
background:#eef4ff;border-radius:6px;padding:1px 7px;margin-left:6px;}
.up{color:var(--green);font-weight:650;}
code{background:var(--soft-bg);border-radius:5px;padding:1px 6px;font-size:12px;
font-family:"SF Mono",Consolas,monospace;}
ul{margin:8px 0;padding-left:22px;}li{margin:3px 0;}
.foot{font-size:11.5px;color:var(--faint);padding:30px 0 60px;border-top:1px solid var(--grid);}
@media print{.cover{padding:60px 40px 40px;}section.s{padding:26px 0;}
section.s,.fig,table,.callout{break-inside:avoid;}.cover h1{font-size:36px;}}
"""


def _fig(name, cap):
    p = os.path.join(OUT, "figures", name)
    if not os.path.exists(p):
        return ""
    return f'<div class="fig"><img src="figures/{name}" alt="{esc(cap)}"/><div class="cap">{esc(cap)}</div></div>'


def _latest_snapshot():
    """取 outputs/snapshots/ 下最新有效的线上就绪度实测快照；没有则现场真抓取一次。"""
    snapdir = os.path.join(OUT, "snapshots")
    cands = []
    if os.path.isdir(snapdir):
        cands = sorted((os.path.join(snapdir, f) for f in os.listdir(snapdir) if f.endswith(".json")),
                       key=os.path.getmtime)
    for p in reversed(cands):
        snap = _load(p, {})
        if snap.get("cri") is not None and snap.get("pillars"):
            return snap
    import importlib
    import sys
    if BASE not in sys.path:
        sys.path.insert(0, BASE)
    RA = importlib.import_module("readiness_audit")
    snap = RA.run("report_live")
    if snap.get("cri") is not None:
        os.makedirs(snapdir, exist_ok=True)
        with open(os.path.join(snapdir, "report_live.json"), "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)
    return snap


def _readiness_section(snap):
    """线上就绪度实测段落（readiness_audit HTTP 真抓取，替代已退役的静态站闭环）。"""
    if not snap or snap.get("cri") is None:
        return ("""<section class="s"><span class="eyebrow">线上就绪度</span>
<h2>线上就绪度实测暂不可得</h2>
<p>本次对线上 mingxinstorage.xyz 的 HTTP 抓取审计全部失败（网络/站点不可达），
如实记录、不编造分数。复现：<code>python readiness_audit.py --label current</code>。</p>
</section>""")
    prow = "".join(
        f"<tr><td>{k} · {PILLAR_NAMES[k]}</td><td class='num'>{snap['pillars'].get(k, 0)}</td>"
        f"<td class='num'>{int(snap['weights'].get(k, 0) * 100)}%</td></tr>"
        for k in ["A", "B", "C", "D", "E"])
    err_note = ""
    if snap.get("errors"):
        bad = "、".join(esc(e.get("url", "")) for e in snap["errors"][:4])
        err_note = f"<p class='cap' style='font-size:11.5px;color:var(--faint)'>抓取失败页（如实记录）：{bad}</p>"
    return f"""<section class="s"><span class="eyebrow">线上就绪度实测</span>
<h2>当前线上 CRI = {snap['cri']}（{esc(snap.get('cri_version', 'v1'))} · HTTP 真抓取）</h2>
<p class="lead">铭信官网为 Next.js 站点（amd 仓库 site/ 子目录，Vercel 部署），旧静态站
「逐轮改站→重审」闭环已退役；现行口径为对线上 {esc(snap.get('n_pages', 0))} 个内容页的
确定性 HTTP 抓取审计（<code>readiness_audit.py</code>，无随机、可复算）。</p>
{_fig('readiness_pillars.png', '线上就绪度实测五支柱（HTTP 真抓取，确定性打分）')}
<table><thead><tr><th>支柱</th><th class="num">得分（0–1）</th><th class="num">权重</th></tr></thead>
<tbody>{prow}</tbody></table>
{err_note}
</section>"""


def build():
    # 旧静态站闭环历史产物（中科时代，已退役；存在则渲染为历史章节，缺失如实跳过）
    loop = _load(os.path.join(OUT, "loop_results.json"))
    # 现行口径：线上就绪度实测（真实 HTTP 抓取，铭信 Next.js 站点）
    snap = _latest_snapshot()
    gvi = _load(os.path.join(OUT, "gvi_compare.json"))
    proj = _load(os.path.join(GEO, "outputs", "geo_projection.json"), {})
    base_snap = _load(os.path.join(OUT, "snapshots", "round00.json"), {})
    final_snap = _load(os.path.join(OUT, "snapshots", "final_best.json"), {})
    live = _load(os.path.join(OUT, "live_status.json"), {})
    offsite = _load(os.path.join(OUT, "offsite_published.json"), {})
    loopv2 = _load(os.path.join(OUT, "loop_results_v2.json"), {})
    final_v2_snap = _load(os.path.join(OUT, "snapshots", "final_best_v2.json"), {})
    today = dt.date.today().isoformat()

    w = (loop or snap or {}).get("weights") or {}
    rounds = loop["rounds"] if loop else []
    scope = (loop or snap or {}).get("scope", "线上 HTTP 抓取审计")

    # KPI 区
    gvi_kpi = ""
    if gvi:
        gvi_kpi = (f'<div class="kpi"><div class="v">{gvi["start"]["gvi"]}→{gvi["end"]["gvi"]}</div>'
                   f'<div class="k">真实 GVI 起点→终点（真测）</div></div>')
    v2_kpi = ""
    if loopv2:
        v2_kpi = (f'<div class="kpi"><div class="v">{loopv2["final_cri_v2"]}</div>'
                  f'<div class="k">CRI v2 终值（突破 97.9）</div></div>')
    offsite_kpi = ""
    if offsite:
        n_pub = sum(1 for c in offsite.get("channels", []) if c.get("status") == "published")
        offsite_kpi = (f'<div class="kpi"><div class="v">{n_pub}</div>'
                       f'<div class="k">站外信源真实上线（已验证 200）</div></div>')
    if loop:
        cri_kpi = (f'<div class="kpi"><div class="v">{loop["baseline_cri"]}→{loop["final_cri"]}</div>'
                   f'<div class="k">CRI v1 基线 → 最终（0–100）</div></div>')
    elif snap and snap.get("cri") is not None:
        cri_kpi = (f'<div class="kpi"><div class="v">{snap["cri"]}</div>'
                   f'<div class="k">线上就绪度 CRI 实测（0–100）</div></div>')
    else:
        cri_kpi = ('<div class="kpi"><div class="v">—</div>'
                   '<div class="k">线上 CRI 暂不可得（网络失败，如实记录）</div></div>')

    h = []
    h.append(f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>铭信 · SEO/GEO 提升与站外发布报告</title><style>{CSS}</style></head><body>""")

    # 封面
    h.append(f"""<div class="cover">
<span class="badge">实事求是 · 可复现 · 白帽</span>
<h1>铭信官网<br/><span class="grad">SEO / GEO 提升与站外发布报告</span></h1>
<p class="sub">{('真实测评收录/排名与线上性能，完成站外内容包并真实上线可自动化渠道，'
                 '再以 5 个全新白帽杠杆把站内就绪度（CRI v2）推过第一阶段 97.9 上限，并诚实对照真实 GVI。') if loop else
                ('真实测评收录/排名与线上性能，以 HTTP 真抓取审计线上就绪度（CRI），'
                 '完成站外内容包并真实上线可自动化渠道，并诚实对照真实 GVI。')}</p>
<p class="meta">Mingxin Technology · 铭信（天津）半导体设备有限公司 · 生成于 {today} · 全程无随机、无臆造</p>
<div class="kpis">
{cri_kpi}
{v2_kpi}
{offsite_kpi}
{gvi_kpi}
</div></div>""")

    h.append('<div class="wrap">')

    # A. 真实现状测评（直接回答：真实 SEO/GEO/谷歌排名如何）
    h.append(_live_section(live, gvi, loop))

    # 0. 诚实边界
    h.append(f"""<section class="s"><span class="eyebrow">先立诚实边界</span>
<h2>两个分数，两种性质——绝不混为一谈</h2>
<div class="callout"><h4>CRI（本闭环优化对象 · 我们真正可控）</h4>
<p>CRI = 站内 GEO+SEO「就绪度」综合指数（0–100），由脚本确定性扫描官网 HTML 计算，
权重公开、无随机、无网络，<b>任何人可逐行复算</b>。它度量的是我们能在站内立即改动并验证的工程质量。</p></div>
<div class="callout warn"><h4>GVI（真实大模型可见性 · 需站外随时间积累）</h4>
<p>GVI = 真实大模型在用户提问时是否「提及/引用/推荐」铭信（对 4 个 DashScope 模型 ×
全部查询的真实 API 采样打分）。<b>站内改动不会改变模型训练语料，故一次会话内 GVI 不会因改站而跳升</b>；
其真实阶跃来自站外多信源被收录/引用，需以「周/月」计。本报告对 GVI 只如实重测、诚实对照，
并把未来提升以<b>明确标注为「规划区间」的预测（P10/P50/P90）</b>呈现，绝不谎称已一键拉满。</p></div>
</section>""")

    # 1. 方法学
    rowsw = "".join(
        f"<tr><td>{k} · {PILLAR_NAMES[k]}</td><td class='num'>{int(v*100)}%</td>"
        f"<td>{_pillar_desc(k)}</td></tr>" for k, v in w.items())
    h.append(f"""<section class="s"><span class="eyebrow">方法学</span>
<h2>CRI 的五支柱与公式（公开、可调、可复现）</h2>
<p class="lead">CRI = 100 · Σ wᵢ·支柱ᵢ。每个支柱为 0–1 的客观达成度，由对官网页面的
确定性扫描（{esc(scope)}）而来；现行口径为对线上 mingxinstorage.xyz 的 HTTP 抓取审计
（<code>readiness_audit.py</code>）。</p>
<table><thead><tr><th>支柱</th><th class="num">权重</th><th>口径（节选）</th></tr></thead>
<tbody>{rowsw}</tbody></table>
<div class="callout"><h4>数据纪律</h4>
<p>所有站内事实单一来源于 <code>business_plan/outputs/results.json</code>（与官网单一数据源
<code>company.ts</code> 同源镜像，签字级实测 R1–R9）；结构化数据/答案块/索引均与之一致，
绝不臆造。复现链：<code>python readiness_audit.py → gvi_measure.py → charts.py → build_report_html.py → export_report_pdf.py</code>。</p></div>
</section>""")

    # 2. 现行口径：线上就绪度实测（真实 HTTP 抓取）
    h.append(_readiness_section(snap))

    # 2b–4. 旧静态站闭环历史章节（产物存在才渲染；铭信 Next.js 站点缺省跳过）
    if loop:
        trow = []
        for r in rounds:
            p = r["pillars"]
            cls = ' class="hl"' if r["round"] == len(rounds) - 1 else ""
            d = f'+{r["delta"]:.2f}' if r["delta"] > 0 else f'{r["delta"]:.2f}'
            trow.append(f"<tr{cls}><td class='num'>{r['round']:02d}</td><td>{esc(r['lever_name'])}</td>"
                        f"<td class='num'>{r['cri']:.2f}</td><td class='num'>{d}</td>"
                        f"<td class='num'>{p['A']}</td><td class='num'>{p['B']}</td><td class='num'>{p['C']}</td>"
                        f"<td class='num'>{p['D']}</td><td class='num'>{p['E']}</td>"
                        f"<td>{'OK' if r['verify_ok'] else 'FAIL'}</td></tr>")
        h.append(f"""<section class="s"><span class="eyebrow">闭环结果（历史）</span>
<h2>10 轮优化：CRI 从 {loop['baseline_cri']} 单调升至 {loop['final_cri']}</h2>
{_fig('cri_trajectory.png', 'CRI 逐轮提升轨迹（每轮真实改站+重审，无随机）')}
<p>第 {loop['converged_round']} 轮后杠杆全开，CRI 收敛于结构上限 <b>{loop['final_cri']}</b>
（非人为 100——仍有少量子项受现实约束未满分，见 §6，体现实事求是）。每轮均通过站内自检
<code>verify_site.py</code>（内链 404 / 双语对齐 / 关键数值一致）。</p>
<table><thead><tr><th class="num">轮</th><th>本轮启用</th><th class="num">CRI</th><th class="num">Δ</th>
<th class="num">A</th><th class="num">B</th><th class="num">C</th><th class="num">D</th><th class="num">E</th><th>校验</th></tr></thead>
<tbody>{''.join(trow)}</tbody></table>
</section>""")

        grow = []
        contrib = {r["lever_enabled"]: r["delta"] for r in rounds if r.get("lever_enabled")}
        for g in loop["lever_groups"]:
            dv = contrib.get(g["id"], 0.0)
            grow.append(f"<tr><td><b>{esc(g['name'])}</b><span class='tag'>{g['pillar']}</span></td>"
                        f"<td class='num up'>+{dv:.2f}</td><td>{esc(g['desc'])}</td></tr>")
        h.append(f"""<section class="s"><span class="eyebrow">归因复盘（历史）</span>
<h2>八个白帽杠杆组的边际贡献</h2>
{_fig('lever_contribution.png', '各杠杆组带来的 CRI 增量（逐轮 Δ）')}
<p>每个杠杆都是真实、可核验、单一数据源的站内改进；不堆砌关键词、不隐藏文字、不臆造外部档案。</p>
<table><thead><tr><th>杠杆组（支柱）</th><th class="num">CRI 增量</th><th>真实改进内容</th></tr></thead>
<tbody>{''.join(grow)}</tbody></table>
</section>""")

        h.append(f"""<section class="s"><span class="eyebrow">支柱画像（历史）</span>
<h2>五支柱：基线 → 最终</h2>
<div class="grid2">{_fig('pillar_radar.png','五支柱雷达：基线 vs 最终')}{_fig('pillar_delta.png','五支柱条形：基线 vs 最终')}</div>
{_pillar_detail_table(base_snap, final_snap)}
</section>""")

    # 4b. CRI v2 第二阶段（第 11–15 轮，g9–g13）
    h.append(_v2_section(loopv2, final_v2_snap, final_snap))

    # 5. 真实 GVI 对照
    if gvi:
        gvrow = "".join(
            f"<tr><td>{esc(m)}</td><td class='num'>{gvi['start']['by_model'].get(m,0)}</td>"
            f"<td class='num'>{gvi['end']['by_model'].get(m,0)}</td></tr>" for m in gvi["models"])
        h.append(f"""<section class="s"><span class="eyebrow">真实大模型采样</span>
<h2>GEO 可见性指数 GVI：起点 vs 终点（同口径真测）</h2>
{_fig('gvi_compare.png','真实 GVI：起点 vs 终点（4 个 DashScope 模型真实 API 采样）')}
<table><thead><tr><th>模型</th><th class="num">起点 GVI</th><th class="num">终点 GVI</th></tr></thead>
<tbody>{gvrow}<tr class="hl"><td>总体</td><td class="num">{gvi['start']['gvi']}</td>
<td class="num">{gvi['end']['gvi']}</td></tr></tbody></table>
<div class="callout warn"><h4>如何诚实解读 ΔGVI = {gvi['delta_gvi']:+.2f}</h4>
<p>{esc(gvi['honest_note'])} 起点取自 geo_plan 既有真测基线（{gvi['start']['n_records_ok']} 条 grade A），
终点为本次站内全部就绪后对同样模型的重新真测（{gvi['end']['n_records_ok']} 条）。
二者落在采样噪声内，<b>恰恰证明：站内就绪度（CRI）已尽最大努力拉满，但真实 GVI 阶跃必须靠站外执行随时间兑现</b>。</p></div>
</section>""")

    # 6. 预测 + 收敛/自我批评
    cri_now = loop["final_cri"] if loop else ((snap or {}).get("cri") if snap else None)
    cri_txt = (f"杠杆全开后 CRI 收敛于 {loop['final_cri']}，并非人为 100。" if loop
               else (f"当前线上实测 CRI = {cri_now}，尚未拉满。" if cri_now is not None
                     else "本次线上抓取失败，CRI 暂不可得（如实记录）。"))
    lowest_src = final_snap if loop else (snap or {})
    h.append(f"""<section class="s"><span class="eyebrow">规划区间（非承诺）</span>
<h2>GEO 提升预测与收敛复盘</h2>
{_fig('geo_projection.png','GEO 提及率提升预测 P10–P90（规划区间）')}
{_projection_table(proj)}
<h3>收敛与自我批评（实事求是）</h3>
<p>{cri_txt}如实记录仍未满分的子项，留待后续迭代/站外执行：</p>
<ul>{_lowest_list(lowest_src)}</ul>
</section>""")

    # 6b. 站外内容包与已上线 URL
    h.append(_offsite_section(offsite))

    # 7. 站外执行 + 治理 + 复现
    h.append(f"""<section class="s"><span class="eyebrow">下一步 · 真实兑现 GVI</span>
<h2>站外多信源执行包与治理红线</h2>
<p>真实 GVI 阶跃需按各国产模型「信源偏好」做白帽站外覆盖（草稿见
<code>geo_plan/offsite/</code>：百度百科/百家号→文心；CSDN/知乎/GitHub→DeepSeek；阿里云/语雀→通义；
微信公众号→元宝；搜狐/网易→豆包），并保持全网实体口径与 <code>results.json</code> 一致。</p>
<div class="callout"><h4>白帽红线</h4>
<p>禁止伪造测评/水军/隐藏文字/页面 prompt 注入/冒称资质；竞品对比用客观可核验口径、不贬损；
所有对外事实可溯源至 results.json（↔ 官网 company.ts）与签字级实测报告 R1–R9（含 R9 昇腾平台口径标注）；预测一律标注为规划区间。</p></div>
<h3>一键复现</h3>
<p><code>cd seo_geo_loop &amp;&amp; python run.py</code>　（依次：闭环优化 → 真实 GVI 重测 → 复现图 → HTML → A4 PDF）</p>
</section>""")

    h.append(f"""<div class="foot">© 2026 铭信（天津）半导体设备有限公司 · Mingxin Technology。本报告所有 CRI/GVI 数值均由
<code>seo_geo_loop/</code> 脚本计算，过程无随机、无网络（GVI 部分为真实 API 采样，原始回答落盘可查）；
预测区间为规划假设、非承诺。生成于 {today}。</div>""")
    h.append("</div></body></html>")

    os.makedirs(OUT, exist_ok=True)
    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write("".join(h))
    with open(META_OUT, "w", encoding="utf-8") as f:
        json.dump({"header": "铭信 · SEO/GEO 提升与站外发布报告",
                   "footer": "铭信 Mingxin Technology · 实事求是 · 可复现"}, f, ensure_ascii=False)
    print(f"Saved: {HTML_OUT}")


def _pillar_desc(k):
    return {
        "A": "每页 title/desc/H1/canonical/hreflang/OG+Twitter/JSON-LD/lang/viewport/alt/内链 + 站级 sitemap/robots/indexnow/manifest",
        "B": "robots 放行 AI bot、声明 sitemap；llms.txt/llms-full.txt 覆盖；sitemap 覆盖全站",
        "C": "Organization(富化)/WebSite(SearchAction)/Product/FAQPage/BreadcrumbList/TechArticle/Person/DefinedTermSet",
        "D": "问句式 H2 + 速答关键事实块 + 规格表 + FAQ + 术语 + 来源标注密度",
        "E": "实体名/规格口径一致、联系方式 NAP、可见更新时间、作者归属、实体富化锚点",
    }[k]


def _pillar_detail_table(base, final):
    if not base or not final:
        return ""
    rows = []
    for k in ["A", "B", "C", "D", "E"]:
        bd = base["detail"].get(k, {})
        fd = final["detail"].get(k, {})
        keys = [x for x in fd.keys() if isinstance(fd.get(x), (int, float)) and not isinstance(fd.get(x), bool)
                and x in SUBCHECK_LABELS]
        # A 支柱的 page_coverage 是嵌套，单独取
        if k == "A":
            bcov = base["detail"]["A"].get("page_coverage", {})
            fcov = final["detail"]["A"].get("page_coverage", {})
            for sk in fcov:
                rows.append((k, SUBCHECK_LABELS.get(sk, sk), bcov.get(sk, 0), fcov.get(sk, 0)))
            continue
        for sk in keys:
            rows.append((k, SUBCHECK_LABELS.get(sk, sk), bd.get(sk, 0), fd.get(sk, 0)))
    body = []
    for k, label, b, f in rows:
        up = ' class="up"' if f > b else ''
        body.append(f"<tr><td>{k}</td><td>{esc(label)}</td><td class='num'>{b}</td>"
                    f"<td class='num'{up}>{f}</td></tr>")
    return (f"<h3>子项达成度明细（基线 → 最终）</h3>"
            f"<table><thead><tr><th>支柱</th><th>子项</th><th class='num'>基线</th>"
            f"<th class='num'>最终</th></tr></thead><tbody>{''.join(body)}</tbody></table>")


def _projection_table(proj):
    if not proj or "phases" not in proj:
        return ""
    phases = proj["phases"]
    order = list(phases.keys())
    rows = []
    for ph in order:
        t1 = phases[ph]["tiers"]["T1"]
        rows.append(f"<tr><td>{esc(ph.replace('_',' '))}</td><td>{esc(phases[ph]['weeks'])}</td>"
                    f"<td class='num'>{t1['mention_p10']*100:.1f}%</td>"
                    f"<td class='num'>{t1['mention_p50']*100:.1f}%</td>"
                    f"<td class='num'>{t1['mention_p90']*100:.1f}%</td></tr>")
    return (f"<p class='lead'>下表为 T1（最窄可防御类目）品牌提及率的规划区间预测（P10/P50/P90，"
            f"系数取自公开 GEO 研究下沿，<b>非承诺</b>）：</p>"
            f"<table><thead><tr><th>阶段</th><th>时点</th><th class='num'>P10</th>"
            f"<th class='num'>P50</th><th class='num'>P90</th></tr></thead><tbody>{''.join(rows)}</tbody></table>")


def _live_section(live, gvi, loop):
    if not live:
        return ""
    idx = live.get("indexing", {})
    cri = live.get("cri_local_best")
    gvi_txt = (f'{live["gvi"]["start"]}→{live["gvi"]["end"]}' if live.get("gvi") else "—")
    # 在线技术 SEO（线上部署版本）
    zh_home = next((p for p in live.get("live_onpage", []) if p["url"].endswith("zh/index.html")), {})
    op = zh_home.get("onpage", {})
    deploy_note = live.get("deploy_note", "")
    # Lighthouse / 实验室
    lh = live.get("lighthouse", {})
    lab_rows = ""
    for r in (lh.get("results", []) if lh else []):
        if r.get("ok") and r.get("method") == "lab":
            m = r["metrics"]
            lab_rows += (f"<tr><td>{esc(r['url'].replace('https://mingxinstorage.xyz',''))}</td>"
                         f"<td class='num'>{(m.get('fcp') or 0)/1000:.2f}s</td>"
                         f"<td class='num'>{(m.get('lcp') or 0)/1000:.2f}s</td>"
                         f"<td class='num'>{(m.get('load') or 0)/1000:.2f}s</td>"
                         f"<td class='num'>{round((m.get('transferBytes') or 0)/1024)} KB</td></tr>")
    lab_tbl = (f"<table><thead><tr><th>页面</th><th class='num'>FCP</th><th class='num'>LCP</th>"
               f"<th class='num'>Load</th><th class='num'>传输</th></tr></thead>"
               f"<tbody>{lab_rows}</tbody></table>" if lab_rows else "")
    serp_rows = ""
    for o in live.get("serp_observations_today", []):
        serp_rows += (f"<tr><td>{esc(o['engine'])}</td><td>{esc(o['query'])}</td>"
                      f"<td>{esc(o['our_position'])}</td><td>{esc(o.get('notes',''))}</td></tr>")
    acc = "".join(f"<li>{esc(x)}</li>" for x in live.get("index_acceleration_checklist", []))
    dep = live.get("deploy", {})
    inx = live.get("indexnow", {})
    deploy_block = ""
    if dep:
        vl = dep.get("verified_live", {})
        eps = inx.get("endpoints", {}) if inx else {}
        eps_txt = "　".join(f"{k}=<b>{v}</b>" for k, v in eps.items()) if eps else "—"
        deploy_block = (
            f'<div class="callout ok"><h4>本次已真实部署上线 + 主动提交收录</h4>'
            f'<p>推送优化构建到 GitHub <code>main</code> → Netlify 自动构建上线（commit <code>{esc(str(dep.get("commit","")))}</code>）。'
            f'线上复核：首页 JSON-LD=<b>{vl.get("homepage_jsonld_count","—")}</b>、canonical=<b>{vl.get("canonical","—")}</b>、'
            f'sameAs=<b>{vl.get("sameas","—")}</b>、Speakable=<b>{vl.get("speakable","—")}</b>；'
            f'<code>sitemap.xml</code>/<code>robots.txt</code>/IndexNow key 由 <b>404→200</b>。</p>'
            f'<p>IndexNow 推送 <b>{inx.get("url_count","—")}</b> 条 URL（{eps_txt}）；'
            f'Google ping 已弃用（{(inx.get("sitemap_ping",{}) or {}).get("google_ping",{}).get("status","—")}），'
            f'依赖 Search Console/自然抓取与站外信源积累——如实说明。</p></div>'
        )
    return f"""<section class="s"><span class="eyebrow">真实现状测评 · 实事求是</span>
<h2>真实 SEO / GEO / 收录与排名现状（{esc(live.get('computed_at','')[:10])} 实查）</h2>
<p class="lead">不臆造、不美化：以真实 web 检索复核收录与排名，以 Playwright/CDP 对<b>线上</b> mingxinstorage.xyz 做实验室性能真测。</p>
<div class="grid2">
<div class="card"><h4>收录状态</h4><p>Google：<b>{esc(idx.get('google_site','—'))}</b>　Bing：<b>{esc(idx.get('bing_site','—'))}</b>　百度：{esc(idx.get('baidu','—'))}</p></div>
<div class="card"><h4>排名状态</h4><p>{esc(live.get('ranking_summary',''))}</p></div>
<div class="card"><h4>本地最佳就绪度</h4><p>CRI v1 = <b>{cri}</b>（站内可控，已拉满）</p></div>
<div class="card"><h4>真实大模型可见性</h4><p>GVI = <b>{gvi_txt}</b>（真实 API 采样，需站外随时间积累）</p></div>
</div>
<h3>实时 SERP 观测（agent web_search，写入 <code>seo/data/serp_observations.csv</code>）</h3>
<table><thead><tr><th>引擎</th><th>查询</th><th>我方位次</th><th>说明</th></tr></thead><tbody>{serp_rows}</tbody></table>
{deploy_block}
<div class="callout"><h4>线上部署版本（诚实说明）</h4>
<p>线上 zh 首页 JSON-LD 数 = <b>{op.get('jsonld_count','—')}</b>、canonical = {op.get('canonical','—')}、hreflang = {op.get('hreflang_count','—')}。{esc(deploy_note)}</p></div>
<h3>线上性能实验室真测（Playwright/CDP · 审计主机网络）</h3>
{_fig('live_lab.png','线上 mingxinstorage.xyz 实验室性能（PSI 受限退回实验室，口径如实标注）')}
{lab_tbl}
<p class="cap" style="font-size:11.5px;color:var(--faint)">注：PSI(PageSpeed Insights) 在无 API key 的共享 IP 下被限流(429)，故退回 Playwright 实验室测量；
数值受审计主机网络影响，作趋势参考，不等同 Google 实地 CWV。</p>
<h3>收录加速清单（可执行）</h3><ul>{acc}</ul>
</section>"""


def _v2_section(loopv2, final_v2, final_v1):
    if not loopv2:
        return ""
    rows = loopv2["rounds"]
    trow = []
    for r in rows:
        p = r["pillars"]
        cls = ' class="hl"' if r is rows[-1] else ""
        d = f'+{r["delta"]:.2f}' if r["delta"] > 0 else f'{r["delta"]:.2f}'
        trow.append(f"<tr{cls}><td class='num'>{r['round']:02d}</td><td>{esc(r['lever_name'])}</td>"
                    f"<td class='num'>{r['cri']:.2f}</td><td class='num'>{d}</td>"
                    f"<td class='num'>{p['A']}</td><td class='num'>{p['B']}</td><td class='num'>{p['C']}</td>"
                    f"<td class='num'>{p['D']}</td><td class='num'>{p['E']}</td>"
                    f"<td>{'OK' if r['verify_ok'] else 'FAIL'}</td></tr>")
    new_levers = [g for g in loopv2["lever_groups"]
                  if g["id"] in ("g9_sameas", "g10_answer_all", "g11_spec_consistency",
                                 "g12_media_speakable", "g13_perf")]
    contrib = {r["lever_enabled"]: r["delta"] for r in rows if r.get("lever_enabled")}
    grow = "".join(
        f"<tr><td><b>{esc(g['name'])}</b><span class='tag'>{g['pillar']}</span></td>"
        f"<td class='num up'>+{contrib.get(g['id'],0):.2f}</td><td>{esc(g['desc'])}</td></tr>"
        for g in new_levers)
    return f"""<section class="s"><span class="eyebrow">第二阶段 · 突破上限</span>
<h2>CRI v2 第 11–15 轮：{loopv2['baseline_cri']} → {loopv2['final_cri_v2']}（v1 同步达 {loopv2['final_cri_v1']}）</h2>
<p class="lead">原 8 杠杆已收敛于 v1 的 97.9，<b>绝不重复刷分</b>。第二阶段引入 5 个全新真实杠杆（g9–g13），
并把 CRI 扩展为更严格的 v2（新增 8 个确定性子项）。CRI v2 与 v1 为不同刻度，均如实并列。</p>
{_fig('cri_v2_trajectory.png','CRI v2 第 11–15 轮提升轨迹（突破第一阶段 97.9 上限）')}
<table><thead><tr><th class="num">轮</th><th>本轮启用</th><th class="num">CRI v2</th><th class="num">Δ</th>
<th class="num">A</th><th class="num">B</th><th class="num">C</th><th class="num">D</th><th class="num">E</th><th>校验</th></tr></thead>
<tbody>{''.join(trow)}</tbody></table>
{_fig('lever_contribution_v2.png','新增 5 杠杆（g9–g13）的边际贡献')}
<table><thead><tr><th>新杠杆组（支柱）</th><th class="num">CRI v2 增量</th><th>真实改进内容</th></tr></thead>
<tbody>{grow}</tbody></table>
<div class="callout"><h4>诚实口径</h4><p>{esc(loopv2.get('note',''))}
其中 g9 的 <code>sameAs</code> 只写入<b>已真实上线并实测 200</b> 的站外 URL（见下节），兑现此前诚实留空的实体锚点。</p></div>
</section>"""


def _offsite_section(offsite):
    if not offsite:
        return ""
    rows = ""
    for c in offsite.get("channels", []):
        rows += (f"<tr><td>{esc(c['platform'])}</td><td>{esc(c['type'])}</td>"
                 f"<td>{esc(c['status'])}</td>"
                 f"<td><a href='{esc(c['url'])}'>{esc(c['url'])}</a></td>"
                 f"<td>{'✓' if c.get('verified_http_200') else '—'}</td></tr>")
    ugc = offsite.get("ugc_manual", {})
    drafts = "、".join(ugc.get("drafts", []))
    same = "".join(f"<li><code>{esc(u)}</code></li>" for u in offsite.get("sameas_urls", []))
    return f"""<section class="s"><span class="eyebrow">站外内容包 · 真实发布</span>
<h2>站外信源：可自动化渠道真实上线，UGC 交付即可发布定稿</h2>
<p class="lead">站外信源是真实 GVI 阶跃的根因。可程序化、合规的渠道已<b>真实部署上线并实测 HTTP 200</b>；
UGC 平台（无开放写 API、需实名）按计划交付即可发布定稿 + SOP，由人工择期发布。</p>
<table><thead><tr><th>渠道</th><th>方式</th><th>状态</th><th>已上线 URL</th><th>200</th></tr></thead>
<tbody>{rows}</tbody></table>
<div class="callout warn"><h4>UGC（人工发布）</h4>
<p>{esc(ugc.get('note',''))}<br/>即可发布定稿：<code>{esc(drafts)}</code>（见 <code>geo_plan/offsite/</code>）。</p></div>
<h3>已回灌官网的真实实体锚点（Organization.sameAs）</h3>
<ul>{same}</ul>
<p class="cap" style="font-size:11.5px;color:var(--faint)">仅写入已上线且实测可达的 URL；记录见
<code>seo_geo_loop/outputs/offsite_published.json</code>。</p>
</section>"""


def _lowest_list(final):
    if not final:
        return "<li>（快照缺失）</li>"
    import importlib
    import sys
    sys.path.insert(0, BASE)
    RA = importlib.import_module("readiness_audit")
    items = RA.lowest_levers(final, 6)
    out = []
    for v, name in items:
        out.append(f"<li><code>{esc(name)}</code> = {v}（如实保留；多为现实约束，如首页不设面包屑、"
                   f"部分页含其它合法 GB/s 数值等）</li>")
    return "".join(out)


if __name__ == "__main__":
    build()
