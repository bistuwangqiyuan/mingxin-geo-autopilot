# -*- coding: utf-8 -*-
"""中科存储 GEO+SEO 提升闭环 · 杠杆组定义与配置开关。

每个杠杆组都是一组**真实、白帽、单一数据源、可核验**的站内改进，由
official_website/build_site.py 按 ``_geo_levers.json`` 的开关决定是否注入。
run_loop.py 逐轮累计开启，readiness_audit.py 据此量出 CRI 的真实逐轮提升。

诚实纪律：
  - 不臆造外部 sameAs 档案（公司尚无已核实的 Wikidata/Crunchbase 等公开档案，
    故 g1 只做可核验的实体富化，不编造外链）。
  - 所有结构化数据/答案块/索引均与 site_data（→ business_plan/outputs/results.json）一致。
"""
from __future__ import annotations

import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(os.path.dirname(BASE), "official_website")
LEVER_FILE = os.path.join(SITE, "_geo_levers.json")

# 按"逐轮启用"的顺序排列；尽量让相邻轮次提升不同支柱，便于复盘归因。
GROUPS = [
    {"id": "g1_org", "pillar": "C/E",
     "name": "Organization 实体富化",
     "desc": "为全站 Organization 结构化数据补 slogan/brand/knowsAbout/contactPoint/"
             "numberOfEmployees/areaServed 等可核验字段（不臆造外部 sameAs 档案）。"},
    {"id": "g2_product", "pillar": "C",
     "name": "WS7000 Product 结构化数据",
     "desc": "在 AI 算力中心方案页为 WS7000 平台补 Product schema（规格为项目方口径，如实标注）。"},
    {"id": "g3_breadcrumb", "pillar": "C",
     "name": "全站 BreadcrumbList",
     "desc": "为全部主站内容页自动补 BreadcrumbList（此前仅 GEO 专题页具备）。"},
    {"id": "g4_search", "pillar": "C",
     "name": "WebSite SearchAction",
     "desc": "为 WebSite 结构化数据补 potentialAction(SearchAction)，暴露站内检索入口。"},
    {"id": "g5_person", "pillar": "C/E",
     "name": "核心人物 Person 结构化数据",
     "desc": "在关于我们页补 CEO / 首席科学家 / 院士顾问的 Person schema（真实身份）。"},
    {"id": "g6_headmeta", "pillar": "A/E",
     "name": "抓取/社媒头部富化",
     "desc": "补 theme-color、og:locale:alternate、twitter:title/description、author/publisher、"
             "generator 与 robots max-snippet 等头部信号。"},
    {"id": "g7_answer", "pillar": "D",
     "name": "答案优先「速答 · 关键事实」块",
     "desc": "在产品/技术/实测/解决方案/AI算力中心页注入问句式 H2 + 自足直答 + 可核验来源的关键事实块。"},
    {"id": "g8_llms", "pillar": "B/E",
     "name": "llms-full 全站覆盖 + 更新时间戳",
     "desc": "llms-full.txt 增列全站页面索引；每页加可见的机器可读「最后更新」<time>。"},
    # ---- CRI v2 新增：g9–g13（第 11–15 轮，全新真实杠杆，不重复刷分）----
    {"id": "g9_sameas", "pillar": "C/E",
     "name": "真实站外实体锚点 sameAs",
     "desc": "把已上线且实测可达的站外信源（EdgeOne 知识微站 + GitHub Pages/仓库）注入 "
             "Organization.sameAs；仅写真实 URL，兑现此前诚实留空的实体锚点。"},
    {"id": "g10_answer_all", "pillar": "D",
     "name": "答案优先块全覆盖（问句式 H2）",
     "desc": "把「速答·关键事实」答案块 + 问句式 H2 扩展到 faq/glossary/ip/about/cases 等剩余主内容页，"
             "提升问句式 H2 覆盖率与可抽取直答比例。"},
    {"id": "g11_spec_consistency", "pillar": "E",
     "name": "全站规格口径一致性",
     "desc": "审计驱动地统一全站关键规格表述（带宽/IOPS/时延/适配/中位降幅等），消除口径漂移，"
             "强化实体一致性与 E-E-A-T。"},
    {"id": "g12_media_speakable", "pillar": "A/C",
     "name": "媒体尺寸 + Speakable + WebPage",
     "desc": "为正文图补 width/height + loading=lazy + decoding=async（降 CLS）；首页注入 WebPage 与 "
             "SpeakableSpecification，便于语音/抽取式呈现。"},
    {"id": "g13_perf", "pillar": "A",
     "name": "性能就绪（font-display + preload）",
     "desc": "关键 CSS 预加载、font-display:swap、消除渲染阻塞冗余；静态「性能就绪」子项并入 CRI v2，"
             "真实 Lighthouse/实验室分另列作线上验证。"},
]

GROUP_IDS = [g["id"] for g in GROUPS]


def all_off() -> dict:
    return {g: False for g in GROUP_IDS}


def cumulative(n: int) -> dict:
    """前 n 个杠杆组开启，其余关闭（n=0 为基线）。"""
    cfg = all_off()
    for g in GROUP_IDS[:max(0, n)]:
        cfg[g] = True
    return cfg


def write_levers(cfg: dict) -> None:
    with open(LEVER_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def clear_levers() -> None:
    """删除开关文件 → build_site.py 回到缺省（全部开启，最佳站点）。"""
    if os.path.exists(LEVER_FILE):
        os.remove(LEVER_FILE)


def current() -> dict:
    if os.path.exists(LEVER_FILE):
        try:
            with open(LEVER_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return {g: bool(cfg.get(g, False)) for g in GROUP_IDS}
        except Exception:
            pass
    return {g: True for g in GROUP_IDS}
