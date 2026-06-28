# -*- coding: utf-8 -*-
"""中科存储 goni.top · "24h 自动 GEO + 自动 SEO" 验收测试（可复现 PASS/FAIL）。

两个套件（与计划一致，单一事实源复用引擎逻辑）：

  live        线上站点契约：sitemap/robots/llms/IndexNow 一致；全站链接可达；
              关键页 JSON-LD/canonical/hreflang/meta/h1/OG/SearchAction；
              内容新鲜度（<time datetime>）在阈值内 = 证明每日自动刷新仍在跑。
  automation  24h 自动化契约：workflow 含 schedule+dispatch；gh 可用且已认证；
              仓库 Secrets 齐备；最近一次运行 recent 且 conclusion==success。

诚实纪律：客观人工受限项（GSC 配额 / ICP / UGC）不计为失败；
gh 不可用时相关检查标记 SKIP（视为未通过，不伪造绿）。

复现：
  python tests/test_geo_seo_autopilot.py            # 跑全部
  python tests/test_geo_seo_autopilot.py --live     # 只跑线上
  python tests/test_geo_seo_autopilot.py --automation
环境变量：ZK_SITE_URL, ZK_FRESH_DAYS, ZK_REPO, ZK_INDEXNOW_KEY
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

SITE = os.environ.get("ZK_SITE_URL", "https://goni.top").rstrip("/")
REPO = os.environ.get("ZK_REPO", "bistuwangqiyuan/zk-geo-autopilot")
WORKFLOW = os.environ.get("ZK_WORKFLOW", "geo-autopilot.yml")
INDEXNOW_KEY = os.environ.get("ZK_INDEXNOW_KEY", "REDACTED_INDEXNOW_KEY")
FRESH_DAYS = int(os.environ.get("ZK_FRESH_DAYS", "2"))
RUN_MAX_AGE_H = float(os.environ.get("ZK_RUN_MAX_AGE_H", "26"))

KEY_PAGES = [
    f"{SITE}/zh/index.html",
    f"{SITE}/zh/product.html",
    f"{SITE}/en/index.html",
]
REQUIRED_SECRETS = ["DASHSCOPE_API_KEY", "GH_PAT"]

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(HERE, "last_report.json")
TODAY = dt.date.today()

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE
_UA = "Mozilla/5.0 (compatible; ZK-GEO-SEO-Test/1.0; +https://goni.top/)"


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
    robots_ok = (rst == 200 and "sitemap.xml" in rbody.lower()
                 and re.search(r"user-agent:\s*googlebot", rbody, re.I)
                 and re.search(r"user-agent:\s*gptbot", rbody, re.I))
    s.add("robots_ok", bool(robots_ok),
          f"status={rst}, refs_sitemap={'sitemap.xml' in rbody.lower()}, "
          f"allows_googlebot={bool(re.search(r'googlebot', rbody, re.I))}, "
          f"allows_gptbot={bool(re.search(r'gptbot', rbody, re.I))}")

    # llms.txt (GEO 事实索引)
    lst, lbody = fetch(f"{SITE}/llms.txt")
    s.add("llms_txt_ok", lst == 200 and len(lbody.strip()) > 50,
          f"status={lst}, len={len(lbody.strip())}")

    # IndexNow key file
    kurl = f"{SITE}/{INDEXNOW_KEY}.txt"
    kst, kbody = fetch(kurl)
    s.add("indexnow_key_ok", kst == 200 and kbody.strip() == INDEXNOW_KEY,
          f"status={kst}, matches={kbody.strip() == INDEXNOW_KEY} ({kurl})")

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
        objs, n_blocks, errs = jsonld_blocks(html)
        types = jsonld_types(objs)
        canonical = bool(re.search(r'rel="canonical"', html, re.I))
        hreflang = len(re.findall(r'rel="alternate"\s+hreflang', html, re.I))
        desc = bool(re.search(r'<meta\s+name="description"', html, re.I))
        h1 = len(re.findall(r"<h1\b", html, re.I))
        og = bool(re.search(r'property="og:', html, re.I))
        tw = bool(re.search(r'name="twitter:title"', html, re.I))
        theme = bool(re.search(r'name="theme-color"', html, re.I))
        search_action = "SearchAction" in html
        pdate = max_page_date(html)
        if pdate:
            page_dates.append((url, pdate))

        page_ok = (errs == 0 and n_blocks > 0
                   and ("WebPage" in types or "WebSite" in types)
                   and "Organization" in types
                   and canonical and hreflang >= 2 and desc and h1 == 1
                   and og and tw and theme and search_action)
        s.add(f"page_ok::{url}", page_ok,
              f"jsonld_blocks={n_blocks},parse_errs={errs},types={types},"
              f"canonical={canonical},hreflang={hreflang},desc={desc},h1={h1},"
              f"og={og},twitter={tw},theme={theme},search_action={search_action}")

        # product 结构化数据：若含 Product 必须带 offers/aggregateRating/review 之一
        if url.endswith("product.html"):
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

    # freshness = 自动刷新仍在跑的证据
    if page_dates:
        newest = max(d for _, d in page_dates)
        age = (TODAY - newest).days
        s.add("content_freshness", age <= FRESH_DAYS,
              f"newest_page_date={newest.isoformat()}, age_days={age}, "
              f"threshold={FRESH_DAYS} (>阈值=每日自动化已停摆)")
    else:
        s.add("content_freshness", False, "关键页未找到 <time datetime> 新鲜度标记")

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
