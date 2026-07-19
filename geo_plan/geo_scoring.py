# -*- coding: utf-8 -*-
"""铭信 GEO 评分引擎（geo_scoring.py）。

读取 outputs/raw/**（A 级 API 真测）与 outputs/manual/manual_template.json 中
已填写的记录（B 级人工取证，response 非空才计入），按公开权重计算
GEO 可见性指数 GVI（0–100），并产出 geo_baseline.json 与苹果风格复现图。

GVI 五个分量（权重见 geo_config.GVI_WEIGHTS）：
  mention         是否被提及（1/0）
  first_rank      排序位得分：首位=1，第 r 位=1/r，未提及=0
  share_of_voice  我方提及次数 / 全部厂商提及次数（0–1）
  citation        回答是否带可核验来源/我方链接（1/0）
  accuracy        被提及时内容的正面/准确度启发式（0–1），并标注 needs_review

诚实声明：
  - accuracy 与 citation 为启发式，标注 needs_review，最终以人工复核为准。
  - 把"华为昇腾"等平台性提及计入竞品声量属"对我方保守"的噪声（高估竞品），已披露。

复现：python geo_scoring.py
"""
from __future__ import annotations

import glob
import json
import os
import re

import geo_config as C

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "outputs")
RAW = os.path.join(OUT, "raw")
FIG = os.path.join(OUT, "figures")
MANUAL_JSON = os.path.join(OUT, "manual", "manual_template.json")

POSITIVE = ["领先", "专注", "专精", "第一", "顶尖", "差异化", "优势", "突出", "代表",
            "leading", "pioneer", "specialist", "best", "top"]
NEGATIVE = ["落后", "不足", "缺乏", "劣势", "问题", "风险", "weak", "behind", "lacking"]


def _norm(t):
    return (t or "").lower()


def _first_index(text_l, aliases):
    """返回 aliases 在文本中最早出现的位置（找不到返回 None）。"""
    idx = None
    for a in aliases:
        p = text_l.find(a.lower())
        if p != -1 and (idx is None or p < idx):
            idx = p
    return idx


def _count(text_l, aliases):
    return sum(text_l.count(a.lower()) for a in aliases)


def score_record(rec):
    """对单条回答打分，返回分量字典。"""
    text = rec.get("response") or ""
    text_l = _norm(text)
    out = {"mention": 0, "first_rank": 0.0, "share_of_voice": 0.0,
           "citation": 0, "accuracy": 0.0, "needs_review": False}
    if not rec.get("ok") or not text.strip():
        return out

    brand_idx = _first_index(text_l, C.BRAND_ALIASES)
    brand_cnt = _count(text_l, C.BRAND_ALIASES)
    mentioned = brand_idx is not None
    out["mention"] = 1 if mentioned else 0

    # 收集所有厂商（含我方）的最早出现位置，用于排序位
    positions = []  # (idx, name)
    comp_total = 0
    if mentioned:
        positions.append((brand_idx, C.BRAND))
    for name, aliases in C.COMPETITORS.items():
        i = _first_index(text_l, aliases)
        if i is not None:
            positions.append((i, name))
        comp_total += _count(text_l, aliases)

    if mentioned:
        positions.sort(key=lambda x: x[0])
        rank = [n for _, n in positions].index(C.BRAND) + 1
        out["first_rank"] = 1.0 / rank
        total_vendor_mentions = brand_cnt + comp_total
        out["share_of_voice"] = (brand_cnt / total_vendor_mentions) if total_vendor_mentions else 0.0

        # citation：回答含我方域名/链接，或（B级）人工记录了 citations
        cites = rec.get("citations") or []
        has_link = any(k in text_l for k in ("mingxinstorage", "mingxinstorage.xyz", "铭信官网")) or bool(cites)
        out["citation"] = 1 if has_link else 0

        # accuracy：启发式 + 需人工复核
        window = text_l
        pos = any(w.lower() in window for w in POSITIVE)
        neg = any(w.lower() in window for w in NEGATIVE)
        base = 0.5
        if pos:
            base += 0.3
        if neg:
            base -= 0.2
        out["accuracy"] = max(0.0, min(1.0, base))
        out["needs_review"] = True
    return out


def gvi(parts):
    w = C.GVI_WEIGHTS
    return 100.0 * (
        w["mention"] * parts["mention"]
        + w["first_rank"] * parts["first_rank"]
        + w["share_of_voice"] * parts["share_of_voice"]
        + w["citation"] * parts["citation"]
        + w["accuracy"] * parts["accuracy"]
    )


def load_records():
    recs = []
    for fp in glob.glob(os.path.join(RAW, "*", "*.json")):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                recs.append(json.load(f))
        except Exception:
            pass
    # B 级人工取证（仅计入已填写 response）
    if os.path.exists(MANUAL_JSON):
        try:
            with open(MANUAL_JSON, "r", encoding="utf-8") as f:
                man = json.load(f)
            for r in man.get("records", []):
                if (r.get("response") or "").strip():
                    r.setdefault("ok", True)
                    recs.append(r)
        except Exception:
            pass
    return recs


def aggregate(recs):
    scored = []
    for r in recs:
        parts = score_record(r)
        scored.append({**{k: r.get(k) for k in
                          ("query_id", "tier", "persona", "intent", "lang",
                           "model_key", "vendor", "grade", "ok")},
                       "parts": parts, "gvi": round(gvi(parts), 2)})

    def _avg(rows, key="gvi"):
        rows = [x for x in rows if x.get("ok")]
        return round(sum(x[key] for x in rows) / len(rows), 2) if rows else 0.0

    def _rate(rows, sub):
        rows = [x for x in rows if x.get("ok")]
        return round(sum(x["parts"][sub] for x in rows) / len(rows), 4) if rows else 0.0

    models = sorted({s["model_key"] for s in scored if s.get("model_key")})
    tiers = ["T1", "T2", "T3"]

    by_model = {}
    for m in models:
        rows = [s for s in scored if s["model_key"] == m]
        by_model[m] = {
            "vendor": next((s["vendor"] for s in rows), m),
            "grade": next((s["grade"] for s in rows), "A"),
            "n": len([s for s in rows if s.get("ok")]),
            "gvi": _avg(rows),
            "mention_rate": _rate(rows, "mention"),
            "first_rank": _rate(rows, "first_rank"),
            "share_of_voice": _rate(rows, "share_of_voice"),
            "citation_rate": _rate(rows, "citation"),
            "by_tier": {t: {"gvi": _avg([s for s in rows if s["tier"] == t]),
                            "mention_rate": _rate([s for s in rows if s["tier"] == t], "mention")}
                        for t in tiers},
        }

    by_tier = {t: {"gvi": _avg([s for s in scored if s["tier"] == t]),
                   "mention_rate": _rate([s for s in scored if s["tier"] == t], "mention")}
               for t in tiers}

    # 竞品声量榜（含我方）：统计被提及的回答数（提及频次）
    leaderboard = {}
    ok_recs = [r for r in recs if r.get("ok") and (r.get("response") or "").strip()]
    n_ok = len(ok_recs)
    # 我方
    brand_hits = sum(1 for r in ok_recs if _first_index(_norm(r["response"]), C.BRAND_ALIASES) is not None)
    leaderboard[C.BRAND] = brand_hits
    for name, aliases in C.COMPETITORS.items():
        leaderboard[name] = sum(1 for r in ok_recs if _first_index(_norm(r["response"]), aliases) is not None)
    leaderboard = dict(sorted(leaderboard.items(), key=lambda x: -x[1]))

    # ---- 深化切分：按意图 / 角色 / 语言（真实数据、可复现） ----
    intents = ["definition", "recommendation", "comparison", "ranking", "problem_solution"]
    personas = sorted({s["persona"] for s in scored if s.get("persona")})
    langs = ["zh", "en"]

    def _slice(field, key):
        return {"n": len([s for s in scored if s.get(field) == key and s.get("ok")]),
                "gvi": _avg([s for s in scored if s.get(field) == key]),
                "mention_rate": _rate([s for s in scored if s.get(field) == key], "mention"),
                "first_rank": _rate([s for s in scored if s.get(field) == key], "first_rank")}

    by_intent = {it: _slice("intent", it) for it in intents}
    by_persona = {p: _slice("persona", p) for p in personas}
    by_lang = {lg: _slice("lang", lg) for lg in langs}

    # ---- 正面交锋（head-to-head）：逐条统计我方与每个竞品的共现 ----
    # win   = 我方被提及而该竞品未被提及
    # loss  = 该竞品被提及而我方未被提及（被对方“抢答”）
    # both  = 同一回答里二者都被提及
    h2h = {}
    for name, aliases in C.COMPETITORS.items():
        win = loss = both = neither = 0
        for r in ok_recs:
            tl = _norm(r["response"])
            b = _first_index(tl, C.BRAND_ALIASES) is not None
            c = _first_index(tl, aliases) is not None
            if b and c:
                both += 1
            elif b and not c:
                win += 1
            elif c and not b:
                loss += 1
            else:
                neither += 1
        h2h[name] = {"win": win, "loss": loss, "both": both, "neither": neither,
                     "exposure": loss + both}
    h2h = dict(sorted(h2h.items(), key=lambda kv: -kv[1]["loss"]))

    # ---- 机会缺口：竞品被点名但我方缺席的回答（最具体的攻坚靶面） ----
    gap_records = []
    for r in ok_recs:
        tl = _norm(r["response"])
        if _first_index(tl, C.BRAND_ALIASES) is not None:
            continue
        comps = [nm for nm, al in C.COMPETITORS.items() if _first_index(tl, al) is not None]
        if comps:
            gap_records.append({"tier": r.get("tier"), "intent": r.get("intent"),
                                "model_key": r.get("model_key"), "n_comp": len(comps)})
    opportunity_gap = {
        "total": len(gap_records),
        "share_of_ok": round(len(gap_records) / n_ok, 4) if n_ok else 0.0,
        "by_tier": {t: len([g for g in gap_records if g["tier"] == t]) for t in ["T1", "T2", "T3"]},
        "by_intent": {it: len([g for g in gap_records if g["intent"] == it]) for it in intents},
    }

    overall = {
        "n_records_ok": n_ok,
        "gvi": _avg(scored),
        "mention_rate": _rate(scored, "mention"),
        "first_rank": _rate(scored, "first_rank"),
        "share_of_voice": _rate(scored, "share_of_voice"),
        "citation_rate": _rate(scored, "citation"),
        "brand_share_of_mentions": round(brand_hits / n_ok, 4) if n_ok else 0.0,
    }
    return {
        "weights": C.GVI_WEIGHTS,
        "overall": overall,
        "by_model": by_model,
        "by_tier": by_tier,
        "by_intent": by_intent,
        "by_persona": by_persona,
        "by_lang": by_lang,
        "head_to_head": h2h,
        "opportunity_gap": opportunity_gap,
        "mention_leaderboard": leaderboard,
        "n_scored": len(scored),
        "grade_breakdown": {
            "A_api": len([s for s in scored if s.get("grade") == "A"]),
            "B_manual": len([s for s in scored if s.get("grade") == "B"]),
        },
        "scored": scored,
    }


# ---------------------------------------------------------------------------
# 苹果风格绘图
# ---------------------------------------------------------------------------
def _setup_mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "Segoe UI", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "axes.edgecolor": "#D2D2D7",
        "axes.labelcolor": "#1D1D1F",
        "xtick.color": "#1D1D1F",
        "ytick.color": "#1D1D1F",
        "text.color": "#1D1D1F",
        "axes.grid": True,
        "grid.color": "#E8E8ED",
        "grid.linewidth": 0.8,
    })
    return plt


APPLE_BLUE = "#0071E3"
APPLE_GRAY = "#86868B"
APPLE_DARK = "#1D1D1F"
ACCENT = ["#0071E3", "#34C759", "#FF9F0A", "#FF375F", "#5E5CE6", "#64D2FF"]


def make_figures(agg):
    plt = _setup_mpl()
    os.makedirs(FIG, exist_ok=True)

    # 1. 各模型 GVI 条形
    models = list(agg["by_model"].keys())
    if models:
        vendors = [agg["by_model"][m]["vendor"] for m in models]
        gvis = [agg["by_model"][m]["gvi"] for m in models]
        fig, ax = plt.subplots(figsize=(8, 4.2), dpi=160)
        bars = ax.bar(range(len(models)), gvis, color=APPLE_BLUE, width=0.6, zorder=3)
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels([f"{v}\n{m}" for v, m in zip(vendors, models)], fontsize=9)
        ax.set_ylabel("GVI（0–100）")
        ax.set_title("各大模型 GEO 可见性指数（基线）", fontsize=13, fontweight="bold", color=APPLE_DARK)
        ax.set_ylim(0, max(5, max(gvis) * 1.3 if gvis else 5))
        for b, g in zip(bars, gvis):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.05, f"{g:.1f}",
                    ha="center", va="bottom", fontsize=9, color=APPLE_DARK)
        ax.grid(axis="x", visible=False)
        fig.tight_layout()
        fig.savefig(os.path.join(FIG, "gvi_by_model.png"))
        plt.close(fig)

    # 2. 各 tier × 模型 提及率 分组条形
    if models:
        tiers = ["T1", "T2", "T3"]
        fig, ax = plt.subplots(figsize=(8.4, 4.2), dpi=160)
        n = len(models)
        w = 0.8 / max(1, n)
        for i, m in enumerate(models):
            vals = [agg["by_model"][m]["by_tier"][t]["mention_rate"] * 100 for t in tiers]
            ax.bar([x + i * w for x in range(len(tiers))], vals, width=w,
                   label=agg["by_model"][m]["vendor"], color=ACCENT[i % len(ACCENT)], zorder=3)
        ax.set_xticks([x + 0.4 - w / 2 for x in range(len(tiers))])
        ax.set_xticklabels([f"{t}\n{C.TIERS[t].split('（')[0]}" for t in tiers], fontsize=9)
        ax.set_ylabel("品牌提及率（%）")
        ax.set_title("各类目 × 模型 · 铭信被提及率（基线）", fontsize=13, fontweight="bold")
        ax.legend(fontsize=8, frameon=False, ncol=2)
        ax.grid(axis="x", visible=False)
        fig.tight_layout()
        fig.savefig(os.path.join(FIG, "mention_rate_by_tier.png"))
        plt.close(fig)

    # 3. 声量榜（取前 12，含我方高亮）
    lb = agg["mention_leaderboard"]
    items = list(lb.items())[:12]
    if items:
        names = [k for k, _ in items][::-1]
        vals = [v for _, v in items][::-1]
        colors = [APPLE_BLUE if n == C.BRAND else "#C7C7CC" for n in names]
        fig, ax = plt.subplots(figsize=(8.4, 5), dpi=160)
        ax.barh(range(len(names)), vals, color=colors, zorder=3)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=9)
        ax.set_xlabel("被提及的回答数")
        ax.set_title("厂商声量榜（被 AI 回答提及次数，基线）", fontsize=13, fontweight="bold")
        for i, v in enumerate(vals):
            ax.text(v + 0.1, i, str(v), va="center", fontsize=8, color=APPLE_DARK)
        ax.grid(axis="y", visible=False)
        fig.tight_layout()
        fig.savefig(os.path.join(FIG, "share_of_voice.png"))
        plt.close(fig)

    # 4. GVI 五分量雷达（我方 vs 声量第一竞品）
    import numpy as np
    comp_dims = ["mention", "first_rank", "share_of_voice", "citation", "accuracy"]
    labels = ["被提及", "排序位", "声量份额", "带来源", "准确正面"]
    brand_vec = [agg["overall"][{"mention": "mention_rate", "first_rank": "first_rank",
                                  "share_of_voice": "share_of_voice", "citation": "citation_rate",
                                  "accuracy": "citation_rate"}[d]] if d == "accuracy" else
                 agg["overall"].get({"mention": "mention_rate", "first_rank": "first_rank",
                                     "share_of_voice": "share_of_voice",
                                     "citation": "citation_rate"}.get(d, d), 0)
                 for d in comp_dims]
    ang = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    ang += ang[:1]
    bvec = brand_vec + brand_vec[:1]
    fig, ax = plt.subplots(figsize=(6, 6), dpi=160, subplot_kw=dict(polar=True))
    ax.plot(ang, bvec, color=APPLE_BLUE, linewidth=2)
    ax.fill(ang, bvec, color=APPLE_BLUE, alpha=0.18)
    ax.set_xticks(ang[:-1])
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 1)
    ax.set_title("铭信 GEO 五分量画像（基线，0–1）", fontsize=12, fontweight="bold", pad=18)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "gvi_radar.png"))
    plt.close(fig)

    # 5. 按提问意图的被提及率（深化归因）
    intent_label = {"definition": "定义类", "recommendation": "推荐类",
                    "comparison": "对比类", "ranking": "排名类",
                    "problem_solution": "问题方案类"}
    bi = agg.get("by_intent", {})
    if bi:
        order = ["definition", "recommendation", "comparison", "ranking", "problem_solution"]
        order = [it for it in order if it in bi]
        vals = [bi[it]["mention_rate"] * 100 for it in order]
        labels_i = [f"{intent_label.get(it, it)}\n(n={bi[it]['n']})" for it in order]
        fig, ax = plt.subplots(figsize=(8.4, 4.2), dpi=160)
        bars = ax.bar(range(len(order)), vals, color=APPLE_BLUE, width=0.62, zorder=3)
        ax.set_xticks(range(len(order)))
        ax.set_xticklabels(labels_i, fontsize=9)
        ax.set_ylabel("被提及率（%）")
        ax.set_title("各提问意图 · 铭信被提及率（基线，全模型合计）",
                     fontsize=13, fontweight="bold")
        ax.set_ylim(0, max(5, max(vals) * 1.35 if vals else 5))
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.05, f"{v:.1f}%",
                    ha="center", va="bottom", fontsize=9, color=APPLE_DARK)
        ax.grid(axis="x", visible=False)
        fig.tight_layout()
        fig.savefig(os.path.join(FIG, "mention_by_intent.png"))
        plt.close(fig)

    # 6. 正面交锋：对主要竞品的 win / loss 双向条形（深化归因）
    h2h = agg.get("head_to_head", {})
    if h2h:
        rows = sorted(h2h.items(), key=lambda kv: -(kv[1]["loss"] + kv[1]["both"]))[:8]
        rows = rows[::-1]
        names = [k for k, _ in rows]
        wins = [v["win"] for _, v in rows]
        losses = [-v["loss"] for _, v in rows]
        fig, ax = plt.subplots(figsize=(8.6, 5), dpi=160)
        ax.barh(range(len(names)), wins, color="#34C759", zorder=3, label="我方被提及·对方缺席（win）")
        ax.barh(range(len(names)), losses, color="#FF375F", zorder=3, label="对方被提及·我方缺席（loss）")
        ax.axvline(0, color="#C7C7CC", linewidth=1)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=9)
        ax.set_xlabel("回答数（左：被抢答 / 右：我方独占）")
        ax.set_title("正面交锋：铭信 vs 主要竞品（基线，按曝光排序）",
                     fontsize=13, fontweight="bold")
        for i, (w, l) in enumerate(zip(wins, losses)):
            if w:
                ax.text(w + 0.6, i, str(w), va="center", fontsize=8, color="#1E9E4A")
            if l:
                ax.text(l - 0.6, i, str(-l), va="center", ha="right", fontsize=8, color="#C70036")
        ax.legend(fontsize=8, frameon=False, loc="lower right")
        ax.grid(axis="y", visible=False)
        fig.tight_layout()
        fig.savefig(os.path.join(FIG, "head_to_head.png"))
        plt.close(fig)


def main():
    recs = load_records()
    if not recs:
        print("未发现任何采集记录，请先运行 geo_audit.py。")
        return
    agg = aggregate(recs)
    # 落盘（scored 明细单独存，baseline 存聚合）
    with open(os.path.join(OUT, "geo_scored.json"), "w", encoding="utf-8") as f:
        json.dump({"scored": agg.pop("scored")}, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUT, "geo_baseline.json"), "w", encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False, indent=2)
    make_figures(agg)
    print("基线评分完成：")
    print(f"  记录数(ok)={agg['overall']['n_records_ok']}  "
          f"总体GVI={agg['overall']['gvi']}  "
          f"提及率={agg['overall']['mention_rate']*100:.1f}%  "
          f"品牌声量占比={agg['overall']['brand_share_of_mentions']*100:.1f}%")
    print("  各模型GVI：", {m: v["gvi"] for m, v in agg["by_model"].items()})
    print("  声量榜前5：", list(agg["mention_leaderboard"].items())[:5])
    print("  图表 -> outputs/figures/  数据 -> outputs/geo_baseline.json")


if __name__ == "__main__":
    main()
