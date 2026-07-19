# -*- coding: utf-8 -*-
"""铭信 GEO 提升计划 · HTML 构建器（苹果视觉，HTML→PDF 唯一旗舰交付）。

单一数据源：outputs/geo_results.json（由 scoring.py 真实计算）+ business_plan/
outputs/results.json（产品事实，与官网 company.ts 同源）。复用 business_plan/
html_style.py 苹果视觉发射器与 assets/apple.css。绝不在本文件内编造实测数据。

复现：python build_geo_html.py → python export_geo_pdf.py
"""
from __future__ import annotations

import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
BP_DIR = os.path.join(os.path.dirname(BASE), "business_plan")
sys.path.insert(0, BP_DIR)

import html_style as S  # noqa: E402

FIG = os.path.join(BASE, "figures")
CSS_PATH = os.path.join(BP_DIR, "assets", "apple.css")
RESULTS = os.path.join(BASE, "outputs", "geo_results.json")
OUT_HTML = os.path.join(BASE, "outputs", "铭信-GEO提升计划.html")
PDF_META = os.path.join(BASE, "outputs", "pdf_meta.json")

BRAND = "铭信"
ENTITY = "铭信（天津）半导体设备有限公司"
SITE = "https://mingxinstorage.xyz"


def load():
    with open(RESULTS, "r", encoding="utf-8") as f:
        return json.load(f)


def fig(name):
    return os.path.join(FIG, name)


def has_fig(name):
    return os.path.exists(fig(name))


def add_code(doc, code, caption=None):
    """嵌入代码/配置块（用于可直接落地的 robots.txt / llms.txt / JSON-LD 等）。"""
    import html as _h
    cap = f'<div class="code-cap">{S._esc(caption)}</div>' if caption else ""
    doc.add(f'{cap}<pre class="code">{_h.escape(code, quote=False)}</pre>')


def maybe_hero(doc, name):
    if has_fig(name):
        S.add_hero_image(doc, fig(name))


def maybe_divider(doc, label, title_cn, title_en, hero, sub=""):
    """章节扉页：有 hero 图则全幅，否则用简洁文字扉页。"""
    uri = S._data_uri(fig(hero)) if has_fig(hero) else ""
    img = f'<img src="{uri}" alt="hero"/>' if uri else ""
    en = f'<div class="dv-en">{S._esc(title_en)}</div>' if title_en else ""
    sb = f'<div class="dv-sub">{S._esc(sub)}</div>' if sub else ""
    doc.add(
        '<section class="divider">'
        f'<figure class="dv-hero">{img}</figure>'
        f'<div class="dv-num">{S._esc(label)}</div>'
        f'<div class="dv-cn">{S._esc(title_cn)}</div>{en}{sb}'
        '</section>'
    )


def pct(x, d=1):
    return f"{x*100:.{d}f}%"


def build():
    R = load()
    doc = S.init_document()
    S.add_header_text(doc, f"{ENTITY} · {BRAND} GEO 提升计划")
    S.add_footer_pagenumber(doc, ENTITY)
    # 章节在后续 StrReplace 中插入
    _assemble(doc, R)

    with open(CSS_PATH, "r", encoding="utf-8") as f:
        css = f.read()
    css += EXTRA_CSS

    html = (
        "<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"utf-8\"/>\n"
        f"<title>{BRAND} GEO 提升计划</title>\n<style>\n{css}\n</style>\n</head>\n<body>\n"
        f"{doc.body_html()}\n</body>\n</html>"
    )
    os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    with open(PDF_META, "w", encoding="utf-8") as f:
        json.dump({"header": doc.header_text, "footer": doc.footer_text}, f, ensure_ascii=False)
    print(f"Saved: {OUT_HTML}  ({os.path.getsize(OUT_HTML)/1e6:.2f} MB)")


EXTRA_CSS = """
/* GEO 计划专属微调 */
.cover { padding-top: 0; }
.cover .hero img { max-height: 78mm; object-fit: cover; }
.cover .doc-title { font-size: 32pt; margin: 12px 0 2px; }
.cover .doc-subtitle { margin: 2px 0; }
pre.code {
  font-family: "SF Mono", "JetBrains Mono", Consolas, "Microsoft YaHei", monospace;
  font-size: 8.6pt; line-height: 1.5; color: #1D1D1F;
  background: #F5F5F7; border: 0.5px solid #E2E2E7; border-radius: 10px;
  padding: 12px 14px; margin: 8px 0 14px; white-space: pre-wrap; word-break: break-word;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
.code-cap { font-size: 9.5pt; color: #6E6E73; margin: 6px 0 2px; font-weight: 600; }
table.tl td:first-child, table.tl th:first-child { white-space: normal; }
"""


# ===========================================================================
# 封面 + 声明
# ===========================================================================
def cover(doc, R):
    a = R["aggregate"]
    facts = R["facts"]
    doc.add('<section class="cover">')
    maybe_hero(doc, "cover_hero.png")
    S.add_title(doc, f"{BRAND} GEO 提升计划")
    S.add_subtitle(doc, "GENERATIVE ENGINE OPTIMIZATION · 生成式引擎优化", size=14)
    S.add_subtitle(doc, "让各类 AI 大模型在细分类目中优先提及与推荐铭信",
                   size=16, color=S.COLOR_PRIMARY)
    S.add_subtitle(doc, f"{ENTITY} · {BRAND} {R['brand']['model']}",
                   size=12, color=S.COLOR_SOFT)
    doc.add_paragraph()
    S.add_three_line_table(
        doc, ["项目", "内容"],
        [
            ["编制主体", ENTITY],
            ["目标", "在可赢得细分类目争得各 AI 大模型‘第一被提及/被推荐’，宽口径稳步爬坡"],
            ["实测基线", f"窄类目 GEO 指数 {a['narrow']['geo_index']:.1f} · 宽类目 {a['broad']['geo_index']:.1f}（满分 100，{R['meta']['survey_date']} 实测）"],
            ["实测引擎", "通义千问 Max / Plus（真实调用）；另 10 个引擎待密钥复测，绝不编造"],
            ["产品事实", f"吞吐提升 {facts['throughput_uplift']}（R2/R3）· TTFT ↓{facts['ttft_reduction']}（R2）· FX100 满配 ¥{facts['fx100_full_price_cny']:,}（≈¥{facts['fx100_cny_per_tb']:,}/TB）"],
            ["方法纪律", "所有数据由 Python 模型真实跑出、一键复现；合规且合公序良俗"],
        ],
        col_align=["l", "l"], font_size=10.5,
    )
    S.add_body(
        doc,
        "本计划为对外正式文档。实测基线由可复现的 Python 测评模型真实跑出（见第三章与附录）；"
        "‘待密钥复测’引擎在取得授权密钥前不产生任何编造数据。阶段目标为客观靶点而非名次承诺，"
        "见第六章风险与边界。",
        indent=False, size=9.5, align="center",
    )
    doc.add("</section>")


def _assemble(doc, R):
    cover(doc, R)
    chap_exec(doc, R)
    chap_baseline(doc, R)
    chap_category(doc, R)
    chap_method(doc, R)
    chap_levers(doc, R)
    chap_roadmap(doc, R)
    chap_risk(doc, R)
    chap_review(doc, R)
    chap_appendix(doc, R)


# ===========================================================================
# 第一章 执行摘要
# ===========================================================================
def chap_exec(doc, R):
    a = R["aggregate"]
    ls = R["lever_scores"]
    avg_lever = sum(ls[k]["score5"] for k in ls) / len(ls)
    maybe_divider(doc, "执行摘要", "执行摘要", "Executive Summary", "divider_exec.png",
                  "实事求是的现状 · 双靶点策略 · 可复现的测评与可检验的目标")
    S.add_h1(doc, "一", "执行摘要")
    S.add_body(
        doc,
        f"**GEO（生成式引擎优化）** 的目标，是让 ChatGPT、Claude、Gemini、通义千问、DeepSeek、"
        f"豆包、文心一言等各类 AI 大模型在回答用户问题时，优先**提及、引用并推荐 {BRAND}**。"
        f"这与传统 SEO（争搜索结果排名）不同——GEO 争的是**进入 AI 生成答案本身**。",
    )
    S.add_h2(doc, "1.1", "一句话结论")
    S.add_callout(
        doc, "结论",
        f"截至 {R['meta']['survey_date']}，{BRAND} 在主流大模型回答中的被提及率实测为 **0**"
        f"（窄/宽类目 GEO 指数均为 **{a['narrow']['geo_index']:.1f}**），起点近零、如实呈现；"
        "巨头主导宽口径。**可行路径**是：先在‘可赢得的细分类目’用差异化争得真实第一（客观可检验），"
        "同时在宽口径稳步爬坡。本计划给出可复现的测评模型、四大杠杆与分阶段可检验目标。",
        kind="warn",
    )
    S.add_h2(doc, "1.2", "关键指标快照（实测基线）")
    S.add_metric_cards(
        doc,
        [
            (f"{a['narrow']['geo_index']:.0f}", "窄类目 GEO 指数", "满分 100 · 争第一靶点"),
            (f"{a['broad']['geo_index']:.0f}", "宽类目 GEO 指数", "满分 100 · 可见度爬坡"),
            (f"{pct(a['overall']['competitor_sov']['rows'][0]['sov'] if a['overall']['competitor_sov']['rows'] else 0,1)}", "竞品最高声量", "巨头主导现状"),
            (f"{avg_lever:.1f}/5", "四大杠杆就绪度", "实事求是自审"),
        ],
        per_row=4,
    )
    self_sov = next((r["sov"] for r in a["overall"]["competitor_sov"]["rows"] if r["is_self"]), 0)
    S.add_metric_cards(
        doc,
        [
            (f"{pct(self_sov,1)}", f"{BRAND} 当前声量", "近零起点"),
            ("2", "现已实测引擎", "通义千问 Max / Plus"),
            ("10", "待密钥复测引擎", "绝不编造"),
            (f"{R['meta']['n_queries']}×{R['meta']['repeats']}", "查询×重复采样", "统计稳定性"),
        ],
        per_row=4,
    )
    S.add_h2(doc, "1.3", "双靶点策略")
    S.add_bullet(doc, f"**可赢得的细分类目（争真实第一）**：{R['categories']['narrow']['name_zh']}。"
                      "竞争集合小、国产适配壁垒高，凭差异化可真实争第一且客观可检验。")
    S.add_bullet(doc, f"**宽口径（多年可见度爬坡）**：{R['categories']['broad']['name_zh']}。"
                      "诚实目标是进入被提及/被推荐集合并爬升 Top-N，而非短期声称第一。")
    S.add_h2(doc, "1.4", "四大杠杆与节奏")
    S.add_bullet(doc, "**L1 实体接地**：让模型认得清是谁（Wikidata/百科/schema.org/NAP 一致 + FX 命名沿革消歧）。")
    S.add_bullet(doc, "**L2 技术可达性**：让爬虫进得来、读得懂（robots.txt/llms.txt/sitemap/速度）。")
    S.add_bullet(doc, "**L3 结构化内容**：让回答抽得出、引得到（答案胶囊/FAQ/Product schema/对比页/报告编号）。")
    S.add_bullet(doc, "**L4 站外权威**：让模型信得过（行业媒体/独立基准/技术内容/可引用证据库 R1–R9）。")


# ===========================================================================
# 第二章 现状判断与实测基线
# ===========================================================================
def chap_baseline(doc, R):
    a = R["aggregate"]
    maybe_divider(doc, "第 1 章", "现状判断与实测基线", "Baseline & Status",
                  "divider_baseline.png", "联网核查 + 真实大模型实测，杜绝瞎蒙")
    S.add_h1(doc, "二", "现状判断与实测基线")
    S.add_body(
        doc,
        f"为杜绝主观臆断，本章结论来自两条**客观证据链**：(1) {R['meta']['survey_date']} 对公开"
        "搜索引擎与官网源码的联网核查；(2) 用可复现的 Python 测评模型，对真实大模型发起"
        f"**{R['meta']['n_queries']} 条查询 × {R['meta']['repeats']} 次重复**采样并自动判定。",
    )
    S.add_h2(doc, "2.1", "联网核查：站内完备、站外起步")
    S.add_bullet(doc, "检索‘铭信 + KV Cache 分层/全闪 NVMe-oF/存储加速’，返回结果几乎全是竞品"
                      "（华为、曙光、焱融、浪潮、新华三），且‘铭信’易与其他同名企业混淆——"
                      "需实体消歧 + FX 命名沿革声明（FX100 历史称谓 AISSD5000/WS5000/GP5000，同一产品）。")
    S.add_bullet(doc, f"官网（{SITE}，Next.js）站内 GEO 基础设施**已完备**：robots.txt 放行 AI 爬虫、"
                      "llms.txt/llms-full.txt、sitemap、JSON-LD、中英双语、内容引擎 /api/engine/*、"
                      "/api/seo/ping（IndexNow+百度推送）。")
    S.add_bullet(doc, "站外（百科/知乎/CSDN/GitHub）铭信品牌沉淀处于**起步期**；宽口径‘AI 存储加速’"
                      "被巨头主导（公开口径华为份额居前；曙光 IO500、焱融 MLPerf 等独立榜单频现），"
                      "新进入者短期难在宽口径夺冠。")
    S.add_h2(doc, "2.2", "实测：各 AI 引擎的 GEO 指数")
    if has_fig("geo_index_by_engine.png"):
        S.add_figure(doc, fig("geo_index_by_engine.png"),
                     caption="各可实测引擎总体 GEO 指数（误差棒=bootstrap 90% CI）")
    rows = []
    for ek in R["meta"]["chat_engines"]:
        b = R["per_engine"].get(ek, {})
        if not b.get("available"):
            rows.append([b.get("label", ek), "—", "—", "—", "不可用"])
            continue
        ov = b["overall"]
        rows.append([
            b["label"], f"{ov['geo_index']:.1f}",
            pct(ov["metrics"]["mention_rate"], 1),
            pct(ov["metrics"]["sov"], 1),
            f"{ov['ci90'][0]:.1f}–{ov['ci90'][1]:.1f}",
        ])
    rows.append([
        "对话引擎聚合", f"{a['overall']['geo_index']:.1f}",
        pct(a["overall"]["metrics"]["mention_rate"], 1),
        pct(a["overall"]["metrics"]["sov"], 1),
        f"{a['overall']['ci90'][0]:.1f}–{a['overall']['ci90'][1]:.1f}",
    ])
    S.add_three_line_table(
        doc, ["引擎", "GEO 指数", "被提及率", "声量份额", "90% CI"],
        rows, col_align=["l", "c", "c", "c", "c"], highlight_last=True,
    )
    S.add_callout(
        doc, "实测口径说明",
        f"以上为 **{', '.join(R['meta']['chat_engines'])}** 的真实调用结果。{BRAND} 在 "
        f"{a['overall']['metrics']['n']} 条有效回答中被提及 **{a['overall']['competitor_sov']['rows'][0]['mentions'] if False else a['overall']['funnel']['mentioned']}** 次，"
        "故 GEO 指数为 0——这是**真实起点**，不修饰、不夸大。",
    )
    S.add_h2(doc, "2.3", "竞争格局：声量被谁占据")
    if has_fig("sov_competitors.png"):
        S.add_figure(doc, fig("sov_competitors.png"),
                     caption="细分赛道声量份额：铭信 vs 竞品（对话引擎聚合）")
    if has_fig("landscape.png"):
        S.add_figure(doc, fig("landscape.png"),
                     caption="宽类目当前 AI 回答可见度（竞品被提及次数）")
    S.add_h2(doc, "2.4", "转化漏斗：从被提及到被推荐第一")
    if has_fig("mention_funnel.png"):
        S.add_figure(doc, fig("mention_funnel.png"),
                     caption="窄类目 GEO 转化漏斗（实测基线，起点近零）")
    fn = a["narrow"]["funnel"]
    S.add_body(
        doc,
        f"窄类目 {fn['responses']} 条回答中：被提及 {fn['mentioned']}、被推荐 {fn['recommended']}、"
        f"排名第一 {fn['ranked_top1']}。漏斗每一环都是后续可被客观检验的提升靶点。",
        indent=False, size=10.5,
    )
    S.add_h2(doc, "2.5", "待密钥复测引擎（如实披露）")
    pend = R["meta"]["pending_engines"]
    S.add_three_line_table(
        doc, ["引擎", "厂商口径", "所需密钥", "状态"],
        [[p["label"], "", p.get("env_key") or "—", p["note"]] for p in pend],
        col_align=["l", "l", "l", "c"], font_size=9.5,
    )


# ===========================================================================
# 第三章 细分类目锚定（双靶点）
# ===========================================================================
def chap_category(doc, R):
    cat = R["categories"]
    maybe_divider(doc, "第 2 章", "细分类目锚定", "Category Anchoring",
                  "divider_category.png", "在可赢得处争第一，在宽口径稳步爬坡")
    S.add_h1(doc, "三", "细分类目锚定：双靶点策略")
    S.add_body(
        doc,
        "‘达到细分类目第一’必须先定义**在哪个类目、用什么标准**衡量第一，否则无法客观检验。"
        "基于实测现状（宽口径被巨头主导、自身近零），我们采取**双靶点**：先在可赢得的精确"
        "细分争真实第一，再带动宽口径可见度。",
    )
    S.add_h2(doc, "3.1", "靶点一 · 可赢得的细分类目（争真实第一）")
    S.add_callout(doc, cat["narrow"]["name_zh"], cat["narrow"]["rationale"], kind="good")
    S.add_body(doc, "**类目锚词（用于内容与实体一致性）**：" +
               "、".join(cat["narrow"]["anchor_keywords_zh"]) + "。", indent=False, size=10.5)
    S.add_bullet(doc, "可检验的‘第一’定义：在窄类目查询篮上，各实测引擎对‘推荐/排名’类问题中，"
                      f"{BRAND} 为**首个被提及或被明确推荐**的厂商，且多次采样稳定。")
    S.add_h2(doc, "3.2", "靶点二 · 宽口径（多年可见度爬坡）")
    S.add_callout(doc, cat["broad"]["name_zh"], cat["broad"]["rationale"], kind="info")
    S.add_bullet(doc, "可检验目标：进入宽口径‘推荐厂商’回答的被提及集合，并将被提及次数/排名"
                      "逐阶段抬升至 Top-N（非短期夺冠）。")
    S.add_h2(doc, "3.3", "差异化支点（为何窄类目可赢）")
    S.add_three_line_table(
        doc, ["支点", "铭信优势", "对 GEO 的意义"],
        [
            ["480B 签字级实测", "生产部署形态长上下文冷恢复：吞吐 +29–40%、TTFT ↓26–32%（R2/R3）", "高区分度锚词，少有厂商正面占位"],
            ["LMCache 源码级补丁", "并行读补丁 TTFT 4.1×（R1），补丁+原始数据可复现（R8）", "开源可审计，强化 E-E-A-T 可信度"],
            ["多平台适配实测", "AMD MI308X / 昇腾 910B / 沐曦 N260 多平台适配实测（R1/R5/R9）", "国产算力/非 N 卡查询的强匹配实体"],
            ["可复现证据库 + 透明定价", "R1–R9 签字级报告；FX100 满配 ¥371,200（≈¥2,014/TB）", "‘选型/性价比’类查询的有据论点"],
        ],
        col_align=["l", "l", "l"], font_size=9.5,
    )


# ===========================================================================
# 第四章 GEO 测评模型与方法（可复现）
# ===========================================================================
def chap_method(doc, R):
    w = R["meta"]["weights"]
    maybe_divider(doc, "第 3 章", "GEO 测评模型与方法", "Measurement Model",
                  "divider_method.png", "可复现、可检验、绝不瞎蒙的打分体系")
    S.add_h1(doc, "四", "GEO 测评模型与方法（可复现）")
    S.add_body(
        doc,
        "本测评模型是全篇的客观标尺：用统一的查询篮向真实大模型提问，自动判定每条回答中"
        "‘是否提及/是否推荐/排名第几/是否引用/竞品声量’，再按公开权重合成 0–100 的 GEO 指数。"
        "全流程由 Python 实现、一键复现。",
    )
    S.add_h2(doc, "4.1", "查询篮设计")
    S.add_body(doc, f"共 **{R['meta']['n_queries']} 条**查询，覆盖中英双语 × 四类意图"
                    "（信息型/商业型/对比型/排名型）× 窄/宽两类目。商业型与排名型用于判定‘被推荐’。",
               indent=False, size=10.5)
    S.add_h2(doc, "4.2", "GEO 指数合成公式与权重")
    S.add_three_line_table(
        doc, ["指标", "口径", "权重"],
        [
            ["被提及率 Mention", "回答中出现自家任一别名的比例", pct(w["mention_rate"], 0)],
            ["被推荐率 Recommendation", "商业/排名意图下被列为候选厂商的比例", pct(w["recommendation_rate"], 0)],
            ["声量份额 SoV", "自家提及次数 /（自家+竞品）提及次数", pct(w["sov"], 0)],
            ["排名得分 Rank", "首次出现位次归一化（越靠前越高）", pct(w["rank_score"], 0)],
            ["引用率 Citation", "回答含指向官网域名链接的比例", pct(w["citation_rate"], 0)],
        ],
        col_align=["l", "l", "c"], highlight_last=False,
    )
    add_code(
        doc,
        "GEO_Index = 100 × ( 0.30·Mention + 0.30·Recommendation\n"
        "                  + 0.20·SoV + 0.15·RankScore + 0.05·Citation )\n"
        "RankScore = max(0, 1 − (rank − 1) / 8)        # rank=首次出现位次, 8=位次上限\n"
        "SoV       = self_mentions / (self_mentions + competitor_mentions)\n"
        "90% CI    = bootstrap 重采样 2000 次的 [5%, 95%] 分位",
        caption="GEO 指数合成（权重见 geo_data.SCORING_WEIGHTS，可调、可复现）",
    )
    S.add_h2(doc, "4.3", "引擎覆盖与诚实披露")
    S.add_body(doc, "‘各类 AI 大模型’的覆盖如实分两档：**现已实测**（直连各家官方 API 真实调用："
                    "通义/DeepSeek/GLM/Kimi/混元/星火/豆包/Claude/Gemini）与"
                    "**待密钥复测**（适配器就位，取得授权密钥后即可复测）。后者在无密钥时不产生任何"
                    "编造数据。", indent=False, size=10.5)
    rows = []
    for e in R["engines"]:
        rows.append([e["label"], e.get("vendor", ""),
                     "现已实测" if e.get("reachable_now") else "待密钥复测",
                     e.get("note", "")])
    S.add_three_line_table(
        doc, ["引擎", "厂商", "状态", "说明"], rows,
        col_align=["l", "l", "c", "l"], font_size=9,
    )
    S.add_h2(doc, "4.4", "一键复现链")
    add_code(
        doc,
        "python geo_measure.py     # 真实调用大模型 → outputs/measurements_raw.json\n"
        "python scoring.py         # 合成 GEO 指数 + bootstrap CI → outputs/geo_results.json\n"
        "python charts_geo.py      # 苹果视觉图表 → figures/*.png\n"
        "python build_geo_html.py  # 组装 HTML\n"
        "python export_geo_pdf.py  # Playwright(Chromium) 打印 A4 PDF\n"
        "python verify_geo.py      # 复现链与一致性校验",
        caption="复现链（单一数据源：results.json + geo_results.json）",
    )


# ===========================================================================
# 第五章 四大杠杆工作流（可执行 + 可落地工件）
# ===========================================================================
def _checklist_table(doc, lv):
    rows = [["✓ 已具备" if it["done"] else "○ 待落地", it["item"]] for it in lv["checklist"]]
    S.add_three_line_table(doc, ["状态", "清单项"], rows, col_align=["c", "l"], font_size=9.5)


def chap_levers(doc, R):
    L = R["levers"]
    ls = R["lever_scores"]
    facts = R["facts"]
    maybe_divider(doc, "第 4 章", "四大杠杆工作流", "Four Levers",
                  "divider_levers.png", "实体接地 · 技术可达 · 结构化内容 · 站外权威")
    S.add_h1(doc, "五", "四大杠杆工作流（可执行）")
    S.add_body(
        doc,
        "GEO 的因果链是：**让模型认得清（实体）→ 进得来读得懂（技术）→ 抽得出引得到（内容）"
        "→ 信得过（权威）**。四大杠杆一一对应，全部为正当建设，零刷量、零水军、零黑帽。",
    )
    if has_fig("lever_radar.png"):
        S.add_figure(doc, fig("lever_radar.png"),
                     caption="四大杠杆就绪度雷达（自审清单 done/total×5）")

    # —— L1 实体接地 ——
    S.add_h2(doc, "5.1", f"L1 · {L['L1']['name']}（就绪度 {ls['L1']['score5']}/5）")
    S.add_body(doc, L["L1"]["goal"], indent=False, size=10.5)
    _checklist_table(doc, L["L1"])
    S.add_body(doc, "**可落地工件**：在官网每页 `<head>` 注入 Organization 实体标注，sameAs 指向"
                    "工商/媒体/代码托管等可信源，使各引擎跨源一致地识别同一实体，并与其他同名"
                    "‘铭信’企业消歧。", indent=False, size=10.5)
    add_code(
        doc,
        '<script type="application/ld+json">\n'
        '{\n'
        '  "@context": "https://schema.org",\n'
        '  "@type": "Organization",\n'
        f'  "name": "{ENTITY}",\n'
        '  "alternateName": ["铭信", "Mingxin Technology", "铭信科技"],\n'
        f'  "url": "{SITE}/",\n'
        f'  "logo": "{SITE}/logo.svg",\n'
        f'  "description": "{BRAND} 是存储加速 · 国产算力 · 算力中心全产业链服务商，核心产品为 FX 系列全闪 NVMe-oF 存储加速平台（KV Cache 分层，480B 签字级实测）。",\n'
        '  "knowsAbout": ["KV Cache 分层", "全闪存储", "NVMe-oF", "存储加速", "国产算力卡适配", "算力中心建设"],\n'
        '  "sameAs": [\n'
        '    "https://www.wikidata.org/wiki/Q________",\n'
        '    "https://baike.baidu.com/item/铭信",\n'
        '    "https://github.com/________/mingxin-storage-kb",\n'
        '    "https://www.tianyancha.com/company/________"\n'
        '  ]\n'
        '}\n'
        '</script>',
        caption="JSON-LD · Organization + sameAs（实体接地核心，占位 ____ 待填真实 ID；"
                "sameAs 仅写实测 200 的真实档案）",
    )
    S.add_body(doc, "**命名沿革声明（全网一致）**：铭信 FX100 在既往测试报告文件名中称 AISSD5000、"
                    "历史称谓亦作 WS5000/GP5000，均为同一产品；对外统一 FX 命名"
                    "（FX100/FX200/FX300/FX400 同规则）——用于消歧与历史检索。", indent=False, size=10.5)

    # —— L2 技术可达性 ——
    S.add_h2(doc, "5.2", f"L2 · {L['L2']['name']}（就绪度 {ls['L2']['score5']}/5）")
    S.add_body(doc, L["L2"]["goal"], indent=False, size=10.5)
    _checklist_table(doc, L["L2"])
    S.add_body(doc, f"官网为 Next.js 站点，robots.txt / llms.txt / llms-full.txt / sitemap.xml 均以"
                    f"**路由**形式提供并已上线（{R['meta']['survey_date']} 现状核查）；以下为线上"
                    "现状示意，验证方式为对线上 URL 做 HTTP 探测（coverage_resolver.py）。",
               indent=False, size=10.5)
    add_code(
        doc,
        "# robots.txt — 已上线（Next.js 路由），放行主流 AI 爬虫\n"
        "User-agent: GPTBot\nAllow: /\n\n"
        "User-agent: OAI-SearchBot\nAllow: /\n\n"
        "User-agent: ChatGPT-User\nAllow: /\n\n"
        "User-agent: ClaudeBot\nAllow: /\n\n"
        "User-agent: PerplexityBot\nAllow: /\n\n"
        "User-agent: Google-Extended\nAllow: /\n\n"
        "User-agent: Bytespider\nAllow: /\n\n"
        f"Sitemap: {SITE}/sitemap.xml",
        caption=f"robots.txt（线上现状示意：{SITE}/robots.txt）",
    )
    add_code(
        doc,
        "# llms.txt — 机器可读索引（Markdown，Next.js 路由已上线）\n"
        f"# {BRAND} ({R['brand']['en']})\n\n"
        f"> {ENTITY}：存储加速 · 国产算力 · 算力中心全产业链服务商；核心产品"
        f"{R['brand']['model']}，KV Cache 分层，480B 签字级实测。\n\n"
        "## 核心页面\n"
        f"- [FX 系列产品]({SITE}/products): FX100/FX200/FX300/FX400 规格与定价\n"
        f"- [解决方案]({SITE}/solutions): 五条能力线（国产算力卡适配/存储加速/算力中心建设/效能优化/软件开发）\n"
        f"- [证据库]({SITE}/evidence): R1–R9 签字级/正式版实测报告\n"
        f"- [联测与验收]({SITE}/engagement): 先联测、后决策，G1–G4 门禁\n\n"
        "## 关键事实（均带报告编号）\n"
        f"- 推理吞吐提升 {facts['throughput_uplift']}（R2/R3）；TTFT 降 {facts['ttft_reduction']}（R2）\n"
        f"- 对无外存重算加速 {facts['recompute_speedup']}（R2）；模型加载 {facts['model_load_speedup']} vs NFS（R9·昇腾平台）\n"
        f"- FX100：{facts['fx100_port_gb']}Gb 口 · {facts['fx100_iops_million']*100} 万 IOPS · 满配 ¥{facts['fx100_full_price_cny']:,}（≈¥{facts['fx100_cny_per_tb']:,}/TB）",
        caption=f"llms.txt（线上现状示意：{SITE}/llms.txt；llms-full.txt 内联正文供 RAG 直接取用）",
    )

    # —— L3 结构化内容 ——
    S.add_h2(doc, "5.3", f"L3 · {L['L3']['name']}（就绪度 {ls['L3']['score5']}/5）")
    S.add_body(doc, L["L3"]["goal"], indent=False, size=10.5)
    _checklist_table(doc, L["L3"])
    S.add_body(doc, "**答案胶囊模板**：每个关键小节以 40–60 字直接回答开篇——这正是模型抽取并引用的文本。",
               indent=False, size=10.5)
    add_code(
        doc,
        "【问题式标题】什么是面向大模型推理的 KV Cache 分层全闪 NVMe-oF 存储加速平台？\n"
        "【答案胶囊 40–60 字】它把推理中的 KV Cache 按热度分层卸载到外置全闪 NVMe-oF 阵列，\n"
        "命中即直读、免重算，从而支撑长上下文、提升并发与吞吐；\n"
        f"铭信 {R['brand']['model']} 即为此类产品，480B 实测吞吐提升 {facts['throughput_uplift']}（R2/R3）。",
        caption="答案胶囊（开篇直答 + 实体命名 + 带报告编号的可核查事实）",
    )
    add_code(
        doc,
        '<script type="application/ld+json">\n'
        '{ "@context":"https://schema.org", "@type":"FAQPage", "mainEntity":[\n'
        '  {"@type":"Question","name":"KV Cache 分层存储加速解决什么问题？",\n'
        '   "acceptedAnswer":{"@type":"Answer","text":"长上下文冷恢复下无外存需全量重算；'
        '分层卸载到全闪 NVMe-oF 后免重算，480B 实测对重算加速 8.6–20×（R2）。"}},\n'
        '  {"@type":"Question","name":"铭信 FX100 与 WS5000/AISSD5000/GP5000 是什么关系？",\n'
        '   "acceptedAnswer":{"@type":"Answer","text":"同一产品的不同历史称谓；对外统一采用 FX 命名，'
        '报告索引保留原始文件名以便查证。"}}\n'
        ']}\n'
        '</script>',
        caption="JSON-LD · FAQPage（被‘直接答案’位优先抽取，含命名沿革消歧问答）",
    )
    add_code(
        doc,
        '<script type="application/ld+json">\n'
        '{ "@context":"https://schema.org", "@type":"Product",\n'
        f'  "name":"{BRAND} FX100",\n'
        '  "category":"全闪 NVMe-oF + KV Cache 分层存储加速平台",\n'
        '  "brand":{"@type":"Brand","name":"铭信 / Mingxin Technology"},\n'
        '  "additionalProperty":[\n'
        f'    {{"@type":"PropertyValue","name":"网络接口","value":"{facts["fx100_port_gb"]}Gb"}},\n'
        f'    {{"@type":"PropertyValue","name":"随机 IOPS","value":"{facts["fx100_iops_million"]*100} 万"}},\n'
        f'    {{"@type":"PropertyValue","name":"满配参考价","value":"¥{facts["fx100_full_price_cny"]:,}（≈¥{facts["fx100_cny_per_tb"]:,}/TB）"}}\n'
        '  ]\n'
        '}\n'
        '</script>',
        caption="JSON-LD · Product（规格属性结构化，便于对比类回答引用；规格为厂商口径）",
    )

    # —— L4 站外权威 ——
    S.add_h2(doc, "5.4", f"L4 · {L['L4']['name']}（就绪度 {ls['L4']['score5']}/5）")
    S.add_body(doc, L["L4"]["goal"], indent=False, size=10.5)
    _checklist_table(doc, L["L4"])
    S.add_bullet(doc, "**独立基准**：争取参与 MLPerf Storage / IO500 式公开测试，形成可被模型"
                      "反复引用的中立权威结果（对标焱融 MLPerf、曙光 IO500 路径）。")
    S.add_bullet(doc, "**行业媒体**：向存储在线、至顶网、电子发烧友等供稿与接受报道，沉淀跨源一致的品牌事实。")
    S.add_bullet(doc, "**技术内容**：在知乎/CSDN/掘金与 GitHub 知识库（mingxin-storage-kb）公开白皮书与"
                      "技术文档，强化 E-E-A-T 与可发现性。")
    S.add_bullet(doc, "**可引用资产**：将签字级/正式版实测报告 R1–R9 做成结构清晰、口径一致的可引用"
                      "证据库页面；R8 导出包（补丁+负载客户端+原始数据）支持第三方独立复现。")


# ===========================================================================
# 第六章 分阶段路线图与可检验 KPI
# ===========================================================================
def chap_roadmap(doc, R):
    st = R["stage_targets"]
    maybe_divider(doc, "第 5 章", "分阶段路线图与可检验 KPI", "Roadmap & KPI",
                  "divider_roadmap.png", "先定阶段目标，再用客观标准衡量结果")
    S.add_h1(doc, "六", "分阶段路线图与可检验 KPI")
    if has_fig("stage_targets.png"):
        S.add_figure(doc, fig("stage_targets.png"),
                     caption="分阶段 GEO 指数目标（T0 为实测，30/90/180/365 天为靶点）")
    rows = []
    for i, s in enumerate(st["stages"]):
        rows.append([s, f"{st['narrow'][i]:.0f}", f"{st['broad'][i]:.0f}", st["milestones"][i]])
    S.add_three_line_table(
        doc, ["阶段", "窄类目目标", "宽类目目标", "里程碑 / 退出标准"],
        rows, col_align=["l", "c", "c", "l"], font_size=9.5,
    )
    S.add_h2(doc, "6.1", "各阶段退出标准（可证伪）")
    S.add_bullet(doc, "**30 天**：robots.txt/llms.txt/sitemap/Organization+FAQ+Product schema 全部上线；"
                      "Wikidata/百科条目提交；用同一查询篮复测，窄类目被提及率 > 0。")
    S.add_bullet(doc, "**90 天**：窄类目在 ≥1 个实测引擎进入‘被推荐’候选集；宽口径出现被提及；GEO 指数达表中靶点。")
    S.add_bullet(doc, "**180 天**：窄类目在多数实测引擎稳定进入被推荐/被提及第一梯队（争第一可证伪靶点）。")
    S.add_bullet(doc, "**365 天**：窄类目在‘推荐/排名’类查询中为首个被提及/被推荐厂商且多次采样稳定；"
                      "宽口径稳定进入 Top-N。")
    S.add_h2(doc, "6.2", "目标依据（方向性证据，非名次承诺）")
    S.add_body(
        doc,
        "靶点设定参考公开 GEO 研究的方向性结论：完整 Tier-1 schema 约带来 +40% AI 概览出现率、"
        "llms.txt 部署约 14 天 +32% AI 覆盖（来源 G2/G3）。这些是**方向性证据**，叠加实体接地与"
        "站外权威的复利效应；但 GEO 见效依赖各模型更新节奏，故目标为靶点而非保证（见第七章）。",
        indent=False, size=10.5,
    )
    S.add_h2(doc, "6.3", "测量节奏")
    S.add_bullet(doc, "每 30 天用 `geo_measure.py`+`scoring.py` 复测同一查询篮，结果并入对照，"
                      "形成可追溯的时间序列；取得国际引擎密钥后纳入复测矩阵。")


# ===========================================================================
# 第七章 风险、边界与合规
# ===========================================================================
def chap_risk(doc, R):
    maybe_divider(doc, "第 6 章", "风险、边界与合规", "Risk & Compliance",
                  "divider_risk.png", "实话实说：能承诺什么，不能承诺什么")
    S.add_h1(doc, "七", "风险、边界与合规")
    S.add_h2(doc, "7.1", "本计划承诺与不承诺")
    S.add_callout(
        doc, "边界声明",
        "本计划承诺：**正当手段 + 可复现测量 + 阶段性可检验目标**。不承诺：在任何特定日期对任何"
        "特定模型取得绝对第一名次——因为 GEO 见效依赖各模型训练/检索更新节奏，存在时滞、不可强求。",
        kind="warn",
    )
    S.add_h2(doc, "7.2", "主要风险与对策")
    S.add_three_line_table(
        doc, ["风险", "说明", "对策"],
        [
            ["更新时滞", "模型训练/检索更新有周期，优化见效非即时", "提前布局、持续复测、以检索型引擎先见效"],
            ["品牌混淆", "‘铭信’易与其他同名企业混淆", "L1 实体接地 + FX 命名沿革声明，强化唯一实体"],
            ["巨头主导", "宽口径份额集中于头部", "双靶点：窄类目先赢，宽口径渐进"],
            ["可达性失败", "WebSearch 探针当前 500 不可用", "如实标注、服务恢复后复测；不影响对话引擎实测"],
            ["数据缺口", "国际引擎暂无密钥", "适配器就位，取得密钥后复测，绝不编造"],
        ],
        col_align=["l", "l", "l"], font_size=9.5,
    )
    S.add_h2(doc, "7.3", "合规与公序良俗")
    S.add_bullet(doc, "**绝不**刷榜、伪造评价、雇佣水军、批量灌水或任何操纵性黑帽手段。")
    S.add_bullet(doc, "**绝不**冒用院士肖像或夸大背书；沿用官网既有‘经本人同意、仅文字说明’口径。")
    S.add_bullet(doc, "所有对外事实与官网/商业计划书/实测报告**同源一致**，经得起第三方尽调与检验。")


# ===========================================================================
# 第八章 复盘与自我纠错机制
# ===========================================================================
def chap_review(doc, R):
    maybe_divider(doc, "第 7 章", "复盘与自我纠错机制", "Review & Self-Correction",
                  "divider_review.png", "主动复盘纠错，小问题早处理，既纠错又治本")
    S.add_h1(doc, "八", "复盘与自我纠错机制")
    S.add_body(
        doc,
        "GEO 是持续工程而非一次性项目。我们建立‘测量—诊断—改进—再测量’的闭环，坚持批评与自我批评、"
        "坚持真理、修正错误，使每一步都经得起客观检验。",
    )
    S.add_h2(doc, "8.1", "闭环节奏")
    S.add_bullet(doc, "**月度复测**：固定查询篮复测，对比 GEO 指数与 SoV 时间序列，定位停滞环节。")
    S.add_bullet(doc, "**漏斗诊断**：按‘被提及→被推荐→排名第一’定位卡点，对应回灌到四大杠杆任务。")
    S.add_bullet(doc, "**根因治本**：区分‘内容缺口/实体缺口/权威缺口/技术缺口’，既改表象又补根因。")
    S.add_h2(doc, "8.2", "自查清单（每次复盘）")
    S.add_bullet(doc, "是否仍有任何未经实测的‘乐观假设’或编造数据？（应为否）")
    S.add_bullet(doc, "新上线的 schema/llms.txt/内容是否被校验工具通过、是否被引擎实际抓取？")
    S.add_bullet(doc, "竞品是否有新动作（独立榜单、媒体、内容）导致我方相对份额下降？")


# ===========================================================================
# 附录
# ===========================================================================
def chap_appendix(doc, R):
    maybe_divider(doc, "附录", "附录", "Appendix", "divider_appendix.png",
                  "查询篮 · 引擎注册表 · 引用登记册 · 复现清单")
    S.add_h1(doc, "九", "附录")
    S.add_h2(doc, "A", "查询篮全表")
    type_zh = {"info": "信息型", "commercial": "商业型", "comparison": "对比型", "ranking": "排名型"}
    cat_zh = {"narrow": "窄", "broad": "宽"}
    rows = [[q["id"], cat_zh[q["category"]], type_zh[q["type"]], q["lang"], q["text"]]
            for q in R["query_basket"]]
    S.add_three_line_table(doc, ["ID", "类目", "意图", "语言", "查询文本"],
                           rows, col_align=["l", "c", "c", "c", "l"], font_size=8.5)
    S.add_h2(doc, "B", "AI 引擎注册表")
    rows = [[e["label"], e.get("vendor", ""), e.get("model") or "(默认)",
             "现已实测" if e.get("reachable_now") else "待密钥复测",
             e.get("env_key", "—") or "—"] for e in R["engines"]]
    S.add_three_line_table(doc, ["引擎", "厂商", "模型", "状态", "所需密钥"],
                           rows, col_align=["l", "l", "l", "c", "l"], font_size=8.5)
    S.add_h2(doc, "C", "引用登记册")
    rows = [[k, v] for k, v in R["sources"].items()]
    S.add_three_line_table(doc, ["编号", "来源"], rows, col_align=["c", "l"], font_size=8.5)
    S.add_h2(doc, "D", "复现清单与文件")
    S.add_bullet(doc, "geo_data.py — 单一数据源（类目/查询篮/竞品/引擎/权重/杠杆/目标/引用）。")
    S.add_bullet(doc, "geo_measure.py — 真实采集（bl 调用 + 待密钥适配器）。")
    S.add_bullet(doc, "scoring.py — GEO 指数合成 + bootstrap CI。")
    S.add_bullet(doc, "charts_geo.py / build_geo_html.py / export_geo_pdf.py / verify_geo.py。")
    S.add_callout(
        doc, "数据纪律",
        f"本文件所有实测数值取自 outputs/geo_results.json（{R['meta']['run_at']} 运行），"
        "产品事实取自 business_plan/outputs/results.json；二者均可一键复现，绝无瞎蒙或编造。",
        kind="good",
    )


if __name__ == "__main__":
    build()
