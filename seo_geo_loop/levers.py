# -*- coding: utf-8 -*-
"""铭信 GEO+SEO 提升闭环 · 杠杆组定义（历史兼容 + 铭信口径）。

历史背景：旧架构下每个杠杆组是一组**真实、白帽、单一数据源、可核验**的站内改进，
由静态站生成器按 ``_geo_levers.json`` 开关注入，run_loop.py 逐轮累计开启并量出
CRI 的逐轮提升（历史产物见 outputs/loop_results*.json 与 snapshots/）。

现状（诚实说明）：铭信官网为 Next.js 站点（amd 仓库 site/ 子目录，Vercel 部署），
站内结构化数据/答案块/llms.txt 等由站点自身内容引擎负责，本仓库不再驱动静态重建。
本模块保留杠杆组定义作为「站内 GEO 检查清单」与历史产物的解读依据；开关读写函数
保留 API 兼容但不再产生副作用。

纪律：所有结构化数据/答案块/索引均须与单一事实源一致
（site_facts → business_plan/outputs/results.json ↔ 官网 company.ts）。
"""
from __future__ import annotations

# 按"逐轮启用"的历史顺序排列；现作为铭信站内 GEO 检查清单使用。
GROUPS = [
    {"id": "g1_org", "pillar": "C/E",
     "name": "Organization 实体富化",
     "desc": "全站 Organization 结构化数据补 slogan/brand/knowsAbout/contactPoint/"
             "areaServed 等可核验字段（铭信实体：铭信（天津）半导体设备有限公司，"
             "url=https://mingxinstorage.xyz；不臆造外部 sameAs 档案）。"},
    {"id": "g2_product", "pillar": "C",
     "name": "FX100 Product 结构化数据",
     "desc": "产品页为 FX100（FX 系列）补 Product schema，含 alternateName 命名沿革"
             "（AISSD5000/WS5000/GP5000，同一产品）；规格/价格为厂商口径，如实标注。"},
    {"id": "g3_breadcrumb", "pillar": "C",
     "name": "全站 BreadcrumbList",
     "desc": "为全部主站内容页补 BreadcrumbList。"},
    {"id": "g4_search", "pillar": "C",
     "name": "WebSite SearchAction",
     "desc": "为 WebSite 结构化数据补 potentialAction(SearchAction)，暴露站内检索入口。"},
    {"id": "g5_person", "pillar": "C/E",
     "name": "核心人物 Person 结构化数据",
     "desc": "在关于我们页补核心团队的 Person schema（真实身份）。"},
    {"id": "g6_headmeta", "pillar": "A/E",
     "name": "抓取/社媒头部富化",
     "desc": "补 theme-color、og:locale:alternate、twitter:title/description、author/publisher、"
             "generator 与 robots max-snippet 等头部信号。"},
    {"id": "g7_answer", "pillar": "D",
     "name": "答案优先「速答 · 关键事实」块",
     "desc": "在产品/证据/解决方案页注入问句式 H2 + 自足直答 + 可核验来源（R1–R9 编号）"
             "的关键事实块（吞吐 +29–40%、TTFT ↓26–32% 等签字级口径）。"},
    {"id": "g8_llms", "pillar": "B/E",
     "name": "llms-full 全站覆盖 + 更新时间戳",
     "desc": "llms-full.txt 增列全站页面索引；每页加可见的机器可读「最后更新」<time>。"},
    {"id": "g9_sameas", "pillar": "C/E",
     "name": "真实站外实体锚点 sameAs",
     "desc": "把已上线且实测可达的站外信源（EdgeOne 知识微站 + GitHub Pages 知识库 "
             "mingxin-storage-kb）注入 Organization.sameAs；仅写真实 URL。"},
    {"id": "g10_answer_all", "pillar": "D",
     "name": "答案优先块全覆盖（问句式 H2）",
     "desc": "把「速答·关键事实」答案块 + 问句式 H2 扩展到 faq/about 等剩余主内容页，"
             "提升问句式 H2 覆盖率与可抽取直答比例。"},
    {"id": "g11_spec_consistency", "pillar": "E",
     "name": "全站规格口径一致性",
     "desc": "审计驱动地统一全站关键指标表述（吞吐 +29–40%、TTFT ↓26–32%、对重算 8.6–20×、"
             "模型加载 6.2–9.3×（R9·昇腾平台标注）等），消除口径漂移、清零旧口径数字。"},
    {"id": "g12_media_speakable", "pillar": "A/C",
     "name": "媒体尺寸 + Speakable + WebPage",
     "desc": "为正文图补 width/height + loading=lazy + decoding=async（降 CLS）；首页注入 WebPage 与 "
             "SpeakableSpecification，便于语音/抽取式呈现。"},
    {"id": "g13_perf", "pillar": "A",
     "name": "性能就绪（font-display + preload）",
     "desc": "关键 CSS 预加载、font-display:swap、消除渲染阻塞冗余；线上真实性能另由 "
             "lighthouse_psi.py 验证。"},
]

GROUP_IDS = [g["id"] for g in GROUPS]


def all_off() -> dict:
    return {g: False for g in GROUP_IDS}


def cumulative(n: int) -> dict:
    """前 n 个杠杆组开启，其余关闭（n=0 为基线）。历史兼容。"""
    cfg = all_off()
    for g in GROUP_IDS[:max(0, n)]:
        cfg[g] = True
    return cfg


def write_levers(cfg: dict) -> None:  # noqa: ARG001
    """历史兼容 no-op：静态站构建链路已退役（铭信站为 Next.js/Vercel），
    不再写 _geo_levers.json 开关文件。"""
    return None


def clear_levers() -> None:
    """历史兼容 no-op（同上）。"""
    return None


def current() -> dict:
    """铭信站内优化由站点内容引擎持有，视为全部杠杆常开。"""
    return {g: True for g in GROUP_IDS}


if __name__ == "__main__":
    print("铭信站内 GEO 杠杆检查清单（站点为 Next.js/Vercel，由站点内容引擎负责落地）：")
    for g in GROUPS:
        print(f"  {g['id']:22s} [{g['pillar']:3s}] {g['name']}")
