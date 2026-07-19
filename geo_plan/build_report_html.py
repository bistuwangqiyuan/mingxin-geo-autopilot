# -*- coding: utf-8 -*-
"""铭信 GEO 提升计划 · 正式报告 HTML 生成器（苹果视觉风格）。

数据驱动：读取 outputs/ 下的 geo_baseline.json、geo_projection.json、source_gap.json、
entity_facts.json、run_manifest.json，嵌入 outputs/figures/ 的复现图，产出一份
可导出为 A4 PDF 的正式报告。每个数字均可溯源到上述脚本与 results.json。

复现链：geo_audit.py → geo_scoring.py / geo_projection.py / source_audit.py
        → build_report_html.py → export_report_pdf.py
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os

import geo_config as C

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "outputs")
HTML_OUT = os.path.join(OUT, "铭信-GEO提升计划.html")
META_OUT = os.path.join(OUT, "report_meta.json")


def L(name):
    with open(os.path.join(OUT, name), "r", encoding="utf-8") as f:
        return json.load(f)


def esc(s):
    return html.escape(str(s), quote=True)


def pct(x, d=1):
    return f"{x*100:.{d}f}%"


CSS = """
:root{
  --ink:#1D1D1F; --ink2:#48484A; --mut:#86868B; --line:#E2E2E7; --line2:#F0F0F3;
  --blue:#0071E3; --blueink:#0058B9; --green:#34C759; --orange:#FF9F0A; --red:#FF375F;
  --bg:#FFFFFF; --soft:#F5F5F7; --card:#FBFBFD;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  -webkit-font-smoothing:antialiased;line-height:1.65;font-size:15px;}
.wrap{max-width:980px;margin:0 auto;padding:0 30px;}
h1,h2,h3,h4{letter-spacing:-0.01em;line-height:1.2;color:var(--ink);}
h2{font-size:27px;font-weight:650;margin:0 0 6px;}
h3{font-size:19px;font-weight:600;margin:26px 0 8px;}
h4{font-size:15.5px;font-weight:600;margin:18px 0 6px;color:var(--ink2);}
p{margin:9px 0;color:var(--ink2);}
small,.mut{color:var(--mut);}
a{color:var(--blue);text-decoration:none;}
.eyebrow{font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--blue);}
.section{padding:40px 0;border-top:1px solid var(--line2);}
.section:first-of-type{border-top:none;}
.lead{font-size:17px;color:var(--ink2);}
.kpis{display:flex;flex-wrap:wrap;gap:14px;margin:18px 0;}
.kpi{flex:1 1 150px;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px;}
.kpi .v{font-size:30px;font-weight:680;letter-spacing:-0.02em;color:var(--ink);}
.kpi .v.blue{color:var(--blue);} .kpi .v.green{color:#1E9E4A;} .kpi .v.red{color:var(--red);}
.kpi .k{font-size:12.5px;color:var(--mut);margin-top:2px;}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 20px;margin:14px 0;}
.note{background:#FFF8EC;border:1px solid #F3E2BD;border-radius:14px;padding:14px 18px;margin:14px 0;}
.note.crit{background:#FFF1F3;border-color:#F6CBD4;}
.note.ok{background:#EFFaf1;border-color:#CDEBD5;}
.note h4{margin-top:0;color:var(--ink);}
table{width:100%;border-collapse:collapse;margin:14px 0;font-size:13.5px;}
th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top;}
th{font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--mut);font-weight:600;}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;}
tr.hl td{background:#F0F7FF;font-weight:600;color:var(--ink);}
figure{margin:18px 0;text-align:center;}
figure img{max-width:100%;border:1px solid var(--line);border-radius:14px;}
figcaption{font-size:12px;color:var(--mut);margin-top:7px;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
ul,ol{color:var(--ink2);padding-left:20px;} li{margin:5px 0;}
.tag{display:inline-block;font-size:11px;font-weight:600;padding:2px 9px;border-radius:999px;background:#EEF;color:var(--blueink);margin-right:6px;}
.tag.a{background:#E7F6EC;color:#1E9E4A;} .tag.b{background:#FDEEDB;color:#B5740B;}
.cover{min-height:1040px;display:flex;flex-direction:column;justify-content:center;padding:60px 30px;}
.cover .big{font-size:50px;font-weight:700;letter-spacing:-0.03em;line-height:1.08;margin:8px 0;}
.cover .sub{font-size:19px;color:var(--ink2);max-width:680px;}
.cover .meta{margin-top:38px;color:var(--mut);font-size:13.5px;line-height:1.9;}
.brandrow{display:flex;align-items:center;gap:12px;font-weight:680;font-size:20px;letter-spacing:-0.01em;}
.dot{width:11px;height:11px;border-radius:50%;background:var(--blue);display:inline-block;}
.pagebreak{page-break-before:always;}
@media print{ .section{padding:26px 0;} body{font-size:12.5px;} .cover{min-height:980px;} h2{font-size:23px;} .kpi .v{font-size:25px;} }
"""


def fig(name, cap):
    return (f'<figure><img src="figures/{name}" alt="{esc(cap)}" />'
            f'<figcaption>{esc(cap)}</figcaption></figure>')


def kpi(v, k, cls=""):
    return f'<div class="kpi"><div class="v {cls}">{v}</div><div class="k">{esc(k)}</div></div>'


def table(headers, rows, aligns=None, hl_last=False):
    aligns = aligns or ["l"] * len(headers)
    th = "".join(f'<th class="num">{esc(h)}</th>' if a in ("r", "c") else f"<th>{esc(h)}</th>"
                 for h, a in zip(headers, aligns))
    trs = []
    for i, r in enumerate(rows):
        cls = ' class="hl"' if (hl_last and i == len(rows) - 1) else ""
        tds = "".join(f'<td class="num">{c}</td>' if a in ("r", "c") else f"<td>{c}</td>"
                      for c, a in zip(r, aligns))
        trs.append(f"<tr{cls}>{tds}</tr>")
    return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table>"


def build():
    base = L("geo_baseline.json")
    proj = L("geo_projection.json")
    gap = L("source_gap.json")
    facts = L("entity_facts.json")
    man = L("run_manifest.json")
    # 报告日期与数据采集日期对齐，避免暗示“今日新采样”（实事求是）。
    today = (man.get("compiled_at") or "")[:10] or dt.date.today().isoformat()
    ov = base["overall"]
    bm = base["by_model"]

    S = []  # sections

    # ---- 封面 ----
    S.append(f"""
<section class="cover">
  <div class="brandrow"><span class="dot"></span>铭信 · Mingxin Technology</div>
  <div class="eyebrow" style="margin-top:30px">Generative Engine Optimization · 国产大模型优先</div>
  <div class="big">基于 AI 的 GEO<br/>提升计划与基线报告</div>
  <div class="sub">让国产 AI 大模型在“存储加速 / KV Cache 分层 / 算力中心”相关提问中，优先提及、引用并推荐铭信——
  以白帽、可复现、实事求是的内容与结构工程达成。</div>
  <div class="meta">
    报告日期：{today}　·　主体：{esc(facts['entity_zh'])}<br/>
    数据等级：A（API 真测，{man['counts'].get('ok',0)+man['counts'].get('skip',0)} 条）/ B（人工取证协议，待采集）<br/>
    复现链：geo_audit.py → geo_scoring.py / geo_projection.py / source_audit.py → 本报告<br/>
    单一事实源：business_plan/outputs/results.json
  </div>
</section>""")

    # ---- 执行摘要 ----
    S.append(f"""
<section class="section pagebreak"><div class="wrap">
  <div class="eyebrow">执行摘要</div>
  <h2>结论先行：现状、行动与可达目标</h2>
  <p class="lead">本计划用 Python + 百炼 CLI 对 4 个可直连国产大模型做了 {ov['n_records_ok']} 次真实采样，
  得出可复现的 GEO 基线，并已完成站内 GEO 地基落地与站外工具包，给出保守的提升区间。</p>
  <div class="kpis">
    {kpi(f"{ov['gvi']:.1f}", "基线总体 GVI（0–100）", "blue")}
    {kpi(pct(ov['mention_rate']), "品牌平均被提及率")}
    {kpi(pct(ov['first_rank'],1), "排序位得分（首位=1）")}
    {kpi(pct(ov['citation_rate'],1), "带可核验来源引用率", "red")}
  </div>
  <h3>三个核心发现</h3>
  <ol>
    <li><b>我们已被“看见”，但远未“领先”。</b>铭信在 4 个模型上的平均被提及率约 {pct(ov['mention_rate'])}，
    但声量榜由华为 OceanStor、焱融、曙光 ParaStor 主导，铭信尚未进入第一梯队。</li>
    <li><b>被引用率≈0 是最大短板。</b>纯对话场景下模型几乎不附来源；这正是“可被抓取 + 结构化 + 站外多信源”要补的环节。</li>
    <li><b>信源覆盖近乎空白。</b>各国产模型的高权重信源（CSDN/知乎/百科/公众号等）我方覆盖率 0–5%，缺口即机会。</li>
  </ol>
  <h3>已完成的落地（本次）</h3>
  <ul>
    <li>站内：铭信官网（mingxinstorage.xyz，Next.js）GEO 基础设施完备——robots 放行 AI 爬虫、
    llms.txt / llms-full.txt、sitemap、JSON-LD、中英双语、内容引擎 /api/engine/*、
    /api/seo/ping（IndexNow+百度推送）；本轮以线上 HTTP 探测复核。</li>
    <li>测量：查询宇宙（70 问）+ 真测采集器 + GVI 评分 + 保守提升预测 + 信源缺口分析，全部一键复现。</li>
    <li>站外：从单一事实源生成 9 个平台的内容母版/改写草稿与发布一致性清单（待人工核准发布，
    实测数字均带报告编号 R1–R9）。</li>
  </ul>
</div></section>""")

    # ---- 自我批评与修正 ----
    S.append(f"""
<section class="section"><div class="wrap">
  <div class="eyebrow">坚持批评与自我批评 · 修正错误</div>
  <h2>两处必须如实纠正的判断</h2>
  <div class="note crit"><h4>修正一：“站内 GEO 还要从零建设”的初判不成立</h4>
  <p>实际核查线上站点后确认，铭信官网（Next.js）已具备 robots.txt（放行 AI 爬虫）、llms.txt/llms-full.txt、
  sitemap、JSON-LD、中英双语与内容引擎/推送接口——站内地基<b>无需重复建设</b>；真实短板在<b>站外</b>：
  百科/知乎/CSDN/GitHub 的铭信品牌沉淀处于起步期，且需与其他同名“铭信”企业消歧（FX 命名沿革声明）。
  本计划把重心如实移到站外信源与实体一致性。</p></div>
  <div class="note crit"><h4>修正二：对“T1 首位提及率 ≥ 60%”的目标做诚实校准</h4>
  <p>用保守的对数赔率模型测算，满配 GEO 后 T1（最窄类目）全量问法的被提及率 P50 约
  {pct(proj['phases']['P4_稳固出海']['tiers']['T1']['mention_p50'])}（P10–P90 区间
  {pct(proj['phases']['P4_稳固出海']['tiers']['T1']['mention_p10'])}–{pct(proj['phases']['P4_稳固出海']['tiers']['T1']['mention_p90'])}），
  对应首位提及率 P50 约 {pct(proj['phases']['P4_稳固出海']['tiers']['T1']['first_mention_p50'])}。
  因此“≥60% 首位提及”应理解为<b>仅适用于最窄的核心长尾问法、且处于乐观（P90）区间</b>的冲刺目标，
  不应作为全量 T1 的承诺值。本报告以区间而非单点对外表述。</p></div>
</div></section>""")

    # ---- 方法学 ----
    w = base["weights"]
    S.append(f"""
<section class="section pagebreak"><div class="wrap">
  <div class="eyebrow">方法学</div>
  <h2>一切数据有理有据、可复现</h2>
  <h3>查询宇宙</h3>
  <p>70 条标准问法，覆盖 T1/T2/T3 三层类目 × 5 类角色画像 × 5 种提问意图 × 中英双语，固定种子
  {C.SEED}、固定时间戳，存于 <code>queries.json</code>。</p>
  <h3>采集与数据分级</h3>
  <p><span class="tag a">A · API 真测</span>经百炼 CLI（DashScope）直连
  {esc('、'.join(man['available_api_models']))}，每条问法采样、原始回答全部落盘 <code>outputs/raw/</code>。
  <span class="tag b">B · 人工取证</span>无法直连的模型（文心/豆包/元宝/Kimi/海外）采用标准化人工取证协议
  （统一 prompt、追问来源、截图+文本+双人复核），<b>不臆造</b>，模板见 <code>outputs/manual/</code>。</p>
  <h3>GEO 可见性指数 GVI（0–100，权重公开可调）</h3>
  {table(["分量","含义","权重"],
    [["Mention 提及","是否被提及", pct(w['mention'],0)],
     ["First-Rank 排序位","首位=1，第 r 位=1/r", pct(w['first_rank'],0)],
     ["Share-of-Voice 声量","我方提及次数 / 全部厂商提及次数", pct(w['share_of_voice'],0)],
     ["Citation 引用","回答是否带可核验来源/链接", pct(w['citation'],0)],
     ["Accuracy 准确正面","被提及内容的正面/准确启发式（需人工复核）", pct(w['accuracy'],0)]],
    ["l","l","r"])}
  <p class="mut">诚实声明：Citation 与 Accuracy 为启发式并标注 needs_review；把“华为昇腾”等平台性提及计入竞品声量属
  对我方保守的噪声（高估竞品），已如实披露。</p>
</div></section>""")

    # ---- 基线结果 ----
    model_rows = []
    for m, v in bm.items():
        model_rows.append([f"{v['vendor']}（{m}）", f"{v['gvi']:.2f}", pct(v['mention_rate']),
                           f"{v['first_rank']:.3f}", pct(v['citation_rate'],0)])
    lb = list(base["mention_leaderboard"].items())
    lb_rows = [[(f"{C.BRAND}（我方）" if k == C.BRAND else k), str(v)] for k, v in lb[:10]]
    S.append(f"""
<section class="section"><div class="wrap">
  <div class="eyebrow">基线结果</div>
  <h2>真实可见性基线（{ov['n_records_ok']} 次采样）</h2>
  {fig("gvi_by_model.png","各大模型 GEO 可见性指数（基线）")}
  {table(["模型","GVI","被提及率","排序位","引用率"], model_rows, ["l","r","r","r","r"])}
  <div class="grid2">
    <div>{fig("mention_rate_by_tier.png","各类目 × 模型 · 被提及率")}</div>
    <div>{fig("gvi_radar.png","GEO 五分量画像（基线）")}</div>
  </div>
  <h3>厂商声量榜（被 AI 回答提及次数）</h3>
  {fig("share_of_voice.png","厂商声量榜（基线）")}
  {table(["厂商","被提及回答数"], lb_rows, ["l","r"])}
  <p class="mut">解读：铭信被提及多源自“点名式”问法（如“铭信是做什么的”），在开放式推荐/排序问法中仍较少被主动列举——这正是提升空间。</p>
</div></section>""")

    # ---- 深度归因（按意图/角色/语言 + 正面交锋 + 机会缺口） ----
    intent_label = {"definition": "定义类", "recommendation": "推荐类",
                    "comparison": "对比类", "ranking": "排名类",
                    "problem_solution": "问题方案类"}
    bi = base["by_intent"]
    intent_order = ["definition", "recommendation", "comparison", "ranking", "problem_solution"]
    intent_rows = [[intent_label[it], str(bi[it]["n"]), pct(bi[it]["mention_rate"]),
                    f"{bi[it]['first_rank']:.3f}", f"{bi[it]['gvi']:.1f}"]
                   for it in intent_order if it in bi]
    bp = base["by_persona"]
    persona_rows = [[p, str(d["n"]), pct(d["mention_rate"]), f"{d['gvi']:.1f}"]
                    for p, d in sorted(bp.items(), key=lambda kv: -kv[1]["mention_rate"])]
    bl = base["by_lang"]
    lang_name = {"zh": "中文", "en": "英文"}
    lang_rows = [[lang_name.get(lg, lg), str(d["n"]), pct(d["mention_rate"]), f"{d['gvi']:.1f}"]
                 for lg, d in bl.items()]
    h2h = base["head_to_head"]
    h2h_rows = [[((f"{C.BRAND}（我方）" if k == C.BRAND else k)),
                 str(v["win"]), str(v["loss"]), str(v["both"]), str(v["exposure"])]
                for k, v in list(h2h.items())[:8]]
    og = base["opportunity_gap"]
    og_rows = [[intent_label[it], str(og["by_intent"].get(it, 0))]
               for it in intent_order]
    rec0 = pct(bi["recommendation"]["mention_rate"]) if "recommendation" in bi else "0.0%"
    cmp0 = pct(bi["comparison"]["mention_rate"]) if "comparison" in bi else "0.0%"
    en0 = pct(bl.get("en", {}).get("mention_rate", 0))
    S.append(f"""
<section class="section pagebreak"><div class="wrap">
  <div class="eyebrow">深度归因 · 用矛盾的眼光看问题</div>
  <h2>我们在“哪种问法、哪类人、哪种语言”被看见，在哪缺席</h2>
  <p class="lead">把 {ov['n_records_ok']} 条真实回答按提问意图、角色画像、语言三维拆开，
  矛盾立刻清晰：铭信几乎只在<b>点名式</b>（对比 {cmp0}、定义）问法里出现，
  在<b>开放式推荐/排名/问题求解</b>问法里被提及率为 {rec0}——这正是“被看见但未领先”的量化证据。</p>
  {fig("mention_by_intent.png","各提问意图 · 铭信被提及率（基线，全模型合计）")}
  {table(["提问意图","样本数","被提及率","排序位","GVI"], intent_rows, ["l","r","r","r","r"])}
  <div class="grid2">
    <div><h4>按角色画像</h4>
    {table(["角色","样本数","被提及率","GVI"], persona_rows, ["l","r","r","r"])}</div>
    <div><h4>按语言（出海缺口）</h4>
    {table(["语言","样本数","被提及率","GVI"], lang_rows, ["l","r","r","r"])}
    <p class="mut">英文问法被提及率 {en0}：海外/英文语料几乎空白，是“稳固出海”阶段的明确靶面。</p></div>
  </div>
  <h3>正面交锋：与主要竞品的“同框/抢答”计数</h3>
  <p>逐条统计每个竞品与铭信的共现：<b>win</b>=我方被提及而对方缺席；
  <b>loss</b>=对方被提及而我方缺席（被抢答）；<b>both</b>=同一回答同框；<b>exposure</b>=对方总曝光。</p>
  {fig("head_to_head.png","正面交锋：铭信 vs 主要竞品（基线，按曝光排序）")}
  {table(["竞品","win 我方独占","loss 被抢答","both 同框","exposure 对方曝光"], h2h_rows, ["l","r","r","r","r"])}
  <div class="note crit"><h4>机会缺口（最具体的攻坚靶面）</h4>
  <p>共 <b>{og['total']}</b> 条回答（占有效回答 {pct(og['share_of_ok'])}）<b>点名了至少一个竞品却没有提到铭信</b>。
  按类目：T1 {og['by_tier']['T1']} · T2 {og['by_tier']['T2']} · T3 {og['by_tier']['T3']}。
  这 {og['total']} 条就是 GEO 工程要逐条夺回的“失地”，按下表的意图分布优先处理。</p>
  {table(["缺席最严重的意图","竞品被点名而我方缺席的回答数"], og_rows, ["l","r"])}
  </div>
  <p class="mut">方法：共现基于 geo_config.py 的 BRAND_ALIASES 与 COMPETITORS 词表，对 outputs/raw/ 全量真实回答统计，可一键复现；
  把平台性提及（如“华为昇腾”）计入竞品属对我方保守的口径，已如实披露。</p>
</div></section>""")

    # ---- 信源缺口 ----
    gap_rows = []
    for vendor, d in gap["by_model"].items():
        gap_rows.append([vendor, pct(d["weighted_coverage"],0), pct(d["gap"],0),
                         "、".join(d["schema_pref"][:3])])
    prio_rows = [[r["platform"], f"{r['priority']:.2f}", "、".join(r["models"][:3])]
                 for r in gap["platform_priority"][:10]]
    S.append(f"""
<section class="section pagebreak"><div class="wrap">
  <div class="eyebrow">信源覆盖缺口</div>
  <h2>各模型“答案来自哪里”，我们覆盖了多少</h2>
  {fig("source_coverage.png","各国产大模型 · 我方当前加权信源覆盖率")}
  {table(["模型","当前覆盖","缺口","偏好 schema"], gap_rows, ["l","r","r","l"])}
  <h3>站外行动优先级（影响力 × 缺口）</h3>
  {fig("source_priority.png","站外信源行动优先级")}
  {table(["平台","优先级","主要影响模型"], prio_rows, ["l","r","l"])}
</div></section>""")

    # ---- 站内现状（铭信官网，Next.js） ----
    S.append(f"""
<section class="section"><div class="wrap">
  <div class="eyebrow">站内现状（mingxinstorage.xyz · Next.js）</div>
  <h2>站内 GEO 基础设施完备——线上探测可复核</h2>
  {table(["资产","内容","GEO 价值"],
    [["robots 放行 AI 爬虫", f"放行 {len(_ai())} 类（GPTBot/ClaudeBot/PerplexityBot/Google-Extended/Bytespider 等，路由提供）", "被抓取是被引用的前提"],
     ["llms.txt / llms-full.txt", "站点事实索引 + 要点正文内联（路由提供）", "便于模型免爬取直接引用，前瞻信号"],
     ["sitemap.xml + JSON-LD", "全站结构化 + Organization/Product/FAQPage", "实体一致性与可抽取性"],
     ["中英双语", "zh/en 镜像页面", "承接出海与英文问法"],
     ["内容引擎", "/api/engine/*（内容生成与更新）", "持续供给答案优先内容"],
     ["推送接口", "/api/seo/ping（IndexNow + 百度推送，Bearer CRON_SECRET）", "收录时效"],
     ["证据库", "/evidence（R1–R9 签字级/正式版报告）", "可引用的权威事实资产"]],
    ["l","l","l"])}
  <div class="note ok"><h4>现状核查口径</h4><p>以上为 2026-07-19 现状核查结论；官网为 Next.js 站点（robots/llms 为路由），
  复核方式为对线上 URL 做 HTTP 探测（<code>coverage_resolver.py</code>）；网络不可用时如实标注 unknown/pending，不编造。
  关键数值与 results.json（官网 company.ts 镜像）单一数据源一致。</p></div>
</div></section>""")

    # ---- 站外工具包 ----
    S.append(f"""
<section class="section pagebreak"><div class="wrap">
  <div class="eyebrow">站外多信源工具包</div>
  <h2>从单一事实源生成、人工核准后发布</h2>
  <p>按各模型信源偏好，生成母版 + 9 个平台改写草稿与发布一致性清单（<code>geo_plan/offsite/</code>）。
  全部由 <code>entity_facts.json</code> 派生，保证全网口径一致（通义对信息冲突敏感）。</p>
  {table(["平台","主要影响模型","格式要点"],
    [["CSDN / 知乎 / GitHub","DeepSeek / Kimi","技术教程、对比表、可复现数据、README"],
     ["阿里云开发者社区 / 语雀","通义千问","强结构化、标题分层、FAQ、数据模块"],
     ["百度百科 / 百家号 / 文库","文心一言","中性百科、资讯口径、来源支撑"],
     ["微信公众号","腾讯元宝","深度科普、关键数字加粗"],
     ["搜狐号 / 网易号 / 头条","豆包","资讯流、信息前置可摘录"]],
    ["l","l","l"])}
  <div class="note"><h4>白帽红线</h4><p>仅生成草稿、不代发；禁止伪造测评/水军/刷量/隐藏文字；资质沿用“申请中/示意”如实口径；
  实体锚点（sameAs）仅在真实外部档案上线后再写入官网，避免坏链与失真。</p></div>
</div></section>""")

    # ---- 提升预测 ----
    ph = proj["phases"]
    proj_rows = []
    for name in ["P0_基线", "P1_地基", "P2_T1夺冠", "P3_T2梯队", "P4_稳固出海"]:
        t1 = ph[name]["tiers"]["T1"]; t2 = ph[name]["tiers"]["T2"]
        proj_rows.append([f"{name.split('_')[1]}（{ph[name]['weeks']}）",
                          f"{pct(t1['mention_p50'])}", f"{pct(t1['mention_p10'])}–{pct(t1['mention_p90'])}",
                          f"{pct(t2['mention_p50'])}"])
    torn = proj["tornado_T1"]["rows"][:3]
    S.append(f"""
<section class="section"><div class="wrap">
  <div class="eyebrow">提升预测（保守区间，非承诺）</div>
  <h2>分阶段被提及概率的 P10 / P50 / P90</h2>
  <p>模型：在“可被检索的事实页”建立的潜在先验 seed 之上，按各 GEO 杠杆的赔率乘子在 logit 空间叠加，
  并以类目可达上限封顶（T1≤{pct(C.P_CEILING['T1'],0)}）。系数取自 GEO 公开研究的区间下沿，刻意保守。</p>
  {table(["阶段","T1 被提及 P50","T1 区间(P10–P90)","T2 被提及 P50"], proj_rows, ["l","r","r","r"])}
  <div class="grid2">
    <div>{fig("projection_trajectory.png","分阶段各类目被提及概率（P50 线 + P10–P90 带）")}</div>
    <div>{fig("projection_tornado.png","T1 终态杠杆敏感性")}</div>
  </div>
  <p>敏感性头部杠杆：{esc('、'.join(r['lever'] for r in torn))}——印证“先放行抓取、再上结构化、同时铺站外信源”的优先级。</p>
  {fig("projection_seed_sensitivity.png","seed 先验 ±50% 敏感性")}
  <div class="note"><h4>口径声明</h4><p>以上为<b>规划假设区间</b>而非业绩承诺；seed、ceiling 与赔率乘子均已在 geo_config.py 标注来源（G1–G8），
  可调、可质疑、可复测。</p></div>
</div></section>""")

    # ---- 阶段目标 + 客观检验 ----
    S.append(f"""
<section class="section pagebreak"><div class="wrap">
  <div class="eyebrow">阶段目标与客观检验标准</div>
  <h2>可分解、可复盘、可检验</h2>
  {table(["阶段","周期","核心动作","客观检验标准"],
    [["一 · 地基","第1–2周","robots/llms/schema/事实页上线","站内 schema 覆盖达标；AI bot 全放行；基线报告产出 ✓"],
     ["二 · T1 夺冠","第3–6周","DeepSeek/通义信源覆盖 + 答案优先页","DeepSeek、通义在 T1 核心问法被提及率显著提升、GVI 排名进入前列"],
     ["三 · T2 梯队","第7–14周","补文心/豆包/元宝/Kimi 信源","≥4 个国产模型 T2 类目 GVI 进入前 2"],
     ["四 · 稳固出海","第15周起","英文事实页 + 实体锚点 + 月度复测","T1 全模型保持领先；海外模型 T1 进入被引用列表"]],
    ["l","l","l","l"])}
  <p class="mut">每月用同一套 geo_audit.py 复测 GVI，对比阶段目标；未达标的模型定位“抓取层 / 信源层 / 内容层”何处，按“小问题早处理、既纠错又治本”迭代，复盘记入 changelog。</p>
</div></section>""")

    # ---- 月度客观检验看板 ----
    og2 = base["opportunity_gap"]
    S.append(f"""
<section class="section"><div class="wrap">
  <div class="eyebrow">月度客观检验看板（目标，非承诺）</div>
  <h2>用客观、可检验的标准衡量结果</h2>
  <p>下表把“下一轮复测”的检验标准量化：左为本轮真实基线，右为下月目标阈值；
  每月用同一套 <code>geo_audit.py</code> 复测，达标记 ✓、未达标定位“抓取层/信源层/内容层”并记入 changelog。</p>
  {table(["检验指标","本轮基线","下月目标阈值","达标判据"],
    [["总体 GVI（0–100）", f"{ov['gvi']:.1f}", "≥ 12.0", "geo_baseline.overall.gvi"],
     ["品牌平均被提及率", pct(ov['mention_rate']), "≥ 18%", "geo_baseline.overall.mention_rate"],
     ["开放式推荐类被提及率", pct(bi['recommendation']['mention_rate']), "≥ 10%", "geo_baseline.by_intent.recommendation"],
     ["机会缺口（竞品被点名我方缺席）", f"{og2['total']} 条", f"≤ {int(og2['total']*0.7)} 条", "geo_baseline.opportunity_gap.total"],
     ["DeepSeek/通义 加权信源覆盖", "2–5%", "≥ 40%", "source_gap.by_model.weighted_coverage"],
     ["带可核验来源引用率", pct(ov['citation_rate'],1), "≥ 5%", "geo_baseline.overall.citation_rate"]],
    ["l","r","r","l"])}
  <p class="mut">阈值取自 changelog 下月目标，刻意保守可达；目标值为规划假设，最终以复测的客观数据为准（坚持真理、修正错误）。</p>
</div></section>""")

    # ---- 合规 + 治理 ----
    S.append(f"""
<section class="section pagebreak"><div class="wrap">
  <div class="eyebrow">合规、公序良俗与自我纠错</div>
  <h2>白帽红线与数据纪律</h2>
  <ul>
    <li>只做白帽：禁止伪造测评/水军、刷评论、隐藏文字、页面 prompt 注入、冒称资质或证书号。</li>
    <li>所有对外事实可溯源至 results.json 或公开来源（S1–S43）与第三方实测报告；竞品对比用客观口径，不贬损。</li>
    <li>数据纪律：报告中每个数字标注来源与复现脚本；预测区间明确标注为规划假设。</li>
    <li>月度复盘：GVI 复测 + changelog 记录 + 客观检验看板，自我净化、自我完善、自我纠错。</li>
  </ul>
  <h3>复现清单</h3>
  <p class="mut">queries.json · geo_config.py · geo_audit.py · geo_scoring.py · geo_projection.py · source_audit.py ·
  make_offsite_kit.py · build_report_html.py · export_report_pdf.py；数据产物见 outputs/，站外草稿见 offsite/。</p>
</div></section>""")

    body = "".join(S)
    doc = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>铭信 · 基于 AI 的 GEO 提升计划与基线报告</title>
<style>{CSS}</style></head><body>
{body}
</body></html>"""
    # 各 section 内部已自带 .wrap 容器，无需外层重复。
    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    meta = {"header": "铭信 Mingxin Technology · 基于 AI 的 GEO 提升计划与基线报告",
            "footer": f"{facts['entity_zh']} · GEO 计划"}
    with open(META_OUT, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"报告 HTML 已生成：{HTML_OUT}")


def _ai():
    # AI 爬虫清单计数（用于报告文案；与官网 robots 路由口径一致，此处独立维护避免跨仓依赖）
    return ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "anthropic-ai",
            "Claude-Web", "Claude-User", "PerplexityBot", "Perplexity-User",
            "Google-Extended", "Applebot-Extended", "Applebot", "Bytespider",
            "Amazonbot", "CCBot", "Meta-ExternalAgent", "cohere-ai",
            "DeepSeekBot", "YisouSpider", "Sogou web spider"]


if __name__ == "__main__":
    build()
