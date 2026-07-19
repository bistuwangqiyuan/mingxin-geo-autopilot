# -*- coding: utf-8 -*-
"""铭信 GEO 计划 · 单一配置源（事实纪律）。

本文件集中存放 GEO 测量与建模的全部"可调参数与外部假设"，使每一个数字都
可追溯、可复现、可质疑：

  - BRAND_ALIASES / COMPETITORS：实体识别词表（用于提及率、排序位、SoV）。
  - MODELS：可编程真测（A 级）与需人工取证（B 级）的模型清单。
  - SOURCE_PREFERENCE：各国产大模型"答案来自哪里"的信源偏好矩阵（GEO 打法依据）。
  - GVI_WEIGHTS：GEO 可见性指数权重（公开、可调）。
  - LEVERS：提升杠杆的赔率系数与 P10/P50/P90 区间，全部标注外部来源编号 G1–G8。

外部来源（GEO 方法学，2026Q1 检索）：
  G1 serpbays.com/blog/what-is-geo-generative-engine-optimization（GEO 2026 指南）
  G2 citare.ai/geo（GEO 完整指南：5 引擎/4 索引、结构化数据/llms.txt/SoV 度量）
  G3 brandcited.ai/learn/geo-playbook（完整 schema 站点被引用 2–3×）
  G4 ayautomate.com/blog/how-to-get-cited-by-chatgpt-and-perplexity（答案优先 40–60 字）
  G5 shadow.inc/resources/get-cited-by-ai-search（robots 放行 + JSON-LD 提升信任评分）
  G6 Frase 厂商分析：完整 schema 站点在 Perplexity 回答中出现概率 +47%（经 G1/G4 转述）
  G7 火山引擎开发者社区 7625687701307523126（豆包/DeepSeek/千问 1200+ 组对照实测）
  G8 易云/灵猫/白杨 SEO 国产 AI 信源偏好对比（DeepSeek/豆包/元宝/文心/通义/Kimi）

纪律：LEVERS 系数为"规划假设区间"，非承诺；报告与图表必须如实标注其性质。
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. 实体识别词表
# ---------------------------------------------------------------------------
# 我方品牌别名（大小写不敏感匹配；含产品型号、历史称谓与主体名）
BRAND = "铭信"
BRAND_ALIASES = [
    "铭信", "Mingxin", "MingXin", "铭信科技", "铭信（天津）", "铭信(天津)",
    "FX100", "FX200", "FX300", "FX400", "FX 系列", "FX系列",
    "AISSD5000", "WS5000", "GP5000", "FX100-HBMM",
]

# 竞品 / 同场域厂商（用于 Share-of-Voice 与排序位）。分阵营便于解读。
COMPETITORS = {
    "华为 OceanStor": ["华为", "OceanStor", "海思", "昇腾存储", "FusionStorage"],
    "中科曙光 ParaStor": ["曙光", "ParaStor", "中科曙光", "FlashNexus"],
    "浪潮存储": ["浪潮", "Inspur", "AS13000", "浪潮信息"],
    "焱融科技 YRCloudFile": ["焱融", "YRCloudFile", "YRCLOUD"],
    "新华三 H3C": ["新华三", "H3C"],
    "XSKY 星辰天合": ["XSKY", "星辰天合"],
    "同有科技": ["同有科技", "同有"],
    "DDN": ["DDN", "DataDirect"],
    "VAST Data": ["VAST Data", "VAST"],
    "WEKA": ["WEKA", "WekaIO"],
    "Pure Storage": ["Pure Storage", "PureStorage", "FlashBlade"],
    "NetApp": ["NetApp"],
    "Dell": ["Dell", "戴尔", "PowerScale", "Isilon"],
    "阿里云": ["阿里云", "CPFS", "盘古存储"],
    "腾讯云": ["腾讯云"],
    "Alluxio": ["Alluxio"],
}

# ---------------------------------------------------------------------------
# 2. 模型清单
# ---------------------------------------------------------------------------
# A 级 = 可经 bl(DashScope OpenAI 兼容) 编程真测；harness 会逐一探测、失败即跳过并记录。
# 说明：DashScope 同时托管通义千问(qwen-*)与 DeepSeek(deepseek-*)，二者可真测。
MODELS_API = [
    {"key": "qwen-max", "vendor": "通义千问", "model": "qwen-max",
     "note": "通义千问旗舰，阿里生态/权威信源偏好的代表"},
    {"key": "qwen-plus", "vendor": "通义千问", "model": "qwen-plus",
     "note": "通义千问主力"},
    {"key": "qwen3.6-plus", "vendor": "通义千问", "model": "qwen3.6-plus",
     "note": "bl 默认新版"},
    {"key": "deepseek-v3", "vendor": "DeepSeek", "model": "deepseek-v3",
     "note": "DeepSeek 通用，B2B 技术主战场"},
    {"key": "deepseek-r1", "vendor": "DeepSeek", "model": "deepseek-r1",
     "note": "DeepSeek 推理版，重逻辑链/可验证"},
]

# B 级 = 无法直连，须用标准化人工取证协议（截图+文本+双人复核），不臆造数据。
MODELS_MANUAL = [
    {"key": "wenxin", "vendor": "文心一言", "ecosystem": "百度系"},
    {"key": "doubao", "vendor": "豆包", "ecosystem": "字节系"},
    {"key": "yuanbao", "vendor": "腾讯元宝", "ecosystem": "微信/腾讯系"},
    {"key": "kimi", "vendor": "Kimi", "ecosystem": "月之暗面"},
    {"key": "chatgpt", "vendor": "ChatGPT", "ecosystem": "OpenAI（二阶段/出海）"},
    {"key": "claude", "vendor": "Claude", "ecosystem": "Anthropic（二阶段/出海）"},
    {"key": "gemini", "vendor": "Gemini", "ecosystem": "Google（二阶段/出海）"},
    {"key": "perplexity", "vendor": "Perplexity", "ecosystem": "搜索增强（二阶段/出海）"},
]

# ---------------------------------------------------------------------------
# 3. 各大模型信源偏好矩阵（GEO 站外打法依据，来源 G7/G8）
# ---------------------------------------------------------------------------
# weight: 该信源对"被该模型引用"的相对重要度（0–1，主观先验，用于覆盖缺口加权）。
SOURCE_PREFERENCE = {
    "DeepSeek": {
        "primary": ["CSDN", "知乎技术区", "GitHub/GitCode", "技术白皮书", "arXiv/学术"],
        "secondary": ["博客园", "少数派", "InfoQ/机器之心"],
        "weak": ["纯电商页", "营销软文"],
        "schema_pref": ["TechArticle", "HowTo", "Dataset"],
        "weight": 1.0,
    },
    "通义千问": {
        "primary": ["权威媒体", "政府/教育网站(.gov/.edu)", "阿里云开发者社区", "语雀公开知识库", "官网(权威背书)"],
        "secondary": ["新浪财经", "认证媒体号"],
        "weak": ["社交平台碎片", "信息不一致页面"],
        "schema_pref": ["Organization", "FAQPage", "Article", "Product"],
        "weight": 0.95,
    },
    "文心一言": {
        "primary": ["百度百科", "百家号(蓝V)", "百度文库", "百度搜索高排名页"],
        "secondary": ["搜狐号", "垂直合作站"],
        "weak": ["小众独立站"],
        "schema_pref": ["FAQPage", "Article"],
        "weight": 0.9,
    },
    "豆包": {
        "primary": ["抖音", "今日头条", "百科", "搜狐号", "网易号"],
        "secondary": ["什么值得买", "懂车帝(垂类)"],
        "weak": ["独立官网"],
        "schema_pref": ["FAQPage", "VideoObject"],
        "weight": 0.8,
    },
    "腾讯元宝": {
        "primary": ["微信公众号", "微信读书", "腾讯新闻", "企鹅号"],
        "secondary": ["搜狗收录"],
        "weak": ["非微信生态"],
        "schema_pref": ["Article", "FAQPage"],
        "weight": 0.8,
    },
    "Kimi": {
        "primary": ["知乎长文(高赞)", "搜狐", "CSDN"],
        "secondary": ["少数派", "公众号"],
        "weak": ["纯营销页"],
        "schema_pref": ["Article", "FAQPage"],
        "weight": 0.75,
    },
}

# 我方当前站外信源覆盖（实事求是：官网 GEO 基础设施完备，站外沉淀起步期）。
# 取值 0–1：0=完全无覆盖，1=高质量持续覆盖。用于覆盖缺口分析的"现状"。
CURRENT_SOURCE_COVERAGE = {
    "独立官网": 0.85,          # mingxinstorage.xyz：robots/llms.txt/sitemap/schema/双语/内容引擎已就绪
    "CSDN": 0.0, "知乎技术区": 0.0, "GitHub/GitCode": 0.1, "技术白皮书": 0.5,
    "arXiv/学术": 0.0, "百度百科": 0.0, "百家号(蓝V)": 0.0, "百度文库": 0.0,
    "百度搜索高排名页": 0.1, "权威媒体": 0.0, "政府/教育网站(.gov/.edu)": 0.1,
    "阿里云开发者社区": 0.0, "语雀公开知识库": 0.0, "抖音": 0.0, "今日头条": 0.0,
    "百科": 0.0, "搜狐号": 0.0, "网易号": 0.0, "微信公众号": 0.1, "微信读书": 0.0,
    "腾讯新闻": 0.0, "企鹅号": 0.0, "知乎长文(高赞)": 0.0,
}

# ---------------------------------------------------------------------------
# 4. GEO 可见性指数 GVI（0–100）权重（公开、可调；和=1）
# ---------------------------------------------------------------------------
GVI_WEIGHTS = {
    "mention": 0.30,       # 是否被提及
    "first_rank": 0.25,    # 是否首位/排序靠前
    "share_of_voice": 0.20,  # 相对竞品的声量份额
    "citation": 0.15,      # 是否带来源/链接/可核验归因
    "accuracy": 0.10,      # 提及内容是否准确、正面、可核验
}

# ---------------------------------------------------------------------------
# 5. 提升杠杆（赔率乘子 odds-ratio，P10/P50/P90），全部标注外部来源
# ---------------------------------------------------------------------------
# 模型：被提及/被引用概率 p，以 odds = p/(1-p) 表示；每启用一个杠杆，odds 乘以该
# 杠杆的乘子（P50 为中值，P10/P90 为保守/乐观边界）。多杠杆 odds 连乘，再设可达
# 上限 ceiling 防止"必胜"幻觉。系数取自 GEO 公开研究的"区间下沿"，刻意保守。
LEVERS = {
    "crawler_access": {  # robots 放行 + 可被抓取（无此项=不可能被语料/检索引用）
        "name": "抓取放行(robots/sitemap)", "p10": 1.15, "p50": 1.35, "p90": 1.6,
        "src": "G5/G3：被抓取是被引用的前提，缺失则归零",
    },
    "structured_data": {  # JSON-LD @graph 完整 schema
        "name": "结构化数据(JSON-LD @graph)", "p10": 1.3, "p50": 1.6, "p90": 2.3,
        "src": "G6：完整 schema 在 Perplexity 出现概率 +47%；G3：被引用 2–3×（取下沿）",
    },
    "answer_first": {  # 答案优先 40–60 字自足段 + 问句标题
        "name": "答案优先内容结构", "p10": 1.15, "p50": 1.35, "p90": 1.7,
        "src": "G1/G4：自足段落被抽取/引用显著更高",
    },
    "llms_txt": {  # llms.txt / llms-full.txt（前瞻信号，弱）
        "name": "llms.txt 索引", "p10": 1.0, "p50": 1.08, "p90": 1.2,
        "src": "G1：尚非批准标准，作低成本前瞻信号（取近 1）",
    },
    "offsite_source": {  # 每覆盖一个该模型高权重信源平台的增益（按平台再加权）
        "name": "站外高权重信源覆盖(单平台)", "p10": 1.15, "p50": 1.3, "p90": 1.55,
        "src": "G7/G8：信源平台决定该模型可见性（按模型偏好加权）",
    },
    "entity_consistency": {  # 全网实体一致性（尤其利好通义）
        "name": "全网实体一致性", "p10": 1.05, "p50": 1.15, "p90": 1.3,
        "src": "G7：通义对信息冲突敏感，一致性提升采纳概率",
    },
}

# 被提及概率的现实上限（避免"全模型必第一"的乐观谬误）。
# 解释：即便满配 GEO，在宽口径类目里也不可能 100% 被点名第一。
P_CEILING = {"T1": 0.85, "T2": 0.65, "T3": 0.45}

# 类目阶梯定义（与 queries.json 的 tier 对应）
TIERS = {
    "T1": "最窄·最可防御（KV Cache 分层全闪 NVMe-oF 存储加速平台，480B 签字级实测）",
    "T2": "中口径（国产算力卡适配 + 算力中心建设/效能优化的存储加速服务商）",
    "T3": "宽口径（AI 存储加速 / AI 算力中心存储）",
}

# 复现随机种子（与 results.json 同源风格）
SEED = 20260719
