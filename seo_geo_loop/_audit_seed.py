# -*- coding: utf-8 -*-
import json, time

order = "aamerica.icu|ab2b.icu|abest.icu|abot.pw|acash.icu|acomputers.icu|acredit.icu|adesign.icu|aed.pw|afd.pw|afilm.icu|afr.pw|afree.icu|agold.icu|agp.pw|ahelp.icu|aho.pw|aholiday.icu|aiah.top|aiaj.top|aial.top|aidu.fun|aijo.top|ainternet.icu|airai.top|airv.top|aiwb.top|ajai.top|alasvegas.icu|alawyer.icu|aloan.icu|aly.pw|amarketing.icu|amobile.icu|amp3.icu|amusic.icu|anews.icu|aqm.pw|aqw.pw|arn.pw|arr.pw|asale.icu|asecurity.icu|asports.icu|assume.pw|aup.pw|awine.icu|ayt.pw|azai.top|bavo.top|bby.pw|bdc.pw|bey.pw|bgn.pw|bhm.pw|bia.pw|biw.pw|bix.pw|bjx.pw|blex.top|bmb.pw|bmt.pw|bns.pw|bqg.pw|bqs.pw|brp.pw|bry.pw|bwl.pw|bwy.pw|bys.pw|caiq.top|cbl.pw|ccl.pw|ckc.pw|clawall.pw|clawbank.pw|clawinfo.pw|clawit.pw|clawlaw.pw|clawmen.pw|clawmy.pw|clawnet.pw|clawon.pw|clawtop.pw|clawus.pw|clawweb.pw|clawwww.pw|clg.pw|clj.pw|cln.pw|clov.top|clz.pw|cml.pw|cmx.pw|codeclaw.pw|cou.pw|cov.pw|crix.top|csr.pw|cur.pw|dcp.pw|ddo.pw|dollarai.top|drof.top|emoj.top|equal.pw|fova.top|goni.top|govai.top|iclaw.asia|idai.top|ioni.top|isai.top|jafu.top|jaiq.top|kept.pw|kova.top|lafi.top|lako.top|ltdai.top|luisuantech.top|lvsuan.top|mangosea.top|mavo.top|micro4.top|microai.icu|nait.top|nira.top|occur.pw|orbx.top|qore.top|sech.site|sizz.top|taking.pw|tudy.top|ultrai.top|upper.pw|vaku.top|vuke.top|wimo.top|woro.top|xaiy.top|yaiz.top|zaiv.top|zoka.top".split("|")

p = "outputs/gsc_index_status_audit.json"
out = {
    "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "method": "browser URL Inspection read-only (no Request-Indexing, no quota consumed)",
    "status_legend": {
        "indexed": "网址已收录到 Google",
        "not_indexed": "网址尚未收录到 Google",
        "not_in_property": "URL 不属于该资源",
        "timeout": "状态文本未在超时内出现，需复查",
    },
    "total": len(order),
    "order": order,
    "results": {
        "aamerica.icu": "indexed",
        "ab2b.icu": "indexed",
        "abest.icu": "indexed",
        "abot.pw": "indexed",
        "acash.icu": "indexed",
        "acomputers.icu": "indexed",
    },
}
json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("seeded", p, "done=", len(out["results"]), "remaining=", len(order) - len(out["results"]))
