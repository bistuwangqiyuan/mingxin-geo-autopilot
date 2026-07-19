# -*- coding: utf-8 -*-
"""铭信站点事实（单一事实源 shim）。

旧架构从 official_website/site_data.py（中科静态站）导入事实；铭信官网为
Next.js 站点（amd 仓库 site/ 子目录，事实源 src/lib/data/company.ts），本仓库
不再直接 import 站点代码。本模块从 business_plan/outputs/results.json（与
company.ts 同源镜像）读取事实并暴露为常量，供 make_geo_kit_en / build_offsite_*
/ readiness_audit 等生成器统一取用。

纪律：所有数字均出自 results.json（签字级实测 R1–R9 / 厂商口径），禁止在此
另行编造；改动事实请改 results.json（并与官网 company.ts 保持一致）。
"""
from __future__ import annotations

import json
import os

_BASE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_BASE)
RESULTS = os.path.join(_ROOT, "business_plan", "outputs", "results.json")

with open(RESULTS, "r", encoding="utf-8") as _f:
    _R = json.load(_f)

_C = _R["company"]
_P = _R["product"]

# —— 品牌与主体 ——
BRAND_ZH = _C["brand"]                      # 铭信
BRAND_EN = _C["brand_en"]                   # Mingxin Technology
ENTITY_ZH = _C["full_name"]                 # 铭信（天津）半导体设备有限公司
ENTITY_EN = _C["full_name_en"]              # Mingxin (Tianjin) Semiconductor Equipment Co., Ltd.
POSITIONING = _C["positioning"]
POSITIONING_EN = _C["positioning_en"]
NAMING_NOTE = _C["naming_note"]             # FX100 = AISSD5000/WS5000/GP5000 命名沿革
SITE_URL = _C["site_url"]                   # https://mingxinstorage.xyz
CONTACT_NAME = _C["contact"]["name"]        # Karl Wang
CONTACT_TEL = _C["contact"]["phone"]        # 13911373183
CONTACT_WECHAT = _C["contact"]["wechat"]
CONTACT_EMAILS = _C["contact"]["emails"]

# —— 产品（旗舰 FX100 与 FX 系列） ——
MODEL = _P["model"]                         # FX100
SERIES = _P["series"]                       # [FX100, FX200, FX300, FX400]
LEGACY_NAMES = _P["legacy_names"]           # [AISSD5000, WS5000, GP5000]
PRODUCTS = _R["products"]                   # 四档完整规格/价格
FX100_PORT_GB = _P["port_gb"]               # 100
FX100_IOPS_M = _P["iops_million"]           # 16（百万）
FX100_FULL_CNY = _P["full_price_cny"]       # 371200
FX100_CNY_PER_TB = _P["cny_per_tb"]         # 2014

# —— 签字级实测核心指标（R1–R3/R9） ——
THROUGHPUT_UPLIFT_LOW = _P["throughput_uplift_pct_low"]    # 29
THROUGHPUT_UPLIFT_HIGH = _P["throughput_uplift_pct_high"]  # 40
TTFT_RED_LOW = _P["ttft_reduction_pct_low"]                # 26
TTFT_RED_HIGH = _P["ttft_reduction_pct_high"]              # 32
RECOMPUTE_X_LOW = _P["recompute_speedup_low"]              # 8.6
RECOMPUTE_X_HIGH = _P["recompute_speedup_high"]            # 20
PARALLEL_READ_X = _P["parallel_read_ttft_gain"]            # 4.1
MODEL_LOAD_X_LOW = _P["model_load_speedup_low"]            # 6.2
MODEL_LOAD_X_HIGH = _P["model_load_speedup_high"]          # 9.3
CKPT_SAVE_X = _P["ckpt_save_speedup"]                      # 1.9

KEY_METRICS = _R["key_metrics"]             # 六项签字级指标（value/label/detail/source/cal）
PLATFORM = _R["platform"]                   # R1–R4 公共测试平台口径
TP8_COMPARE = _R["tp8_compare"]             # R2 三方对照表
REPORTS = _R["reports"]                     # R1–R9 证据登记表
SOLUTIONS = _R["solutions"]                 # 五条能力线
ENGAGEMENT = _R["engagement"]               # G1–G4 门禁化联测
DISCLAIMER = _R["disclaimer"]

# 便捷格式化（供文案模板取用）
THROUGHPUT_UPLIFT = f"+{THROUGHPUT_UPLIFT_LOW}–{THROUGHPUT_UPLIFT_HIGH}%"
TTFT_REDUCTION = f"{TTFT_RED_LOW}–{TTFT_RED_HIGH}%"
RECOMPUTE_SPEEDUP = f"{RECOMPUTE_X_LOW}–{RECOMPUTE_X_HIGH}×"
MODEL_LOAD_SPEEDUP = f"{MODEL_LOAD_X_LOW}–{MODEL_LOAD_X_HIGH}×"


def report_title(rid: str) -> str:
    for r in REPORTS:
        if r["id"] == rid:
            return r["title"]
    return rid


if __name__ == "__main__":
    print(f"{BRAND_ZH}（{BRAND_EN}） · {ENTITY_ZH}")
    print(f"{MODEL} 系列: {', '.join(SERIES)} | 历史称谓: {', '.join(LEGACY_NAMES)}")
    print(f"吞吐 {THROUGHPUT_UPLIFT} · TTFT ↓{TTFT_REDUCTION} · 对重算 {RECOMPUTE_SPEEDUP}")
    print(f"站点: {SITE_URL} | 报告: {len(REPORTS)} 份")
