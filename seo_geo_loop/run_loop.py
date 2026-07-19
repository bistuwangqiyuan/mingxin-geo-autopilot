# -*- coding: utf-8 -*-
"""铭信 GEO+SEO 闭环驱动器（诚实退役说明 + 历史产物兼容）。

历史背景：旧架构对本地静态站做「写杠杆开关 → 重建站点 → 站内自检 → 确定性审计 CRI →
记录逐轮 delta」的闭环优化（最多 10+5 轮）。逐轮快照与结果保留在
outputs/loop_results.json、outputs/loop_results_v2.json 与 outputs/snapshots/，
作为历史产物继续供 charts.py / build_report_html.py 读取。

现状（诚实说明，本脚本不报错、不假装重建）：
  - 铭信官网为 Next.js 站点（amd 仓库 site/ 子目录，Vercel 部署），本地没有
    build_site.py/verify_site.py 静态构建链路可驱动；站内结构化数据、答案块、
    llms.txt 等由站点自身内容引擎负责。
  - 因此「重建站点」步骤在本仓库**如实跳过**；如需度量当前线上就绪度，请运行
    `python readiness_audit.py --label <tag>`（对 https://mingxinstorage.xyz 做
    线上 HTTP 抓取审计，网络失败时如实记录 error）。

复现：python run_loop.py            # 打印说明并退出 0（不再驱动静态重建）
"""
from __future__ import annotations

import argparse

import levers


def main():
    ap = argparse.ArgumentParser()
    # 历史参数全部保留以兼容既有编排（run.py / 文档中的命令行）；均不再触发重建。
    ap.add_argument("--rounds", type=int, default=10, help="（历史参数，保留兼容）")
    ap.add_argument("--v2", action="store_true", help="（历史参数，保留兼容）")
    ap.add_argument("--from-lever", type=int, default=1, help="（历史参数，保留兼容）")
    ap.add_argument("--to-lever", type=int, default=0, help="（历史参数，保留兼容）")
    ap.add_argument("--round-offset", type=int, default=0, help="（历史参数，保留兼容）")
    ap.add_argument("--suffix", default="", help="（历史参数，保留兼容）")
    ap.parse_args()

    print("=" * 72)
    print("铭信 GEO+SEO 闭环 · 站内重建步骤已退役（如实跳过）")
    print("=" * 72)
    print("铭信官网为 Next.js 站点（amd 仓库 site/ 子目录，Vercel 部署）：")
    print("  - 站内结构化数据/答案块/llms.txt 由站点自身内容引擎负责，本仓库不再驱动静态重建；")
    print("  - 历史闭环产物（outputs/loop_results*.json、snapshots/）保留为可追溯记录；")
    print("  - 站内 GEO 检查清单见 levers.GROUPS（共 %d 组，铭信口径）；" % len(levers.GROUPS))
    print("  - 度量当前线上就绪度：python readiness_audit.py --label current")
    print("    （对 https://mingxinstorage.xyz 线上抓取审计；网络失败如实记录，不编造分数）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
