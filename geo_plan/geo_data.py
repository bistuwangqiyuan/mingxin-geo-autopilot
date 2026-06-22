# -*- coding: utf-8 -*-
"""中科存储 GEO 提升计划 · 单一数据源（Single Source of Truth）。

设计原则
--------
1. 单一数据源：产品事实数值统一取自 business_plan/outputs/results.json（与商业
   计划书 / 公司简介 / 官网同源），绝不在本文件内另行编造。
2. 可复现：本模块只定义"输入"（类目锚定、查询篮、竞品别名、引擎注册表、评分
   权重、杠杆清单、阶段目标、引用登记册）与"判定函数"，不产生随机数；所有
   实测结果由 geo_measure.py 真实跑出、scoring.py 计算。
3. 实事求是：引擎是否"现在可实测"如实标注；无密钥/服务不可用者标注"待复测"，
   绝不编造排名或被提及率。

被 geo_measure.py / scoring.py / charts_geo.py / build_geo_html.py 共同导入。
"""
from __future__ import annotations

import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
BP_DIR = os.path.join(os.path.dirname(BASE), "business_plan")
RESULTS = os.path.join(BP_DIR, "outputs", "results.json")

OUT_DIR = os.path.join(BASE, "outputs")
FIG_DIR = os.path.join(BASE, "figures")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)

# 采集口径日期（联网核查现状的日期，写入文档以示可追溯）
SURVEY_DATE = "2026-06-21"

BRAND_ZH = "中科存储"
BRAND_EN = "ZK-Storage"
ENTITY_ZH = "深圳市中科航星科技有限公司"
PRODUCT_MODEL = "WS5000（WS-HBMM5000）"


# ---------------------------------------------------------------------------
# 产品事实（单一数据源）
# ---------------------------------------------------------------------------
def load_results():
    with open(RESULTS, "r", encoding="utf-8") as f:
        return json.load(f)


def ground_truth_facts():
    """从 results.json 取产品关键事实，用于"事实准确率/幻觉"核对与文档展示。"""
    R = load_results()
    p = R["product"]
    return {
        "bandwidth_gbps": p["bandwidth_gbps"],            # 300
        "iops_wan": int(round(p["iops_million"] * 100)),   # 5000（万）
        "latency_us": p["latency_us"],                     # 20
        "gpu_adaptation_pct": int(round(p["gpu_adaptation"] * 100)),  # 90
        "deploy_hours": p["deploy_hours"],                 # 48-72
        "cost_reduction_pct": int(round(p["cost_reduction"] * 100)),  # 40
        "kv_cache_save_pct": round(p.get("kv_cache_cost_save", 0) * 100, 1),
    }


# ---------------------------------------------------------------------------
# 一、细分类目锚定（双靶点）
# ---------------------------------------------------------------------------
CATEGORIES = {
    "narrow": {
        "key": "narrow",
        "name_zh": "国产·存算分离全闪 + KV Cache 卸载 + 国产GPU深度适配的推理存储一体机",
        "name_en": "Domestic disaggregated all-flash + KV Cache offload inference storage appliance",
        "rationale": (
            "在该精确细分中，竞争集合小、技术壁垒与国产适配壁垒高，是中科存储"
            "可凭差异化（存算分离全闪 × KV Cache 卸载 × 昇腾/寒武纪深度适配 × "
            "大湾区成本）真实争得第一、且客观可检验的靶点。"
        ),
        "anchor_keywords_zh": ["存算分离", "全闪存储", "KV Cache 卸载", "国产GPU适配",
                               "昇腾", "寒武纪", "推理存储一体机", "GPU 利用率"],
    },
    "broad": {
        "key": "broad",
        "name_zh": "国产 AI 存储 / AI 存储加速",
        "name_en": "Domestic AI storage / AI storage acceleration",
        "rationale": (
            "宽口径被华为、浪潮、新华三、深信服、曙光、焱融等巨头主导（公开口径"
            "华为份额居前）。诚实目标是多年可见度爬坡——进入 AI 回答的被提及/被"
            "推荐集合并爬升 Top-N，而非短期声称第一。"
        ),
        "anchor_keywords_zh": ["AI 存储", "全闪存储", "分布式存储", "高性能存储", "智算存储"],
    },
}


# ---------------------------------------------------------------------------
# 二、品牌与竞品别名（用于"被提及 / 声量份额"判定）
# ---------------------------------------------------------------------------
SELF_ALIASES = [
    "中科存储", "ZK-Storage", "ZK Storage", "ZKStorage",
    "中科航星", "Zhongke Hangxing",
    "WS5000", "WS-HBMM5000", "WS-HBMM", "WS7000", "HBMM5000",
]

# 竞品集合（宽类目主流 + 海外对照）。每个竞品给出别名用于子串匹配。
COMPETITORS = {
    "huawei": {"name_zh": "华为", "aliases": ["华为", "Huawei", "OceanStor", "FusionStorage"]},
    "sugon": {"name_zh": "中科曙光", "aliases": ["曙光", "Sugon", "ParaStor", "FlashNexus"]},
    "yanrong": {"name_zh": "焱融科技", "aliases": ["焱融", "YanRong", "YRCloudFile", "F9000X"]},
    "inspur": {"name_zh": "浪潮", "aliases": ["浪潮", "Inspur", "AS13000"]},
    "h3c": {"name_zh": "新华三", "aliases": ["新华三", "H3C", "UniStor"]},
    "sangfor": {"name_zh": "深信服", "aliases": ["深信服", "Sangfor", "EDS"]},
    "vast": {"name_zh": "VAST Data", "aliases": ["VAST Data", "VAST"]},
    "weka": {"name_zh": "WEKA", "aliases": ["WEKA", "WekaIO", "WekaFS"]},
    "ddn": {"name_zh": "DDN", "aliases": ["DDN", "DataDirect"]},
    "xsky": {"name_zh": "XSKY 星辰天合", "aliases": ["XSKY", "星辰天合"]},
}


# ---------------------------------------------------------------------------
# 三、查询篮（中英 × 四类意图 × 窄/宽类目）
# ---------------------------------------------------------------------------
# type: info(信息型) / commercial(商业型) / comparison(对比型) / ranking(排名型)
QUERY_BASKET = [
    # —— 窄类目 · 中文 ——
    {"id": "n_zh_info", "lang": "zh", "type": "info", "category": "narrow",
     "text": "什么是面向 AI 推理的 KV Cache 卸载、存算分离全闪存储加速一体机？它解决什么问题？"},
    {"id": "n_zh_comm", "lang": "zh", "type": "commercial", "category": "narrow",
     "text": "为 AI 推理做 KV Cache 卸载、存算分离全闪存储加速的一体机，有哪些厂商可以推荐？请列出厂商与代表产品。"},
    {"id": "n_zh_cmp", "lang": "zh", "type": "comparison", "category": "narrow",
     "text": "国产、支持 KV Cache 卸载、并深度适配昇腾/寒武纪国产 GPU 的存算分离全闪存储一体机有哪些？分别有什么特点？"},
    {"id": "n_zh_rank", "lang": "zh", "type": "ranking", "category": "narrow",
     "text": "面向国产 GPU（昇腾/寒武纪）推理的存算分离全闪 KV Cache 卸载存储一体机，哪家做得最好？给出排序与理由。"},
    # —— 窄类目 · 英文 ——
    {"id": "n_en_info", "lang": "en", "type": "info", "category": "narrow",
     "text": "What is a KV Cache offloading, disaggregated all-flash storage appliance for AI inference, and what problem does it solve?"},
    {"id": "n_en_comm", "lang": "en", "type": "commercial", "category": "narrow",
     "text": "Which vendors offer disaggregated all-flash storage with KV Cache offload for AI inference on domestic Chinese GPUs (Ascend/Cambricon)? List vendors and products."},
    # —— 宽类目 · 中文 ——
    {"id": "b_zh_info", "lang": "zh", "type": "info", "category": "broad",
     "text": "什么是面向 AI 大模型训练与推理的高性能全闪/分布式存储？"},
    {"id": "b_zh_comm", "lang": "zh", "type": "commercial", "category": "broad",
     "text": "AI 训练和推理的高性能全闪/分布式存储，国产厂商推荐哪些？请列出厂商与代表产品。"},
    {"id": "b_zh_cmp", "lang": "zh", "type": "comparison", "category": "broad",
     "text": "国产 AI 存储厂商有哪些？各自的技术路线和特点是什么？"},
    {"id": "b_zh_rank", "lang": "zh", "type": "ranking", "category": "broad",
     "text": "在国产 AI 存储/AI 存储加速领域，排名靠前的厂商有哪些？请给出大致排序。"},
    # —— 宽类目 · 英文 ——
    {"id": "b_en_comm", "lang": "en", "type": "commercial", "category": "broad",
     "text": "Recommend high-performance all-flash / distributed storage vendors for AI training and inference in China. List vendors and products."},
    {"id": "b_en_rank", "lang": "en", "type": "ranking", "category": "broad",
     "text": "Who are the leading AI storage vendors in China? Give an approximate ranking."},
]


# ---------------------------------------------------------------------------
# 四、AI 引擎注册表（可插拔；如实标注是否现在可实测）
# ---------------------------------------------------------------------------
# adapter: "bl_chat"(现在可用) / "openai" / "anthropic" / "gemini" / "perplexity" /
#          "deepseek" / "dashscope_other"...（需密钥，未配置时优雅跳过）
ENGINES = [
    {"key": "qwen-max", "label": "通义千问 Max", "vendor": "阿里巴巴",
     "adapter": "bl_chat", "model": "qwen-max", "reachable_now": True,
     "note": "经 bl(DashScope) 实测（旗舰）"},
    {"key": "qwen-plus", "label": "通义千问 Plus", "vendor": "阿里巴巴",
     "adapter": "bl_chat", "model": "qwen-plus", "reachable_now": True,
     "note": "经 bl(DashScope) 实测"},
    {"key": "web_retrieval", "label": "联网检索可见度（DashScope WebSearch）",
     "vendor": "检索探针", "adapter": "bl_search", "model": "websearch",
     "reachable_now": True, "note": "反映 RAG 类引擎可检索到的可见度；服务异常时标注‘待复测’"},
    # —— 以下需用户提供 API 密钥后复测；无密钥时如实标注、绝不编造 ——
    {"key": "gpt", "label": "ChatGPT (GPT)", "vendor": "OpenAI", "adapter": "openai",
     "model": "gpt-4o", "reachable_now": False, "env_key": "OPENAI_API_KEY",
     "note": "待密钥复测"},
    {"key": "claude", "label": "Claude", "vendor": "Anthropic", "adapter": "anthropic",
     "model": "claude-3-7-sonnet", "reachable_now": False, "env_key": "ANTHROPIC_API_KEY",
     "note": "待密钥复测"},
    {"key": "gemini", "label": "Gemini", "vendor": "Google", "adapter": "gemini",
     "model": "gemini-2.5-pro", "reachable_now": False, "env_key": "GEMINI_API_KEY",
     "note": "待密钥复测"},
    {"key": "perplexity", "label": "Perplexity", "vendor": "Perplexity", "adapter": "perplexity",
     "model": "sonar", "reachable_now": False, "env_key": "PERPLEXITY_API_KEY",
     "note": "待密钥复测"},
    {"key": "deepseek", "label": "DeepSeek", "vendor": "深度求索", "adapter": "openai_compat",
     "model": "deepseek-chat", "reachable_now": False, "env_key": "DEEPSEEK_API_KEY",
     "note": "待密钥复测"},
    {"key": "doubao", "label": "豆包 (Doubao)", "vendor": "字节跳动", "adapter": "openai_compat",
     "model": "doubao-pro", "reachable_now": False, "env_key": "ARK_API_KEY",
     "note": "待密钥复测"},
    {"key": "ernie", "label": "文心一言 (ERNIE)", "vendor": "百度", "adapter": "qianfan",
     "model": "ernie-4.5", "reachable_now": False, "env_key": "QIANFAN_API_KEY",
     "note": "待密钥复测"},
    {"key": "kimi", "label": "Kimi", "vendor": "月之暗面", "adapter": "openai_compat",
     "model": "moonshot-v1", "reachable_now": False, "env_key": "MOONSHOT_API_KEY",
     "note": "待密钥复测"},
    {"key": "glm", "label": "智谱 GLM", "vendor": "智谱 AI", "adapter": "openai_compat",
     "model": "glm-4.5", "reachable_now": False, "env_key": "ZHIPU_API_KEY",
     "note": "待密钥复测"},
    {"key": "yuanbao", "label": "腾讯元宝 (Hunyuan)", "vendor": "腾讯", "adapter": "hunyuan",
     "model": "hunyuan-turbo", "reachable_now": False, "env_key": "HUNYUAN_API_KEY",
     "note": "待密钥复测"},
]

# 实测重复采样次数（统计稳定性；可调）。
REPEATS = 2


# ---------------------------------------------------------------------------
# 五、GEO 指数评分权重（公开、可调）
# ---------------------------------------------------------------------------
SCORING_WEIGHTS = {
    "mention_rate": 0.30,        # 被提及率
    "recommendation_rate": 0.30, # 被推荐率（商业/排名意图）
    "sov": 0.20,                 # 相对竞品的声量份额
    "rank_score": 0.15,          # 排名位次得分（越靠前越高）
    "citation_rate": 0.05,       # 引用官网域名率
}
RANK_CAP = 8  # 排名得分归一化的位次上限


# ---------------------------------------------------------------------------
# 六、四大杠杆工作流（含现状自审清单，score = done/total*5，可复现）
# ---------------------------------------------------------------------------
# 现状由 2026-06-21 对官网与公开检索的核查得出（如实记录）：
# 官网为纯静态站（利于 SSR/速度），但无 robots.txt / llms.txt / sitemap /
# JSON-LD schema / sameAs；公开检索几乎检索不到中科存储独立条目。
LEVERS = {
    "WS1": {
        "name": "实体接地（让模型认得清是谁）",
        "goal": "建立可被各引擎一致识别的品牌实体，杜绝与同名/竞品混淆。",
        "checklist": [
            {"item": "Wikidata 实体 Q-ID 建立并填充关系（行业/产品/创始人/总部）", "done": False},
            {"item": "百度百科 / 维基百科 词条收录", "done": False},
            {"item": "官网 schema.org Organization + sameAs 数组（领英/天眼查/企查查/GitHub/媒体）", "done": False},
            {"item": "全网 NAP（名称/地址/电话）一致性核对", "done": False},
            {"item": "固定 100 字中英规范简介作为‘事实基准’全网统一", "done": False},
            {"item": "天眼查/企查查/工商信息与官网口径一致", "done": True},
        ],
    },
    "WS2": {
        "name": "技术可达性（让爬虫进得来、读得懂）",
        "goal": "让 AI 爬虫可抓取、可解析、可快速加载。",
        "checklist": [
            {"item": "robots.txt 放行 GPTBot/ClaudeBot/PerplexityBot/Google-Extended/Bytespider 等", "done": False},
            {"item": "根目录 llms.txt（精选页索引）", "done": False},
            {"item": "llms-full.txt（技术站点正文内联）", "done": False},
            {"item": "sitemap.xml 提交主流站长平台", "done": False},
            {"item": "服务端渲染/纯静态（首屏可直接解析）", "done": True},
            {"item": "FCP < 1s 的加载性能", "done": True},
        ],
    },
    "WS3": {
        "name": "结构化内容（让回答抽得出、引得到）",
        "goal": "以答案胶囊 + 结构化标注，提升被抽取与被引用概率。",
        "checklist": [
            {"item": "关键页 40–60 字‘答案胶囊’开篇 + 问题式标题", "done": False},
            {"item": "FAQPage JSON-LD（5–7 问）", "done": False},
            {"item": "Article + Product/TechArticle JSON-LD 叠加", "done": False},
            {"item": "‘What is WS5000 / 什么是中科存储’定义页", "done": False},
            {"item": "对比页（vs 曙光/焱融/华为，配 ItemList schema）", "done": False},
            {"item": "第三方实测/基准数据页（含来源与口径）", "done": True},
        ],
    },
    "WS4": {
        "name": "站外权威（让模型信得过）",
        "goal": "在中立高权威域形成跨源一致的品牌事实，强化实体可信度。",
        "checklist": [
            {"item": "行业媒体（存储在线/至顶网/电子发烧友）报道与收录", "done": False},
            {"item": "知乎/CSDN/掘金等技术内容沉淀", "done": False},
            {"item": "GitHub 白皮书 / 技术文档公开", "done": False},
            {"item": "MLPerf Storage / IO500 / SPC-1 式独立基准参与", "done": False},
            {"item": "第三方实测报告（北京信息科技大学）成为可引用资产", "done": True},
            {"item": "专利与院士顾问背书的合规呈现", "done": True},
        ],
    },
}


def lever_scores():
    """由 checklist 计算 0–5 的就绪度（done/total*5），可复现、可追溯。"""
    out = {}
    for k, v in LEVERS.items():
        items = v["checklist"]
        done = sum(1 for it in items if it["done"])
        out[k] = {
            "name": v["name"],
            "done": done,
            "total": len(items),
            "score5": round(done / len(items) * 5, 2),
        }
    return out


# ---------------------------------------------------------------------------
# 七、分阶段可检验目标（GEO 指数靶点；T0 由实测填入）
# ---------------------------------------------------------------------------
# 目标为‘靶点’而非承诺；方向性依据见 SOURCES（llms.txt≈14天+32%覆盖、完整
# schema≈+40% AI 概览出现率）——标注为方向性证据，不构成名次保证。
STAGE_TARGETS = {
    "stages": ["T0 基线", "30 天", "90 天", "180 天", "365 天"],
    "narrow": [None, 15, 40, 65, 80],   # T0 由实测填入
    "broad": [None, 5, 15, 30, 45],
    "milestones": [
        "如实记录起点（预期近零）",
        "技术就绪：robots/llms.txt/sitemap/schema/实体脚手架上线",
        "窄类目进入被推荐集合；宽类目开始被提及",
        "窄类目稳定进入被推荐/被提及第一梯队（争第一可证伪靶点）",
        "窄类目实测第一并复现；宽类目稳定进入 Top-N",
    ],
}


# ---------------------------------------------------------------------------
# 八、引用登记册（GEO 方法与现状证据来源）
# ---------------------------------------------------------------------------
SOURCES = {
    "G1": "LLMReach, What is Generative Engine Optimization (GEO)? The Complete 2026 Guide, llmreach.ai, 2026.",
    "G2": "Erlin.ai, 15 Generative Engine Optimization Best Practices Backed by Latest Research（含 llms.txt 部署约 14 天 +32% AI 覆盖的方向性数据）, 2026.",
    "G3": "Averi.ai, The Definitive Guide to GEO: Get Cited by AI in 2026（完整 Tier-1 schema 约 +40% AI 概览出现率；答案胶囊 40–60 字）, 2026.",
    "G4": "SerpBays, GEO 2026: The Generative Engine Optimization Guide（实体栈：Wikidata Q-ID + sameAs + 维基/百科 + 跨源一致）, 2026.",
    "G5": "llmclicks.ai, Generative Engine Optimization (GEO) Playbook for SaaS（Product/FAQ/TechArticle schema、NAP 一致、规范化描述）, 2026.",
    "C1": "存储在线 dostor.com,《2 亿 IOPS 背后，中科曙光 FlashNexus 9000》, 2026-05.",
    "C2": "焱融科技,《3 节点集群带宽突破 513GB/s，焱融存储再度登顶 MLPerf Storage 全球榜单》, 2025-08.",
    "C3": "CSDN,《2026 国内主流存储厂商全解析》（华为/浪潮/新华三/深信服 第一方阵；IDC 文件存储份额口径）, 2026-06.",
    "C4": "简米科技,《国内存储服务器品牌排行榜 2026》（华为市占居前的公开口径）, 2026.",
    "S38": "北京信息科技大学，华为昇腾 Atlas 910B 平台第三方独立实测报告（以 NFS 为基线），见 business_plan/sources.py。",
    "DS": "中科存储产品事实：business_plan/outputs/results.json（与商业计划书/官网同源）。",
    "SV": f"现状核查：{SURVEY_DATE} 对官网源码与公开搜索引擎的核查（官网无 robots/llms/sitemap/schema；品牌独立检索条目稀少）。",
}


# ---------------------------------------------------------------------------
# 九、判定函数（被 measure 与 scoring 共用）
# ---------------------------------------------------------------------------
def _first_index(text_l, aliases):
    """返回任一别名在文本中首次出现的位置（找不到返回 None）。"""
    idxs = [text_l.find(a.lower()) for a in aliases]
    idxs = [i for i in idxs if i >= 0]
    return min(idxs) if idxs else None


def detect_mentions(text, query_type):
    """对一条回答做实体提及/排名/推荐/引用判定，返回结构化结果。

    口径（如实、保守）：
    - mention：自家任一别名出现于回答中。
    - rank：在所有出现的厂商（自家+竞品）中，按首次出现位置排序后自家的名次。
    - recommended：仅对 commercial/ranking 意图计：被提及即视为被推荐进入候选集
      （info/comparison 记为 None，不计入被推荐率）。
    - citation：回答中出现指向自家官网域名的链接 token。
    - competitor_hits：各竞品是否被提及（用于 SoV）。
    """
    text_l = (text or "").lower()
    self_idx = _first_index(text_l, [a.lower() for a in SELF_ALIASES])
    self_mention = self_idx is not None

    comp_first = {}
    for key, c in COMPETITORS.items():
        idx = _first_index(text_l, [a.lower() for a in c["aliases"]])
        if idx is not None:
            comp_first[key] = idx

    # 排名：自家在‘自家+竞品’首次出现序列中的位次
    order = []
    if self_mention:
        order.append(("__self__", self_idx))
    for k, idx in comp_first.items():
        order.append((k, idx))
    order.sort(key=lambda x: x[1])
    rank = None
    if self_mention:
        rank = [i for i, (k, _) in enumerate(order, start=1) if k == "__self__"][0]

    # 被推荐（仅商业/排名意图）
    if query_type in ("commercial", "ranking"):
        recommended = self_mention
    else:
        recommended = None

    # 引用官网域名（保守：必须是 URL/域名 token，而非品牌名）
    citation_tokens = ["zk-storage", "zkstorage", "zhongke", "中科存储官网", "://"]
    has_url = "://" in text_l
    cited = has_url and any(t in text_l for t in ["zk-storage", "zkstorage", "zhongke"])

    return {
        "self_mention": self_mention,
        "rank": rank,
        "recommended": recommended,
        "cited": bool(cited),
        "competitor_hits": {k: True for k in comp_first},
        "n_competitors_mentioned": len(comp_first),
    }


def reachable_engines():
    return [e for e in ENGINES if e.get("reachable_now")]


def pending_engines():
    return [e for e in ENGINES if not e.get("reachable_now")]


if __name__ == "__main__":
    f = ground_truth_facts()
    print("Ground-truth facts:", f)
    print("Lever scores:", lever_scores())
    print(f"Queries: {len(QUERY_BASKET)} | Engines reachable now: {len(reachable_engines())} | pending: {len(pending_engines())}")
