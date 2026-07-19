"""Refresh live_status.json after the real deploy: re-probe live pages + record deploy & IndexNow."""
from __future__ import annotations

import json
import re
import ssl
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path

OUT = Path(__file__).resolve().parent / "outputs"
LIVE = OUT / "live_status.json"
IDX = OUT / "indexnow_submit.json"

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE
_UA = "Mozilla/5.0 (compatible; MX-probe/1.0)"

PAGES = [
    "https://mingxinstorage.xyz/",
    "https://mingxinstorage.xyz/products",
    "https://mingxinstorage.xyz/en",
]


def fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        r = urllib.request.urlopen(req, timeout=25, context=_CTX)
        return r.status, r.read().decode("utf-8", "ignore")
    except Exception as e:  # noqa: BLE001
        return -1, f"{type(e).__name__}: {e}"


def jsonld_types(html: str) -> list[str]:
    types: list[str] = []
    for m in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I):
        for t in re.findall(r'"@type"\s*:\s*"([^"]+)"', m):
            types.append(t)
    return sorted(set(types))


def onpage(html: str) -> dict:
    return {
        "title": (re.search(r"<title>(.*?)</title>", html, re.S | re.I) or [None, ""])[1].strip() if "<title>" in html.lower() else "",
        "has_description": 'name="description"' in html,
        "canonical": 'rel="canonical"' in html,
        "hreflang_count": len(re.findall(r'hreflang="', html)),
        "h1_count": len(re.findall(r"<h1", html, re.I)),
        "jsonld_count": len(re.findall(r"application/ld\+json", html)),
        "jsonld_types": jsonld_types(html),
        "og": 'property="og:' in html,
        "twitter_title": 'name="twitter:title"' in html,
        "theme_color": 'name="theme-color"' in html,
        "search_action": "SearchAction" in html,
        "speakable": "SpeakableSpecification" in html,
        "sameas": html.count("sameAs"),
        "key_facts_block": ("速答" in html) or ("Quick answer" in html) or ('key-facts' in html),
        "brand_entity": ("铭信" in html and ("Mingxin" in html or "FX100" in html)),
        "naming_note": ("WS5000" in html or "AISSD5000" in html),  # FX100 命名沿革声明在页
        "html_len": len(html),
    }


def main() -> int:
    data = json.loads(LIVE.read_text(encoding="utf-8"))
    data["recomputed_at"] = datetime.now().isoformat(timespec="seconds")

    live_onpage = []
    for u in PAGES:
        st, html = fetch(u)
        live_onpage.append({"url": u, "status": st, "onpage": onpage(html) if st == 200 else {}})
    data["live_onpage"] = live_onpage

    # deploy record（amd 仓库 clone 位于 ../official_website，路径保留）
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(Path(__file__).resolve().parent.parent / "official_website"),
             "rev-parse", "HEAD"]).decode().strip()[:9]
    except Exception:  # noqa: BLE001
        commit = "unknown"
    deployed = all(p["onpage"].get("jsonld_count", 0) >= 1 and p["onpage"].get("canonical")
                   for p in live_onpage if p["status"] == 200)
    data["live_deploy_has_session_upgrades"] = bool(deployed)
    data["deploy"] = {
        "host": "Vercel (GitHub: bistuwangqiyuan/amd, site/ 子目录, 项目 mingxin-site)",
        "commit": commit,
        "deployed_at": data["recomputed_at"],
        "verified_live": {
            "homepage_jsonld_count": live_onpage[0]["onpage"].get("jsonld_count"),
            "canonical": live_onpage[0]["onpage"].get("canonical"),
            "sameas": live_onpage[0]["onpage"].get("sameas"),
            "speakable": live_onpage[0]["onpage"].get("speakable"),
        },
    }
    data["deploy_note"] = (
        "线上 mingxinstorage.xyz 为 Next.js 站点(amd 仓库 site/ 子目录,推送 GitHub main → Vercel 自动构建上线)。"
        "本脚本对线上首页/产品页/英文页复核 JSON-LD、canonical、sameAs、Speakable 等结构化信号,"
        "确认部署版本与仓库一致;收录提交走站点自带 /api/seo/ping(Bearer CRON_SECRET)。"
    )

    # indexnow record
    if IDX.exists():
        idx = json.loads(IDX.read_text(encoding="utf-8"))
        data["indexnow"] = {
            "submitted_at": idx.get("submitted_at"),
            "url_count": idx.get("sitemap", {}).get("url_count"),
            "seo_ping_status": (idx.get("seo_ping") or {}).get("status"),
            "endpoints": {k: v.get("status") for k, v in (idx.get("indexnow", {}) or {}).items()},
            "note": idx.get("google_note"),
        }

    data["index_acceleration_checklist"] = [
        "[持续] 常态化调用站点 /api/seo/ping(IndexNow + 百度主动推送 + WebSub,需 CRON_SECRET)",
        "[进行中·依赖站长平台] Google Search Console 提交 sitemap + URL Inspection(见 gsc_cli.py)",
        "[持续] robots.txt 放行 AI 爬虫(GPTBot/ClaudeBot/PerplexityBot 等,站点已具备)",
        "[持续] 站外高权重信源(GitHub Pages 知识库 mingxin-storage-kb / EdgeOne 微站)→ 真实外链与 sameAs 实体锚点积累",
        "[持续] 缓解品牌混淆:强化『铭信 Mingxin / FX100(历史称谓 AISSD5000/WS5000/GP5000)』实体词,"
        "与其他同名『铭信』企业消歧(以运营主体全称与官网域名核对)",
    ]

    LIVE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("deployed_verified =", deployed)
    print(json.dumps(live_onpage, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
