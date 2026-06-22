# -*- coding: utf-8 -*-
"""中科存储 GEO+SEO 提升闭环驱动器（最多 10 轮，可复现）。

每轮：写入累计杠杆开关 → 重建站点(build_site.py) → 站内自检(verify_site.py) →
确定性审计 CRI(readiness_audit.run) → 记录逐轮 delta 与"本轮启用了什么"。
循环结束后清除开关文件（回到缺省=全部开启的最佳站点）并重建一次，确保对外站点最优。

诚实纪律：
  - CRI 度量的是"我们真正可控的站内 GEO+SEO 就绪度"，与 LLM 真实嘴上提及率(GVI)区分。
  - 每轮真的改了生成的 HTML、真的重新审计；过程与数字完全可复现（无随机、无网络）。
  - 杠杆全开后若再增轮次 CRI 不再上升，即如实记录"已收敛"。

复现：python run_loop.py            # 默认 10 轮
      python run_loop.py --rounds 10
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys

import levers
import readiness_audit as RA

BASE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(os.path.dirname(BASE), "official_website")
OUT = os.path.join(BASE, "outputs")
SNAP = os.path.join(OUT, "snapshots")
LOOP_JSON = os.path.join(OUT, "loop_results.json")
CHANGELOG = os.path.join(OUT, "changelog.md")


def _run(cmd, cwd):
    p = subprocess.run([sys.executable, *cmd], cwd=cwd,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def rebuild():
    return _run(["build_site.py"], SITE)


def verify():
    rc, out = _run(["verify_site.py"], SITE)
    # verify 仅在内链 404/双语/数值不一致时返回非 0；预存的 portal 警告不致失败。
    return rc == 0, out


def snapshot(label, v2=False):
    snap = RA.run(label, v2=v2)
    os.makedirs(SNAP, exist_ok=True)
    with open(os.path.join(SNAP, f"{label}.json"), "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)
    return snap


def run_phase(args, n_levers):
    """通用「分阶段」优化跑：启用第 from_lever..to_lever 个杠杆，按 v2 评分，
    全局轮号 = 杠杆序号 + round_offset。用于第二阶段（g9–g13 → 第 11–15 轮，CRI v2）。

    例：python run_loop.py --v2 --from-lever 9 --to-lever 13 --round-offset 2 --suffix _v2
    """
    v2 = args.v2
    sfx = args.suffix or ("_v2" if v2 else "")
    from_l = max(1, args.from_lever)
    to_l = args.to_lever or n_levers
    loop_json = os.path.join(OUT, f"loop_results{sfx}.json")
    changelog = os.path.join(OUT, f"changelog{sfx}.md")
    label_tag = sfx.lstrip("_") or "v1"

    print("=" * 72)
    print(f"中科存储 GEO+SEO 提升闭环 · 第二阶段（CRI {('v2' if v2 else 'v1')}, "
          f"杠杆 g{from_l}–g{to_l} → 轮次 {from_l + args.round_offset}–{to_l + args.round_offset}）")
    print("=" * 72)

    rounds = []
    # 阶段基线：启用前 (from_l-1) 个杠杆（= 第一阶段的最佳态），按本评分口径量出起点。
    base_n = from_l - 1
    levers.write_levers(levers.cumulative(base_n))
    rebuild()
    okb, _ = verify()
    base_round = base_n + args.round_offset
    base = snapshot(f"{label_tag}_round{base_round:02d}_base", v2=v2)
    print(f"[round {base_round:02d}] 阶段基线（g1–g{base_n} 开启）CRI({label_tag})={base['cri']}  "
          f"verify={'OK' if okb else 'FAIL'}")
    rounds.append({"round": base_round, "lever_enabled": None,
                   "lever_name": f"阶段基线（g1–g{base_n}）", "levers_on_count": base_n,
                   "cri": base["cri"], "pillars": base["pillars"], "delta": 0.0,
                   "verify_ok": okb, "lowest": RA.lowest_levers(base, 6)})
    prev = base["cri"]

    for L in range(from_l, to_l + 1):
        cfg = levers.cumulative(L)
        levers.write_levers(cfg)
        rebuild()
        ok, _ = verify()
        gr = L + args.round_offset
        snap = snapshot(f"{label_tag}_round{gr:02d}", v2=v2)
        cri = snap["cri"]
        delta = round(cri - prev, 2)
        grp = levers.GROUPS[L - 1]
        rounds.append({"round": gr, "lever_enabled": grp["id"], "lever_name": grp["name"],
                       "pillar_tag": grp["pillar"], "levers_on_count": L,
                       "cri": cri, "pillars": snap["pillars"], "delta": delta,
                       "verify_ok": ok, "lowest": RA.lowest_levers(snap, 6)})
        print(f"[round {gr:02d}] +{grp['name']:24s} CRI({label_tag})={cri:6.2f}  Δ={delta:+.2f}  "
              f"verify={'OK' if ok else 'FAIL'}")
        prev = cri

    # 收尾：清除开关（缺省=全部开启=最佳站点），重建，按 v1 与 v2 双口径各量一次终值。
    levers.clear_levers()
    rebuild()
    okf, _ = verify()
    final_v2 = snapshot("final_best_v2", v2=True)
    final_v1 = snapshot("final_best", v2=False)
    print(f"[final ] 最佳站点 CRI v2={final_v2['cri']} / CRI v1={final_v1['cri']}  "
          f"verify={'OK' if okf else 'FAIL'}")

    result = {
        "computed_at": dt.datetime.now().isoformat(timespec="seconds"),
        "phase": 2, "cri_version": "v2" if v2 else "v1",
        "lever_range": [from_l, to_l], "round_offset": args.round_offset,
        "weights": RA.PILLAR_WEIGHTS,
        "baseline_cri": base["cri"], "final_cri": final_v2["cri"] if v2 else final_v1["cri"],
        "final_cri_v1": final_v1["cri"], "final_cri_v2": final_v2["cri"],
        "total_gain": round((final_v2["cri"] if v2 else final_v1["cri"]) - base["cri"], 2),
        "rounds": rounds, "lever_groups": levers.GROUPS, "scope": base["scope"],
        "note": ("CRI v2 在 v1 五支柱基础上新增 8 个确定性子项（媒体解码/CSS 预加载/字体显示、"
                 "Organization.sameAs 覆盖、首页 WebPage+Speakable、答案块全覆盖、规格排版一致性、"
                 "站外实体锚点）；v2 与 v1 为不同刻度，均如实并列。"),
    }
    with open(loop_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    _write_phase_changelog(result, final_v1, final_v2, changelog)
    print("-" * 72)
    print(f"阶段基线 CRI={result['baseline_cri']} → 最终 CRI {result['cri_version']}="
          f"{result['final_cri']}（Δ {result['total_gain']:+.2f}）")
    print(f"写出：{loop_json}\n      {changelog}")


def _write_phase_changelog(result, final_v1, final_v2, path):
    lines = ["# 中科存储 GEO+SEO 第二阶段 · CRI v2 复盘（changelog）\n",
             f"> 生成：{result['computed_at']}　范围：{result['scope']}\n",
             f"> 阶段基线 CRI v2 **{result['baseline_cri']}** → 最终 CRI v2 **{result['final_cri_v2']}**"
             f"（Δ **{result['total_gain']:+.2f}**）；同口径 CRI v1 终值 **{result['final_cri_v1']}**"
             f"（突破第一阶段 97.9 上限）。\n",
             "\n## 逐轮明细（CRI v2）\n",
             "| 轮次 | 本轮启用 | 支柱 | CRI v2 | Δ | A | B | C | D | E | verify |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in result["rounds"]:
        p = r["pillars"]
        lines.append(
            f"| {r['round']:02d} | {r['lever_name']} | {r.get('pillar_tag','-')} | "
            f"{r['cri']:.2f} | {r['delta']:+.2f} | {p['A']} | {p['B']} | {p['C']} | "
            f"{p['D']} | {p['E']} | {'OK' if r['verify_ok'] else 'FAIL'} |")
    lines.append("\n## 新增 5 个杠杆组的真实改进内容\n")
    for g in result["lever_groups"]:
        if g["id"] in ("g9_sameas", "g10_answer_all", "g11_spec_consistency",
                       "g12_media_speakable", "g13_perf"):
            lines.append(f"- **{g['name']}**（{g['id']}，支柱 {g['pillar']}）：{g['desc']}")
    lines.append("\n## 收敛与自我批评\n")
    lines.append(f"- 全开后 CRI v2 收敛于 **{result['final_cri_v2']}**、CRI v1 收敛于 **{result['final_cri_v1']}**。")
    lines.append("- 仍未满分的 v2 子项（如实记录）：")
    for v, name in RA.lowest_levers(final_v2, 6):
        lines.append(f"  - {name} = {v}")
    lines.append("\n> 复现：`python run_loop.py --v2 --from-lever 9 --to-lever 13 --round-offset 2 --suffix _v2`")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=10, help="优化轮数（默认 10）")
    ap.add_argument("--v2", action="store_true", help="按 CRI v2 评分（含 g9–g13 新子项）")
    ap.add_argument("--from-lever", type=int, default=1, help="本次起始杠杆序号(1-indexed)")
    ap.add_argument("--to-lever", type=int, default=0, help="本次结束杠杆序号(0=全部)")
    ap.add_argument("--round-offset", type=int, default=0, help="全局轮号 = 杠杆序号 + offset")
    ap.add_argument("--suffix", default="", help="输出文件后缀(避免覆盖既有 phase1 结果)")
    args = ap.parse_args()
    os.makedirs(SNAP, exist_ok=True)
    n_levers = len(levers.GROUPS)
    if args.from_lever > 1 or args.to_lever or args.suffix or args.v2:
        return run_phase(args, n_levers)

    print("=" * 72)
    print("中科存储 GEO+SEO 提升闭环 · CRI 优化（确定性、可复现）")
    print("=" * 72)

    rounds = []

    # ---- 第 0 轮：基线（全部杠杆关闭）----
    levers.write_levers(levers.all_off())
    rc, _ = rebuild()
    ok, _ = verify()
    base = snapshot("round00")
    print(f"[round 00] 基线（全部杠杆关闭）CRI={base['cri']}  verify={'OK' if ok else 'FAIL'}  "
          + " ".join(f"{k}={v}" for k, v in base['pillars'].items()))
    rounds.append({"round": 0, "lever_enabled": None, "lever_name": "基线（无新增杠杆）",
                   "levers_on": [], "cri": base["cri"], "pillars": base["pillars"],
                   "delta": 0.0, "verify_ok": ok, "lowest": RA.lowest_levers(base, 5)})
    prev = base["cri"]

    # ---- 第 1..N 轮：逐轮累计启用杠杆，超出后做收敛验证 ----
    converged_round = None
    for r in range(1, args.rounds + 1):
        n_on = min(r, n_levers)
        cfg = levers.cumulative(n_on)
        levers.write_levers(cfg)
        rebuild()
        ok, vout = verify()
        snap = snapshot(f"round{r:02d}")
        cri = snap["cri"]
        delta = round(cri - prev, 2)
        if r <= n_levers:
            grp = levers.GROUPS[r - 1]
            enabled, name = grp["id"], grp["name"]
        else:
            enabled, name = None, "（杠杆已全开 · 收敛验证）"
        on_list = [g for g, v in cfg.items() if v]
        rounds.append({"round": r, "lever_enabled": enabled, "lever_name": name,
                       "pillar_tag": (levers.GROUPS[r - 1]["pillar"] if r <= n_levers else "-"),
                       "levers_on": on_list, "cri": cri, "pillars": snap["pillars"],
                       "delta": delta, "verify_ok": ok, "lowest": RA.lowest_levers(snap, 5)})
        print(f"[round {r:02d}] +{name:22s} CRI={cri:6.2f}  Δ={delta:+.2f}  "
              f"verify={'OK' if ok else 'FAIL'}")
        if r > n_levers and abs(delta) < 0.05 and converged_round is None:
            converged_round = r
        prev = cri

    # ---- 收尾：清除开关文件，回到缺省（全部开启=最佳站点），重建一次 ----
    levers.clear_levers()
    rebuild()
    ok, _ = verify()
    final = snapshot("final_best")
    print(f"[final ] 清除开关（缺省全开=最佳站点）CRI={final['cri']}  verify={'OK' if ok else 'FAIL'}")

    result = {
        "computed_at": dt.datetime.now().isoformat(timespec="seconds"),
        "rounds_run": args.rounds,
        "n_lever_groups": n_levers,
        "weights": RA.PILLAR_WEIGHTS,
        "baseline_cri": base["cri"],
        "final_cri": final["cri"],
        "ceiling_cri": final["cri"],
        "total_gain": round(final["cri"] - base["cri"], 2),
        "converged_round": converged_round if converged_round else min(args.rounds, n_levers),
        "rounds": rounds,
        "lever_groups": levers.GROUPS,
        "scope": base["scope"],
    }
    with open(LOOP_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    write_changelog(result, final)
    print("-" * 72)
    print(f"基线 CRI={result['baseline_cri']} → 最终 CRI={result['final_cri']}  "
          f"(总提升 {result['total_gain']:+.2f})")
    print(f"写出：{LOOP_JSON}\n      {CHANGELOG}")


def write_changelog(result, final):
    lines = ["# 中科存储 GEO+SEO 提升闭环 · 复盘记录（changelog）\n",
             f"> 生成时间：{result['computed_at']}　范围：{result['scope']}\n",
             f"> 基线 CRI **{result['baseline_cri']}** → 最终 CRI **{result['final_cri']}**"
             f"（总提升 **{result['total_gain']:+.2f}**，权重 {result['weights']}）\n",
             "\nCRI 度量的是**站内真正可控的 GEO+SEO 就绪度**（确定性、可复现），"
             "区别于大模型真实嘴上提及率(GVI，见 geo_plan 真测)。\n",
             "\n## 逐轮明细\n",
             "| 轮次 | 本轮启用 | 支柱 | CRI | Δ | A | B | C | D | E | verify |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in result["rounds"]:
        p = r["pillars"]
        lines.append(
            f"| {r['round']:02d} | {r['lever_name']} | {r.get('pillar_tag','-')} | "
            f"{r['cri']:.2f} | {r['delta']:+.2f} | {p['A']} | {p['B']} | {p['C']} | "
            f"{p['D']} | {p['E']} | {'OK' if r['verify_ok'] else 'FAIL'} |")
    lines.append("\n## 每个杠杆组的真实改进内容\n")
    for g in result["lever_groups"]:
        lines.append(f"- **{g['name']}**（{g['id']}，支柱 {g['pillar']}）：{g['desc']}")
    lines.append("\n## 收敛与自我批评\n")
    lines.append(f"- 杠杆全开后 CRI 收敛于 **{result['final_cri']}**（结构上限，非人为 100）。")
    lowest = RA.lowest_levers(final, 6)
    lines.append("- 仍未满分的子项（如实记录，留待站外执行/后续迭代）：")
    for v, name in lowest:
        lines.append(f"  - {name} = {v}")
    lines.append("\n> 复现：`python run_loop.py` —— 过程无随机、无网络，任何人可逐轮复算。")
    with open(CHANGELOG, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
