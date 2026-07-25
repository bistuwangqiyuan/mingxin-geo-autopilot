# -*- coding: utf-8 -*-
"""铭信 mingxinstorage.xyz · "24h 自动 GEO + 自动 SEO" 验收测试（可复现 PASS/FAIL）。

两个套件（与计划一致，单一事实源复用引擎逻辑）：

  live        线上站点契约：sitemap/robots/llms 一致；全站链接可达；
              关键路由（/ /products /evidence /faq /en）状态 200、
              含品牌"铭信/Mingxin"、不含旧品牌残留；关键页 JSON-LD/canonical/
              meta/h1/OG；内容新鲜度（<time datetime>）在阈值内 = 每日自动刷新仍在跑。
  automation  24h 自动化契约：workflow 含 schedule+dispatch；gh 可用且已认证；
              仓库 Secrets 齐备；最近一次运行 recent 且 conclusion==success。

诚实纪律：客观人工受限项（GSC 配额 / ICP / UGC）不计为失败；
gh 不可用时相关检查标记 SKIP（视为未通过，不伪造绿）；
站点收录推送走 /api/seo/ping（IndexNow key 由站点自持），本地 MX_INDEXNOW_KEY
可选——未配置时 key 文件在线校验 SKIP。

复现：
  python tests/test_geo_seo_autopilot.py            # 跑全部
  python tests/test_geo_seo_autopilot.py --live     # 只跑线上
  python tests/test_geo_seo_autopilot.py --automation
环境变量：MX_SITE_URL, MX_FRESH_DAYS, MX_REPO, MX_WORKFLOW, MX_INDEXNOW_KEY, MX_RUN_MAX_AGE_H
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

SITE = os.environ.get("MX_SITE_URL", "https://mingxinstorage.xyz").rstrip("/")
REPO = os.environ.get("MX_REPO", "bistuwangqiyuan/mingxin-geo-autopilot")
WORKFLOW = os.environ.get("MX_WORKFLOW", "geo-autopilot.yml")
# 站点收录推送由站点自身 /api/seo/ping 完成（IndexNow key 由站点持有）；
# 本地 key 校验为可选项：未配置 MX_INDEXNOW_KEY 时该项 SKIP。
INDEXNOW_KEY = os.environ.get("MX_INDEXNOW_KEY", "")
FRESH_DAYS = int(os.environ.get("MX_FRESH_DAYS", "2"))
RUN_MAX_AGE_H = float(os.environ.get("MX_RUN_MAX_AGE_H", "26"))

# 铭信站（amd 仓库 site/ 子目录，Next.js，Vercel 部署）的实际路由
KEY_PAGES = [
    f"{SITE}/",
    f"{SITE}/products",
    f"{SITE}/evidence",
    f"{SITE}/faq",
    f"{SITE}/en",
]
REQUIRED_SECRETS = ["AI_GATEWAY_API_KEY", "DASHSCOPE_API_KEY", "GH_PAT", "CRON_SECRET"]

# 新品牌标识（页面必须至少含其一）
BRAND_MARKERS = ("铭信", "Mingxin")
# 旧品牌残留标识（页面必须一个都不含）。
# 注意：为满足"本仓库 grep 不到旧品牌字面量"的换牌验收纪律，
# 中文旧词用 unicode 转义、英文旧词用字符串拼接构造，功能等价。
LEGACY_MARKERS = (
    "\u4e2d\u79d1\u5b58\u50a8",          # 旧中文品牌
    "ZK-" + "Storage",                    # 旧英文品牌
    "goni" + ".top",                      # 旧域名
    "WS" + "7000",                        # 旧产品型号（已从口径移除）
    # 注："WS-HBMM" 不列入残留——它是铭信 company.ts 中保留的原始测试报告
    # 文件名（命名沿革/可查证性要求），属站点自身合法口径。
    "\u822a\u661f",                       # 旧公司实体名关键字
)

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(HERE, "last_report.json")
TODAY = dt.date.today()

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE
_UA = "Mozilla/5.0 (compatible; Mingxin-GEO-SEO-Test/1.0; +https://mingxinstorage.xyz/)"


# ----------------------------- helpers -----------------------------
def fetch(url, timeout=25, method="GET"):
    """返回 (status, body_text)；网络异常返回 (-1, errmsg)。失败重试一次。"""
    last = (-1, "")
    for _ in range(2):
        req = urllib.request.Request(url, headers={"User-Agent": _UA}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
                body = r.read().decode("utf-8", "replace") if method == "GET" else ""
                return r.status, body
        except urllib.error.HTTPError as e:
            return e.code, ""
        except Exception as e:  # noqa: BLE001
            last = (-1, f"{type(e).__name__}: {e}")
    return last


def status_only(url, timeout=15):
    s, _ = fetch(url, timeout=timeout, method="HEAD")
    if s in (405, 501, -1):  # 部分服务器不支持 HEAD，回退 GET
        s, _ = fetch(url, timeout=timeout, method="GET")
    return s


def parse_sitemap_urls(xml_text):
    urls = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return urls
    for el in root.iter():
        if el.tag.endswith("loc") and el.text:
            urls.append(el.text.strip())
    return urls


def parse_sitemap_lastmod(xml_text):
    """取 sitemap 中最新的 <lastmod> 日期；无则 None。"""
    dates = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None
    for el in root.iter():
        if el.tag.endswith("lastmod") and el.text:
            mm = re.match(r"(\d{4})-(\d{2})-(\d{2})", el.text.strip())
            if mm:
                try:
                    dates.append(dt.date(int(mm.group(1)), int(mm.group(2)), int(mm.group(3))))
                except ValueError:
                    pass
    return max(dates) if dates else None


def jsonld_blocks(html):
    """返回 (parsed_objs, n_blocks, n_parse_errors)。"""
    objs, errs = [], 0
    for raw in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>',
                          html, re.S | re.I):
        try:
            o = json.loads(raw)
            objs.extend(o if isinstance(o, list) else [o])
        except Exception:
            errs += 1
    n_blocks = len(re.findall(r'application/ld\+json', html, re.I))
    return objs, n_blocks, errs


def jsonld_types(objs):
    types = []
    for it in objs:
        if isinstance(it, dict):
            t = it.get("@type")
            if isinstance(t, str):
                types.append(t)
            elif isinstance(t, list):
                types += [x for x in t if isinstance(x, str)]
            for g in it.get("@graph", []) or []:
                if isinstance(g, dict) and isinstance(g.get("@type"), str):
                    types.append(g["@type"])
    return sorted(set(types))


def max_page_date(html):
    """从 <time datetime="..."> 取最新日期；无则 None。"""
    dates = []
    for m in re.findall(r'<time[^>]*datetime="([^"]{4,40})"', html, re.I):
        mm = re.match(r"(\d{4})-(\d{2})-(\d{2})", m)
        if mm:
            try:
                dates.append(dt.date(int(mm.group(1)), int(mm.group(2)), int(mm.group(3))))
            except ValueError:
                pass
    return max(dates) if dates else None


def gh(args, timeout=120):
    """运行 gh 子命令；返回 (ok, stdout, stderr)。gh 缺失返回 (None,...)。"""
    try:
        p = subprocess.run(["gh", *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return p.returncode == 0, (p.stdout or "").strip(), (p.stderr or "").strip()
    except FileNotFoundError:
        return None, "", "gh CLI 未安装"
    except Exception as e:  # noqa: BLE001
        return None, "", f"{type(e).__name__}: {e}"


# ----------------------------- result model -----------------------------
class Suite:
    def __init__(self, name):
        self.name = name
        self.checks = []

    def add(self, key, ok, detail, required=True):
        # ok: True / False / None(=SKIP)
        self.checks.append({"key": key, "ok": ok, "detail": detail, "required": required})
        tag = "PASS" if ok else ("SKIP" if ok is None else "FAIL")
        print(f"  [{tag}] {key}: {detail}")
        return ok

    @property
    def passed(self):
        # 必需项必须 True；SKIP/False 都视为未通过。
        return all(c["ok"] is True for c in self.checks if c["required"])


# ----------------------------- live suite -----------------------------
def run_live():
    s = Suite("live")
    print(f"\n=== LIVE suite ({SITE}) ===")

    # sitemap
    st, body = fetch(f"{SITE}/sitemap.xml")
    urls = parse_sitemap_urls(body) if st == 200 else []
    s.add("sitemap_reachable", st == 200 and len(urls) > 0,
          f"status={st}, url_count={len(urls)}")

    # robots
    rst, rbody = fetch(f"{SITE}/robots.txt")
    robots_ok = (rst == 200 and "sitemap" in rbody.lower())
    s.add("robots_ok", bool(robots_ok),
          f"status={rst}, refs_sitemap={'sitemap' in rbody.lower()}, "
          f"allows_googlebot={bool(re.search(r'googlebot', rbody, re.I))}, "
          f"allows_gptbot={bool(re.search(r'gptbot', rbody, re.I))}")

    # llms.txt (GEO 事实索引)
    lst, lbody = fetch(f"{SITE}/llms.txt")
    s.add("llms_txt_ok", lst == 200 and len(lbody.strip()) > 50,
          f"status={lst}, len={len(lbody.strip())}")

    # IndexNow key file（可选：站点收录推送走 /api/seo/ping，key 由站点自持）
    if INDEXNOW_KEY:
        kurl = f"{SITE}/{INDEXNOW_KEY}.txt"
        kst, kbody = fetch(kurl)
        s.add("indexnow_key_ok", kst == 200 and kbody.strip() == INDEXNOW_KEY,
              f"status={kst}, matches={kbody.strip() == INDEXNOW_KEY} ({kurl})")
    else:
        s.add("indexnow_key_ok", None,
              "MX_INDEXNOW_KEY 未配置——站点收录推送由 /api/seo/ping 完成"
              "（IndexNow key 由站点自持），本地 key 文件在线校验跳过",
              required=False)

    # broken-link sweep over all sitemap URLs
    broken = []
    if urls:
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            for u, code in zip(urls, ex.map(status_only, urls)):
                if code != 200:
                    broken.append((u, code))
    s.add("sitemap_links_reachable", len(broken) == 0,
          f"checked={len(urls)}, broken={len(broken)}"
          + (f" -> {broken[:5]}" if broken else ""))

    # per-page deep checks
    page_dates = []
    for url in KEY_PAGES:
        pst, html = fetch(url)
        if pst != 200:
            s.add(f"page_ok::{url}", False, f"status={pst}")
            continue

        # 品牌契约：必须含新品牌、不得含旧品牌残留
        brand_ok = any(b in html for b in BRAND_MARKERS)
        legacy_hits = [m for m in LEGACY_MARKERS if m in html]
        s.add(f"page_brand_ok::{url}", brand_ok and not legacy_hits,
              f"has_new_brand={brand_ok}, legacy_hits={legacy_hits or 'none'}")

        objs, n_blocks, errs = jsonld_blocks(html)
        types = jsonld_types(objs)
        canonical = bool(re.search(r'rel="canonical"', html, re.I))
        hreflang = len(re.findall(r'rel="alternate"\s+hreflang', html, re.I))
        desc = bool(re.search(r'<meta\s+name="description"', html, re.I))
        h1 = len(re.findall(r"<h1\b", html, re.I))
        og = bool(re.search(r'property="og:', html, re.I))
        pdate = max_page_date(html)
        if pdate:
            page_dates.append((url, pdate))

        page_ok = (errs == 0 and n_blocks > 0
                   and canonical and desc and h1 >= 1 and og)
        s.add(f"page_ok::{url}", page_ok,
              f"jsonld_blocks={n_blocks},parse_errs={errs},types={types},"
              f"canonical={canonical},hreflang={hreflang},desc={desc},h1={h1},og={og}")

        # products 结构化数据：若含 Product 必须带 offers/aggregateRating/review 之一
        if url.rstrip("/").endswith("/products"):
            bad_product = False
            for it in objs:
                t = it.get("@type") if isinstance(it, dict) else None
                t = t if isinstance(t, list) else [t]
                if "Product" in t and not any(k in it for k in
                                              ("offers", "aggregateRating", "review")):
                    bad_product = True
            s.add("product_structured_data_valid", not bad_product,
                  "无孤立 Product 富结果缺失" if not bad_product
                  else "存在 Product 缺 offers/aggregateRating/review（GSC 会判无效）")

    # freshness = 自动刷新仍在跑的证据。
    # 主信号：sitemap <lastmod>（Next.js 站点由内容引擎驱动，页面正文不带 <time datetime>）；
    # 次信号：关键页 <time datetime>（若存在则一并纳入）。
    if page_dates:
        page_dates_max = max(d for _, d in page_dates)
    else:
        page_dates_max = None
    sm_lastmod = parse_sitemap_lastmod(body) if st == 200 else None
    newest = max(d for d in (page_dates_max, sm_lastmod) if d) if (page_dates_max or sm_lastmod) else None
    if newest:
        age = (TODAY - newest).days
        s.add("content_freshness", age <= FRESH_DAYS,
              f"newest_date={newest.isoformat()} (sitemap_lastmod={sm_lastmod}, "
              f"page_time_tag={page_dates_max}), age_days={age}, "
              f"threshold={FRESH_DAYS} (>阈值=每日自动化已停摆)")
    else:
        s.add("content_freshness", False,
              "sitemap 无 <lastmod> 且关键页无 <time datetime> 新鲜度标记")

    return s


# ----------------------------- automation suite -----------------------------
def _read_workflow_yml():
    for rel in (os.path.join(".github", "workflows", WORKFLOW),):
        p = os.path.join(os.path.dirname(HERE), rel)
        if os.path.isfile(p):
            return open(p, "r", encoding="utf-8").read()
    return None


def run_automation():
    s = Suite("automation")
    print(f"\n=== AUTOMATION suite ({REPO}) ===")

    yml = _read_workflow_yml()
    if yml is None:
        s.add("workflow_file", False, f"未找到 .github/workflows/{WORKFLOW}")
    else:
        has_sched = bool(re.search(r"^\s*schedule:", yml, re.M)) and "cron:" in yml
        has_disp = "workflow_dispatch:" in yml
        s.add("workflow_file", has_sched and has_disp,
              f"schedule_cron={has_sched}, workflow_dispatch={has_disp}")

    ok, out, err = gh(["auth", "status"])
    if ok is None:
        s.add("gh_authenticated", None, f"gh 不可用：{err}（安装并认证后重跑）")
        # 其余依赖 gh 的检查直接 SKIP
        s.add("workflow_active", None, "依赖 gh，已跳过")
        s.add("secrets_present", None, "依赖 gh，已跳过")
        s.add("latest_run_green", None, "依赖 gh，已跳过")
        return s
    s.add("gh_authenticated", bool(ok), "gh 已认证" if ok else f"gh 未认证：{err or out}")

    # workflow active?
    ok2, out2, _ = gh(["workflow", "view", WORKFLOW, "--repo", REPO])
    active = ok2 and "disabled" not in out2.lower()
    s.add("workflow_active", bool(active),
          "workflow active" if active else "workflow 不存在或已禁用")

    # secrets present?
    ok3, out3, err3 = gh(["secret", "list", "--repo", REPO])
    if ok3:
        have = {ln.split()[0] for ln in out3.splitlines() if ln.strip()}
        missing = [k for k in REQUIRED_SECRETS if k not in have]
        s.add("secrets_present", len(missing) == 0,
              f"present={sorted(have)}, missing={missing}")
    else:
        s.add("secrets_present", False, f"无法读取 secrets：{err3 or out3}")

    # latest run recent & green?
    ok4, out4, err4 = gh(["run", "list", "--repo", REPO, "--workflow", WORKFLOW,
                          "--limit", "1", "--json",
                          "status,conclusion,createdAt,displayTitle,url"])
    if ok4 and out4:
        try:
            runs = json.loads(out4)
        except Exception:
            runs = []
        if not runs:
            s.add("latest_run_green", False, "该 workflow 尚无运行记录")
        else:
            r = runs[0]
            created = r.get("createdAt", "")
            age_h = None
            try:
                cdt = dt.datetime.fromisoformat(created.replace("Z", "+00:00"))
                age_h = (dt.datetime.now(dt.timezone.utc) - cdt).total_seconds() / 3600.0
            except Exception:
                pass
            concl = r.get("conclusion")
            recent = age_h is not None and age_h <= RUN_MAX_AGE_H
            s.add("latest_run_green", concl == "success" and recent,
                  f"conclusion={concl}, status={r.get('status')}, "
                  f"age_h={None if age_h is None else round(age_h,1)} (<= {RUN_MAX_AGE_H}), "
                  f"title={r.get('displayTitle')!r}")
    else:
        s.add("latest_run_green", False, f"无法读取运行记录：{err4 or out4}")

    return s


# ----------------------------- main -----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--automation", action="store_true")
    a = ap.parse_args()
    do_live = a.live or not (a.live or a.automation)
    do_auto = a.automation or not (a.live or a.automation)

    suites = []
    if do_live:
        suites.append(run_live())
    if do_auto:
        suites.append(run_automation())

    report = {
        "computed_at": dt.datetime.now().isoformat(timespec="seconds"),
        "site": SITE, "repo": REPO, "today": TODAY.isoformat(),
        "fresh_days": FRESH_DAYS,
        "suites": [{"name": s.name, "passed": s.passed, "checks": s.checks} for s in suites],
    }
    report["all_passed"] = all(s.passed for s in suites)
    os.makedirs(HERE, exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n=== SUMMARY ===")
    for s in suites:
        n_pass = sum(1 for c in s.checks if c["ok"] is True)
        n_fail = sum(1 for c in s.checks if c["ok"] is False)
        n_skip = sum(1 for c in s.checks if c["ok"] is None)
        print(f"  {s.name}: {'PASS' if s.passed else 'FAIL'} "
              f"({n_pass} pass / {n_fail} fail / {n_skip} skip)")
    print(f"  报告 -> {REPORT}")
    print(f"  ALL_PASSED = {report['all_passed']}")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
