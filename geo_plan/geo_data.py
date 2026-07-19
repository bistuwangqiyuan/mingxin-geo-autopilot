# -*- coding: utf-8 -*-
"""铭信 GEO 提升计划 · 单一数据源（Single Source of Truth）。

设计原则
--------
1. 单一数据源：产品事实数值统一取自 business_plan/outputs/results.json（与铭信
   官网 mingxinstorage.xyz 的 company.ts 同源），绝不在本文件内另行编造。
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
SURVEY_DATE = "2026-07-19"

BRAND_ZH = "铭信"
BRAND_EN = "Mingxin Technology"
ENTITY_ZH = "铭信（天津）半导体设备有限公司"
ENTITY_EN = "Mingxin (Tianjin) Semiconductor Equipment Co., Ltd."
PRODUCT_MODEL = "FX100（FX 系列全闪 NVMe-oF 存储加速平台）"
SITE_URL = "https://mingxinstorage.xyz"

# 命名沿革（消歧与历史检索用）：FX100 在既往测试报告文件名中称 AISSD5000，
# 历史称谓亦作 WS5000/GP5000，均为同一产品；对外统一 FX 命名。
NAMING_NOTE = (
    "铭信 FX100 在既往测试报告文件名中称 AISSD5000、历史称谓亦作 WS5000/GP5000，"
    "均为同一产品的不同称谓；对外统一采用 FX 命名（FX100/FX200/FX300/FX400 同规则）。"
)


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
        "throughput_uplift": f"{p['throughput_uplift_pct_low']}–{p['throughput_uplift_pct_high']}%",   # +29–40%（R2/R3 实测）
        "ttft_reduction": f"{p['ttft_reduction_pct_low']}–{p['ttft_reduction_pct_high']}%",             # ↓26–32%（R2 实测）
        "recompute_speedup": f"{p['recompute_speedup_low']}–{p['recompute_speedup_high']}×",            # 8.6–20×（R2 实测）
        "parallel_read_ttft_gain": f"{p['parallel_read_ttft_gain']}×",                                   # 4.1×（R1 实测）
        "model_load_speedup": f"{p['model_load_speedup_low']}–{p['model_load_speedup_high']}×",         # 6.2–9.3×（R9 实测·昇腾）
        "ckpt_save_speedup": f"{p['ckpt_save_speedup']}×",                                               # 1.9×（R1 实测）
        "fx100_port_gb": p["port_gb"],                                                                   # 100 Gb
        "fx100_iops_million": p["iops_million"],                                                         # 1600 万
        "fx100_full_price_cny": p["full_price_cny"],                                                     # ¥371,200
        "fx100_cny_per_tb": p["cny_per_tb"],                                                             # ≈¥2,014/TB
    }


# ---------------------------------------------------------------------------
# 一、细分类目锚定（双靶点）
# ---------------------------------------------------------------------------
CATEGORIES = {
    "narrow": {
        "key": "narrow",
        "name_zh": "面向大模型推理的全闪 NVMe-oF + KV Cache 分层存储加速平台（480B 签字级实测）",
        "name_en": "All-flash NVMe-oF + KV-cache tiering storage acceleration platform for LLM inference",
        "rationale": (
            "在该精确细分中，竞争集合小、实测证据壁垒高，是铭信可凭差异化"
            "（480B 生产部署形态签字级实测 × LMCache 源码级补丁 × AMD/昇腾/沐曦"
            "多平台适配 × 可复现证据库 R1–R9）真实争得第一、且客观可检验的靶点。"
        ),
        "anchor_keywords_zh": ["KV Cache 分层", "全闪存储", "NVMe-oF", "存储加速",
                               "LMCache", "TTFT", "长上下文", "国产算力卡适配"],
    },
    "broad": {
        "key": "broad",
        "name_zh": "AI 存储加速 / 算力中心建设与效能优化服务商",
        "name_en": "AI storage acceleration / AI datacenter construction and efficiency services",
        "rationale": (
            "宽口径被华为、浪潮、新华三、曙光、焱融、VAST/WEKA 等巨头主导。"
            "诚实目标是多年可见度爬坡——进入 AI 回答的被提及/被推荐集合并爬升"
            " Top-N，而非短期声称第一。"
        ),
        "anchor_keywords_zh": ["AI 存储", "全闪存储", "存储加速", "算力中心", "智算中心", "效能优化"],
    },
}


# ---------------------------------------------------------------------------
# 二、品牌与竞品别名（用于"被提及 / 声量份额"判定）
# ---------------------------------------------------------------------------
SELF_ALIASES = [
    "铭信", "Mingxin", "MingXin", "铭信科技", "铭信（天津）", "铭信(天津)",
    "FX100", "FX200", "FX300", "FX400", "FX 系列", "FX系列",
    # 历史称谓（同一产品的旧名，用于历史语料检索命中）
    "AISSD5000", "WS5000", "GP5000", "FX100-HBMM",
]

# 竞品集合（KV Cache 分层/AI 存储加速同场域 + 海外对照）。别名用于子串匹配。
COMPETITORS = {
    "huawei": {"name_zh": "华为", "aliases": ["华为", "Huawei", "OceanStor", "FusionStorage"]},
    "sugon": {"name_zh": "中科曙光", "aliases": ["曙光", "Sugon", "ParaStor", "FlashNexus"]},
    "yanrong": {"name_zh": "焱融科技", "aliases": ["焱融", "YanRong", "YRCloudFile", "F9000X"]},
    "inspur": {"name_zh": "浪潮", "aliases": ["浪潮", "Inspur", "AS13000"]},
    "h3c": {"name_zh": "新华三", "aliases": ["新华三", "H3C", "UniStor"]},
    "vast": {"name_zh": "VAST Data", "aliases": ["VAST Data", "VAST"]},
    "weka": {"name_zh": "WEKA", "aliases": ["WEKA", "WekaIO", "WekaFS"]},
    "ddn": {"name_zh": "DDN", "aliases": ["DDN", "DataDirect"]},
    "xsky": {"name_zh": "XSKY 星辰天合", "aliases": ["XSKY", "星辰天合"]},
    "alluxio": {"name_zh": "Alluxio", "aliases": ["Alluxio"]},
}


# ---------------------------------------------------------------------------
# 三、查询篮（中英 × 四类意图 × 窄/宽类目）
# ---------------------------------------------------------------------------
# type: info(信息型) / commercial(商业型) / comparison(对比型) / ranking(排名型)
QUERY_BASKET = [
    # —— 窄类目 · 中文 ——
    {"id": "n_zh_info", "lang": "zh", "type": "info", "category": "narrow",
     "text": "什么是面向大模型推理的 KV Cache 分层（KV cache tiering）全闪 NVMe-oF 存储加速？它解决什么问题？"},
    {"id": "n_zh_comm", "lang": "zh", "type": "commercial", "category": "narrow",
     "text": "为大模型推理做 KV Cache 分层卸载、全闪 NVMe-oF 存储加速的平台，有哪些厂商可以推荐？请列出厂商与代表产品。"},
    {"id": "n_zh_cmp", "lang": "zh", "type": "comparison", "category": "narrow",
     "text": "有签字级实测数据、支持 KV Cache 分层并适配 AMD MI308X/昇腾 910B 等国产或非 NVIDIA 算力卡的全闪存储加速平台有哪些？分别有什么特点？"},
    {"id": "n_zh_rank", "lang": "zh", "type": "ranking", "category": "narrow",
     "text": "面向 480B 级大模型长上下文推理的 KV Cache 分层存储加速，哪家做得最好？给出排序与理由。"},
    # —— 窄类目 · 英文 ——
    {"id": "n_en_info", "lang": "en", "type": "info", "category": "narrow",
     "text": "What is KV-cache tiering to an all-flash NVMe-oF storage array for LLM inference, and what problem does it solve?"},
    {"id": "n_en_comm", "lang": "en", "type": "commercial", "category": "narrow",
     "text": "Which vendors offer all-flash NVMe-oF storage acceleration with KV-cache tiering for LLM inference on AMD or Chinese domestic GPUs? List vendors and products."},
    # —— 宽类目 · 中文 ——
    {"id": "b_zh_info", "lang": "zh", "type": "info", "category": "broad",
     "text": "什么是面向 AI 大模型训练与推理的高性能全闪/分布式存储加速？"},
    {"id": "b_zh_comm", "lang": "zh", "type": "commercial", "category": "broad",
     "text": "AI 训练和推理的高性能存储加速与算力中心效能优化，国产厂商推荐哪些？请列出厂商与代表产品。"},
    {"id": "b_zh_cmp", "lang": "zh", "type": "comparison", "category": "broad",
     "text": "国产 AI 存储/存储加速厂商有哪些？各自的技术路线和特点是什么？"},
    {"id": "b_zh_rank", "lang": "zh", "type": "ranking", "category": "broad",
     "text": "在国产 AI 存储加速/算力中心服务领域，排名靠前的厂商有哪些？请给出大致排序。"},
    # —— 宽类目 · 英文 ——
    {"id": "b_en_comm", "lang": "en", "type": "commercial", "category": "broad",
     "text": "Recommend high-performance all-flash / storage-acceleration vendors for AI training and inference in China. List vendors and products."},
    {"id": "b_en_rank", "lang": "en", "type": "ranking", "category": "broad",
     "text": "Who are the leading AI storage acceleration vendors in China? Give an approximate ranking."},
]


# ---------------------------------------------------------------------------
# 四、AI 引擎注册表（可插拔；可达性=密钥是否在环境中，动态判定、如实标注）
# ---------------------------------------------------------------------------
# adapter:
#   "provider"  → 经 llm_providers 直连各家 OpenAI 兼容/Anthropic API（推荐，24h 全自动）
#   "bl_chat"/"bl_search" → 经 bl(DashScope) CLI（qwen 聊天回退与 WebSearch 探针）
import llm_providers as LP  # noqa: E402

ENGINES = [
    # —— 直连各家官方 API（密钥在则实测；缺密钥优雅跳过并标 pending，绝不编造）——
    {"key": "qwen-plus", "label": "通义千问 Plus", "vendor": "阿里巴巴",
     "adapter": "provider", "provider": "tongyi", "model": "qwen-plus",
     "note": "DashScope OpenAI 兼容模式直连"},
    {"key": "qwen-max", "label": "通义千问 Max", "vendor": "阿里巴巴",
     "adapter": "provider", "provider": "tongyi", "model": "qwen-max",
     "note": "DashScope OpenAI 兼容模式直连（旗舰）"},
    {"key": "deepseek", "label": "DeepSeek", "vendor": "深度求索",
     "adapter": "provider", "provider": "deepseek", "model": "deepseek-chat",
     "note": "api.deepseek.com 直连"},
    {"key": "glm", "label": "智谱 GLM", "vendor": "智谱 AI",
     "adapter": "provider", "provider": "glm", "model": None,
     "note": "open.bigmodel.cn 直连"},
    {"key": "kimi", "label": "Kimi", "vendor": "月之暗面",
     "adapter": "provider", "provider": "kimi", "model": None,
     "note": "api.moonshot.cn 直连"},
    {"key": "yuanbao", "label": "腾讯混元 (元宝)", "vendor": "腾讯",
     "adapter": "provider", "provider": "hunyuan", "model": None,
     "note": "hunyuan OpenAI 兼容直连"},
    {"key": "spark", "label": "讯飞星火", "vendor": "科大讯飞",
     "adapter": "provider", "provider": "spark", "model": None,
     "note": "spark-api-open 直连"},
    {"key": "doubao", "label": "豆包 (Doubao)", "vendor": "字节跳动",
     "adapter": "provider", "provider": "doubao", "model": None,
     "note": "火山方舟直连"},
    {"key": "claude", "label": "Claude", "vendor": "Anthropic",
     "adapter": "provider", "provider": "claude", "model": None,
     "note": "Anthropic Messages API 直连"},
    {"key": "gemini", "label": "Gemini", "vendor": "Google",
     "adapter": "provider", "provider": "gemini", "model": None,
     "note": "Gemini OpenAI 兼容端点直连"},
    # —— 检索探针（bl CLI + DASHSCOPE key）——
    {"key": "web_retrieval", "label": "联网检索可见度（DashScope WebSearch）",
     "vendor": "检索探针", "adapter": "bl_search", "model": "websearch",
     "note": "反映 RAG 类引擎可检索到的可见度；服务异常时标注‘待复测’"},
    # —— 仍待密钥的引擎（如实标注）——
    {"key": "gpt", "label": "ChatGPT (GPT)", "vendor": "OpenAI",
     "adapter": "provider", "provider": None, "model": "gpt-4o",
     "env_key": "OPENAI_API_KEY", "note": "待密钥复测"},
    {"key": "perplexity", "label": "Perplexity", "vendor": "Perplexity",
     "adapter": "provider", "provider": None, "model": "sonar",
     "env_key": "PERPLEXITY_API_KEY", "note": "待密钥复测"},
    {"key": "ernie", "label": "文心一言 (ERNIE)", "vendor": "百度",
     "adapter": "provider", "provider": None, "model": "ernie-4.5",
     "env_key": "QIANFAN_API_KEY", "note": "待密钥复测"},
]


def _engine_reachable(e):
    """可达性动态判定：provider 引擎看密钥；bl 引擎看 DASHSCOPE key（CLI 在 CI 已装）。"""
    if e["adapter"] in ("bl_chat", "bl_search"):
        return bool(os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("TONGYI_API_KEY"))
    if e.get("provider"):
        return LP.has_key(e["provider"])
    return False

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
# 现状由 2026-07-19 对铭信官网（mingxinstorage.xyz，Next.js + 引擎接口）的核查得出：
# 官网已具备 robots/llms.txt/llms-full.txt/sitemap/JSON-LD/双语镜像与内容引擎；
# 站外（百科/知乎/CSDN/GitHub 等）铭信品牌沉淀仍处于起步期。
LEVERS = {
    "L1": {
        "name": "实体接地（让模型认得清是谁）",
        "goal": "建立可被各引擎一致识别的铭信品牌实体，杜绝与同名主体混淆，并声明 FX/历史称谓命名沿革。",
        "checklist": [
            {"item": "Wikidata 实体 Q-ID 建立并填充关系（行业/产品/总部）", "done": False},
            {"item": "百度百科 / 维基百科 词条收录", "done": False},
            {"item": "官网 schema.org Organization + sameAs 数组（GitHub/企查查/媒体）", "done": True},
            {"item": "全网 NAP（名称/电话/联系人）一致性核对", "done": True},
            {"item": "固定 100 字中英规范简介作为‘事实基准’全网统一", "done": True},
            {"item": "FX100=AISSD5000/WS5000/GP5000 命名沿革声明全网一致", "done": True},
        ],
    },
    "L2": {
        "name": "技术可达性（让爬虫进得来、读得懂）",
        "goal": "让 AI 爬虫可抓取、可解析、可快速加载。",
        "checklist": [
            {"item": "robots.txt 放行 GPTBot/ClaudeBot/PerplexityBot/Google-Extended/Bytespider 等", "done": True},
            {"item": "根目录 llms.txt（精选页索引）", "done": True},
            {"item": "llms-full.txt（站点正文内联）", "done": True},
            {"item": "sitemap.xml 提交主流站长平台", "done": True},
            {"item": "服务端渲染（Next.js SSR/预渲染，首屏可直接解析）", "done": True},
            {"item": "IndexNow/百度主动推送常态化（/api/seo/ping）", "done": True},
        ],
    },
    "L3": {
        "name": "结构化内容（让回答抽得出、引得到）",
        "goal": "以答案胶囊 + 结构化标注 + 报告编号引用，提升被抽取与被引用概率。",
        "checklist": [
            {"item": "关键页 40–60 字‘答案胶囊’开篇 + 问题式标题", "done": True},
            {"item": "FAQPage JSON-LD（5–7 问）", "done": True},
            {"item": "Article + Product/TechArticle JSON-LD 叠加", "done": True},
            {"item": "‘什么是铭信 FX100 / What is Mingxin FX100’定义页", "done": False},
            {"item": "对比页（vs 本地盘/无外存重算/NFS，配 ItemList schema 与报告编号）", "done": True},
            {"item": "签字级实测证据库页（R1–R9 报告可下载、口径标注）", "done": True},
        ],
    },
    "L4": {
        "name": "站外权威（让模型信得过）",
        "goal": "在中立高权威域形成跨源一致的铭信品牌事实，强化实体可信度。",
        "checklist": [
            {"item": "行业媒体（存储在线/至顶网/电子发烧友）报道与收录", "done": False},
            {"item": "知乎/CSDN/掘金等技术内容沉淀", "done": False},
            {"item": "GitHub 知识库 / 技术文档公开", "done": False},
            {"item": "MLPerf Storage / IO500 式独立基准参与", "done": False},
            {"item": "签字级第三方实测报告（R1–R9）成为可引用资产", "done": True},
            {"item": "测试代码与原始数据可复现导出包（R8）合规呈现", "done": True},
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
        "站外实体脚手架上线：百科/知乎/CSDN/GitHub 知识库首批沉淀",
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
    "R": "铭信签字级实测报告 R1–R9（AMD MI308X ×8 / 华为 Atlas 910B / 沐曦 N260；证据库 mingxinstorage.xyz/evidence）。",
    "DS": "铭信产品事实：business_plan/outputs/results.json（与官网 company.ts 单一数据源同源）。",
    "SV": f"现状核查：{SURVEY_DATE} 对铭信官网（mingxinstorage.xyz）与公开搜索引擎的核查（站内 GEO 基础设施完备；站外品牌沉淀起步期）。",
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
    has_url = "://" in text_l
    cited = has_url and any(t in text_l for t in ["mingxinstorage", "mingxin"])

    return {
        "self_mention": self_mention,
        "rank": rank,
        "recommended": recommended,
        "cited": bool(cited),
        "competitor_hits": {k: True for k in comp_first},
        "n_competitors_mentioned": len(comp_first),
    }


def reachable_engines():
    return [e for e in ENGINES if _engine_reachable(e)]


def pending_engines():
    return [e for e in ENGINES if not _engine_reachable(e)]


if __name__ == "__main__":
    f = ground_truth_facts()
    print("Ground-truth facts:", f)
    print("Lever scores:", lever_scores())
    print(f"Queries: {len(QUERY_BASKET)} | Engines reachable now: {len(reachable_engines())} | pending: {len(pending_engines())}")
