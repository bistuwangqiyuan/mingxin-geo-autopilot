# -*- coding: utf-8 -*-
"""铭信 GEO Autopilot · 流量来源信号检测（traffic_check.py）——四步法·第 4 步。

经 GA4 Data API（runReport, 近 7 天 sessionSource/sessionMedium）检测 GEO 生效信号：
  - Referral 中出现 reddit.com
  - 来源中出现 perplexity / chatgpt / openai / copilot / gemini 等 AI 引擎

诚实纪律：
  - 需要 GA4_PROPERTY_ID + GA4_SA_JSON（服务账号 JSON，Secrets 注入）。缺失时如实落盘
    status=ga4_not_configured，绝不编造流量信号。
  - 信号未出现≠系统失效：GEO 是信号积累过程，按四步法继续迭代（日报如实说明）。
  - 纯 stdlib 实现（urllib + 手工 JWT/RS256 经 cryptography 不可用时回退 google-auth——
    这里选用最小依赖路径：优先 google-auth 库，缺库且有密钥时如实报 dependency_missing）。
"""
from __future__ import annotations

import datetime as dt
import json
import os

import paths

OUT = os.path.join(paths.OUTPUTS, "traffic_signals.json")

# AI 引擎来源特征（sessionSource 子串匹配，宽松小写）
AI_SOURCES = ("perplexity", "chatgpt", "openai", "copilot", "gemini", "bing.com/chat",
              "you.com", "phind", "kagi")
REDDIT = "reddit"


def _now():
    return dt.datetime.now().isoformat(timespec="seconds")


def _ga4_report(prop_id, sa_info):
    """调用 GA4 Data API runReport；返回 rows=[{source, medium, sessions}]。"""
    # 走 google-auth 拿 access token（requirements 已含 requests；google-auth 在 CI 安装）
    from google.oauth2 import service_account  # type: ignore
    from google.auth.transport.requests import Request  # type: ignore
    import requests

    creds = service_account.Credentials.from_service_account_info(
        sa_info, scopes=["https://www.googleapis.com/auth/analytics.readonly"])
    creds.refresh(Request())
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{prop_id}:runReport"
    body = {
        "dateRanges": [{"startDate": "7daysAgo", "endDate": "today"}],
        "dimensions": [{"name": "sessionSource"}, {"name": "sessionMedium"}],
        "metrics": [{"name": "sessions"}],
        "limit": 250,
    }
    r = requests.post(url, json=body, timeout=60,
                      headers={"Authorization": f"Bearer {creds.token}"})
    r.raise_for_status()
    rows = []
    for row in r.json().get("rows", []):
        dims = [d.get("value", "") for d in row.get("dimensionValues", [])]
        mets = row.get("metricValues", [{}])
        rows.append({"source": dims[0] if dims else "",
                     "medium": dims[1] if len(dims) > 1 else "",
                     "sessions": int(mets[0].get("value", 0)) if mets else 0})
    return rows


def check():
    """返回并落盘信号快照（缺配置/缺依赖/出错均如实标注，绝不编造）。"""
    paths.ensure_dirs()
    prop_id = os.environ.get("GA4_PROPERTY_ID", "").strip()
    sa_raw = os.environ.get("GA4_SA_JSON", "").strip()

    doc = {"ts": _now(), "status": None, "reddit_referral": None,
           "ai_engine_sources": None, "detail": []}

    if not prop_id or not sa_raw:
        doc["status"] = "ga4_not_configured"
        doc["note"] = ("未配置 GA4_PROPERTY_ID/GA4_SA_JSON（Secrets），本轮不检测流量信号；"
                       "提供密钥后自动激活，绝不编造数据。")
        _save(doc)
        return doc

    try:
        sa_info = json.loads(sa_raw)
    except Exception:
        doc["status"] = "ga4_sa_json_invalid"
        _save(doc)
        return doc

    try:
        rows = _ga4_report(prop_id, sa_info)
    except ImportError:
        doc["status"] = "dependency_missing(google-auth)"
        _save(doc)
        return doc
    except Exception as e:  # noqa: BLE001
        doc["status"] = f"ga4_api_error: {e}"
        _save(doc)
        return doc

    reddit_rows = [r for r in rows if REDDIT in r["source"].lower()]
    ai_rows = [r for r in rows
               if any(s in r["source"].lower() for s in AI_SOURCES)]
    doc["status"] = "ok"
    doc["reddit_referral"] = sum(r["sessions"] for r in reddit_rows) or 0
    doc["ai_engine_sources"] = {r["source"]: r["sessions"] for r in ai_rows}
    doc["geo_signal_present"] = bool(reddit_rows or ai_rows)
    doc["detail"] = (reddit_rows + ai_rows)[:20]
    doc["note"] = ("GEO 生效信号已出现" if doc["geo_signal_present"]
                   else "信号尚未出现：GEO 是信号积累过程，继续按四步法迭代（非失效）。")
    _save(doc)
    return doc


def _save(doc):
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def main():
    doc = check()
    print(f"[traffic_check] status={doc['status']} "
          f"reddit={doc.get('reddit_referral')} ai_sources={doc.get('ai_engine_sources')}")


if __name__ == "__main__":
    main()
