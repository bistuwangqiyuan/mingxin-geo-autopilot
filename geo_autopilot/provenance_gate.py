# -*- coding: utf-8 -*-
"""来源闸门（provenance gate）：答案里的具体数字、标准名、缩写、URL，必须能在公司事实源中找到，否则不上线。

背景：自动生成的 FAQ 曾出现 "sub-12μs commit latency"、"EU AI Act Article 16"、
"TPM 2.0 + RCIB"、"/metrics API" 等事实源里不存在的具体参数（公开仓库 outputs 中共 7 条）。
原有的 check_consistency 只拦截已知的旧口径，拦不住"来源不明"的新数字，所以这里加一道来源检查。

规则（保守：宁可拒绝，也不让无依据的参数上线）：
1. 带单位的数字（含区间，如 29–40%）必须在事实源中出现。
2. 标准、法规、未经核实的技术名（EU AI Act、GDPR、Article N、linearizable 等）必须在事实源中出现。
3. 全大写缩写（如 TPM、RCIB、WAL）必须在事实源中出现；通用行业术语白名单除外。
4. URL 的域名必须是当前官网；路径必须是站内真实路由，或在事实源中出现（旧域名一律拒绝）。

事实源：business_plan/outputs/results.json（与官网 company.ts 同源）+ 当前官网地址。
要让新的具体说法通过，必须先把它写进事实源——闸门不替代核实。
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

# 数字 + 单位（可选区间）。前面不能紧跟字母或数字，避免把 MI308X、FX100 里的数字拆开。
_NUM_UNIT_RE = re.compile(
    r"(?<![A-Za-z0-9])\+?\d+(?:[.,]\d+)?"
    r"(?:\s*[–—\-~～]\s*\d+(?:[.,]\d+)?)?"
    r"\s*(?:%|×|x|μs|us|ms|秒|s(?![A-Za-z])|GB|TB|GiB|Gb|Tb|MB|IOPS|tok/s|GHz|万|亿|¥|\$|元|卡|节点|台|次)"
)
_URL_RE = re.compile(r"https?://[^\s)）\]>，。、；;,]+")
# 裸域名（不带协议，如 mingxinstorage.xyz/metrics）。前面不能是 @ 或字母数字（排除邮箱本地部分）。
_BARE_DOMAIN_RE = re.compile(
    r"(?<![@\w.\-/])((?:[a-z0-9\-]+\.)+(?:xyz|top|pw|icu|asia|site|tech|cn|com|net|org|io|ai|to|uno|cc|app|dev))"
    r"(/[^\s)）\]，。、；;,]*)?",
    re.IGNORECASE,
)
# 全大写缩写：2–6 个字母或数字，首字母大写。
_ACRO_RE = re.compile(r"(?<![A-Za-z0-9])[A-Z][A-Z0-9]{1,5}(?![A-Za-z0-9])")

# 通用词与通用行业术语：本身不是具体参数，不要求出现在事实源中（具体数值仍由数字规则把关）。
_COMMON_ACRO = {
    "AI", "API", "FAQ", "GPU", "CPU", "KV", "SSD", "HBM", "LLM", "TTFT",
    "TCO", "PUE", "URL", "USD", "CNY", "GB", "TB", "MB", "IOPS", "OK", "IT",
    "SATA", "SAS", "RDMA", "NFS", "EU", "US", "UK", "CN", "RAM", "VRAM", "DPU", "NPU",
    "CUDA", "SLA", "SLO", "QPS", "TPS", "ROI", "OEM", "ODM", "SDK", "FP8", "FP16",
    "BF16", "INT8", "HTTP", "HTTPS", "JSON", "PDF", "SQL", "RTO", "RPO", "SKU", "MOQ",
    "PB", "TPU", "NIC", "IPMI", "CAGR", "NDA", "DNS", "TGI", "NVIDIA", "AMD",
}
# 标准、法规、未经核实的技术名：事实源里没有就拒绝。
_UNVERIFIED_TERMS = (
    "EU AI Act", "GDPR", "ISO 27001", "SOC 2", "FIPS", "HIPAA",
    "Article 16", "linearizable", "quorum",
)
# 站内真实路由（与官网 build 产物一致）。路径命中这些前缀即视为有来源。
_SITE_ROUTES = (
    "/", "/en", "/products", "/evidence", "/faq", "/tech", "/cases", "/roi", "/solutions",
    "/insights", "/topics", "/gpu-spot", "/contact", "/pricing", "/terms", "/privacy",
    "/token-channels", "/answers", "/compare", "/scenarios", "/accel", "/cooperation",
    "/partners", "/videos", "/month-bill", "/test-drive", "/rss.xml", "/sitemap.xml",
    "/llms.txt", "/llms-full.txt", "/robots.txt",
)


def _norm(s: str) -> str:
    """统一比对口径：小写、各类破折号归为 “–”、乘号 × 归为 x、去掉全部空白。"""
    s = (s or "").lower().replace("×", "x")
    s = re.sub(r"[—\-~～]", "–", s)
    return re.sub(r"\s+", "", s)


def _route_ok(path: str) -> bool:
    p = path.rstrip("/") or "/"
    if p in _SITE_ROUTES:
        return True
    return any(p.startswith(r.rstrip("/") + "/") for r in _SITE_ROUTES if r != "/")


def build_corpus(results_path: str, site_url: str) -> str:
    """读取事实源（results.json 原文）并加入当前官网地址，返回归一化后的比对语料。"""
    with open(results_path, "r", encoding="utf-8") as f:
        raw = f.read()
    return _norm(raw + "\n" + (site_url or ""))


def provenance_issues(text: str, corpus: str, site_url: str) -> list[str]:
    """返回来源问题列表；空列表表示通过。"""
    issues: list[str] = []
    t = text or ""
    site_host = (urlparse(site_url or "").netloc or "").lower()

    # 4) URL：域名必须是当前官网；路径必须是站内路由或在事实源中出现。
    for raw_url in _URL_RE.findall(t):
        url = raw_url.rstrip(".")  # 句末句号不是域名的一部分
        p = urlparse(url)
        host = (p.netloc or "").lower()
        if host != site_host:
            issues.append(f"URL 指向非当前官网域名：{host}")
        elif p.path and p.path != "/" and not _route_ok(p.path) and _norm(p.path) not in corpus:
            issues.append(f"URL 路径无来源：{p.path}")

    body = _URL_RE.sub(" ", t)

    # 4b) 裸域名：域名必须是当前官网；带路径时路径同样需要有来源。
    for m in _BARE_DOMAIN_RE.finditer(body):
        host = m.group(1).lower()
        path = m.group(2) or ""
        if host not in (site_host, "www." + site_host):
            issues.append(f"URL 指向非当前官网域名：{host}")
        elif path and path != "/" and not _route_ok(path) and _norm(path) not in corpus:
            issues.append(f"URL 路径无来源：{path}")
    body = _BARE_DOMAIN_RE.sub(" ", body)

    # 1) 带单位的数字
    for m in _NUM_UNIT_RE.finditer(body):
        token = m.group(0).strip()
        if _norm(token) not in corpus:
            issues.append(f"数字无来源：{token}")

    # 2) 标准、法规、未核实技术名
    low = body.lower()
    for term in _UNVERIFIED_TERMS:
        if term.lower() in low and _norm(term) not in corpus:
            issues.append(f"未核实的标准或技术名：{term}")

    # 3) 全大写缩写
    seen = set()
    for m in _ACRO_RE.finditer(body):
        w = m.group(0)
        if w in seen or w in _COMMON_ACRO:
            continue
        seen.add(w)
        if _norm(w) not in corpus:
            issues.append(f"缩写无来源：{w}")

    return issues
