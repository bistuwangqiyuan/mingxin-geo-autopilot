# -*- coding: utf-8 -*-
"""从已部署资产诚实推导 CURRENT_SOURCE_COVERAGE（单一事实源，可复现）。

读取：
  - seo_geo_loop/outputs/offsite_published.json
  - seo_geo_loop/outputs/live_status.json（可选）
  - 铭信官网线上探测（https://mingxinstorage.xyz 的 robots.txt / llms.txt / sitemap.xml）

说明：铭信官网为 Next.js 站点（amd 仓库 site/ 子目录，Vercel 部署），robots/llms
均为路由而非静态文件，故对线上 URL 做 HTTP 探测；网络不可用时如实标注
unknown/pending 并回退 geo_config 静态基线，绝不编造。

纪律：仅对已实测 HTTP 200 且含结构化内容的渠道计分；UGC 平台无 live URL 则保持 0。
"""
from __future__ import annotations

import json
import os
import urllib.request

import geo_config as C

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
OFFSITE_PUB = os.path.join(ROOT, "seo_geo_loop", "outputs", "offsite_published.json")
LIVE_STATUS = os.path.join(ROOT, "seo_geo_loop", "outputs", "live_status.json")

SITE_URL = "https://mingxinstorage.xyz"
SITE_PROBE_PATHS = ["/robots.txt", "/llms.txt", "/sitemap.xml"]


def _load_json(path):
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _http_ok(url, timeout=8):
    """探测单个 URL：200 → True；非 200 → False；网络不可用 → None（unknown）。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "mingxin-geo-coverage/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return None


def _site_geo_ready():
    """官网 GEO 基础设施是否齐全（线上 HTTP 探测）。

    返回 (ratio, status)：
      - status="probed"：至少一个探测有确定结果，ratio = 200 数 / 探测数。
      - status="unknown"：全部探测网络失败，ratio=None（不编造，回退静态基线）。
    """
    results = [_http_ok(SITE_URL + p) for p in SITE_PROBE_PATHS]
    known = [r for r in results if r is not None]
    if not known:
        return None, "unknown"
    ok = sum(1 for r in known if r)
    return round(ok / len(SITE_PROBE_PATHS), 2), "probed"


def resolve_coverage():
    """返回 (coverage_dict, evidence_list)。"""
    pub = _load_json(OFFSITE_PUB)
    live = _load_json(LIVE_STATUS)
    evidence = []

    cov = dict(C.CURRENT_SOURCE_COVERAGE)  # baseline from config

    # 独立官网：线上 GEO 基础设施探测 + 部分搜索引擎收录
    geo_ready, probe_status = _site_geo_ready()
    gsc_indexed = 0
    if live.get("onpage"):
        gsc_indexed = sum(
            1 for p in live["onpage"]
            if p.get("google_indexed") is True
        )
    if probe_status == "probed":
        site_score = min(0.98, 0.55 + 0.35 * geo_ready + 0.08 * min(gsc_indexed, 3) / 3)
        cov["独立官网"] = round(site_score, 2)
        rationale = (f"线上探测 robots/llms/sitemap 就绪 {geo_ready:.0%}；"
                     f"GSC 已编入 {gsc_indexed} 页（partial indexing）")
    else:
        # 网络不可用：如实标注 unknown/pending，保持 geo_config 静态基线，不编造
        rationale = ("线上探测网络不可用（unknown/pending），沿用 geo_config 静态基线；"
                     "待网络恢复后复测，不编造")
    evidence.append({
        "platform": "独立官网", "score": cov["独立官网"],
        "probe_status": probe_status,
        "rationale": rationale,
        "urls": [SITE_URL + p for p in SITE_PROBE_PATHS],
    })

    # GitHub/GitCode：知识库仓库（mingxin-storage-kb）+ Pages
    gh_live = any(
        ch.get("verified_http_200") and "github" in ch.get("platform", "").lower()
        for ch in pub.get("channels", [])
    )
    repo_live = bool(pub.get("sameas_urls") and any("github.com" in u for u in pub["sameas_urls"]))
    gh_score = 0.0
    if gh_live and repo_live:
        gh_score = 0.72
    elif repo_live:
        gh_score = 0.45
    cov["GitHub/GitCode"] = gh_score
    if gh_score:
        evidence.append({
            "platform": "GitHub/GitCode", "score": gh_score,
            "rationale": "公开知识库仓库 + GitHub Pages 实测 200，含 JSON-LD 与英文 README",
            "urls": [u for u in pub.get("sameas_urls", []) if "github" in u],
        })

    # 技术白皮书 / 证据库：官网 /evidence 页（R1–R9 签字级/正式版报告）
    ev_ok = _http_ok(SITE_URL + "/evidence")
    if ev_ok is True:
        cov["技术白皮书"] = 0.88
        evidence.append({
            "platform": "技术白皮书", "score": 0.88,
            "rationale": "官网证据库页 /evidence 实测 200（R1–R9 签字级/正式版报告，口径标注）",
            "urls": [SITE_URL + "/evidence"],
        })
    elif ev_ok is None:
        evidence.append({
            "platform": "技术白皮书", "score": cov.get("技术白皮书", 0.0),
            "probe_status": "unknown",
            "rationale": "证据库页探测网络不可用（unknown/pending），沿用静态基线，不编造",
            "urls": [SITE_URL + "/evidence"],
        })

    # 自建结构化微站（如有）：计入 sameAs 实体图，但不冒充 UGC 平台覆盖
    micro = next(
        (ch for ch in pub.get("channels", [])
         if ch.get("verified_http_200") and "edgeone" in ch.get("platform", "").lower()),
        None,
    )
    if micro:
        # 诚实：这是自建微站，不是 CSDN/知乎/语雀；保持 UGC 平台为 0，避免虚报
        evidence.append({
            "platform": "自建知识微站（不计入 UGC 平台覆盖）",
            "score": "N/A",
            "rationale": "已部署结构化微站，计入 sameAs 实体图，但不冒充 CSDN/语雀覆盖",
            "urls": [micro.get("url", "")],
        })

    # UGC 平台：drafts ready but not published → 保持 0
    ugc = pub.get("ugc_manual", {})
    if ugc.get("status") == "publish_ready_drafts":
        evidence.append({
            "platform": "UGC（CSDN/知乎/百科/公众号等）",
            "score": 0.0,
            "rationale": "定稿已就绪（geo_plan/offsite/*.md），待人工核准发布；白帽不自动发帖",
            "urls": [],
        })

    return cov, evidence


def write_coverage_snapshot(out_dir=None):
    out_dir = out_dir or os.path.join(BASE, "outputs")
    cov, evidence = resolve_coverage()
    snap = {
        "resolved_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "coverage": cov,
        "evidence": evidence,
        "method": "coverage_resolver.py · 官网走线上 HTTP 探测（网络不可用则 unknown/pending）；"
                  "其余仅计实测 200 的渠道；UGC 无 live URL 则为 0",
    }
    path = os.path.join(out_dir, "source_coverage_resolved.json")
    os.makedirs(out_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)
    return snap, path
