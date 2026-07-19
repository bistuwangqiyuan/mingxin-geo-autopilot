# -*- coding: utf-8 -*-
"""铭信 SEO/GEO 提升与站外发布 · 一键复现编排器。

依次执行（确定性部分无随机；联网部分如实标注）：
  1) run_loop.py            站内重建步骤诚实跳过说明（历史闭环产物保留，exit 0）
  2) readiness_audit.py     线上 CRI 审计（对 mingxinstorage.xyz HTTP 抓取，联网）
  3) build_offsite_site.py  生成站外知识微站（EdgeOne 部署目录）
  4) build_offsite_github.py组装 GitHub Pages 知识库（mingxin-storage-kb）
  5) live_audit.py          线上收录/排名/在线技术 SEO 真测（联网，可 --skip-net）
  6) lighthouse_psi.py      线上性能真测 PSI→实验室（联网，可 --skip-net）
  7) gvi_measure.py         真实大模型 GVI 重测（联网，可 --skip-gvi）
  8) charts.py              苹果风复现图
  9) build_report_html.py   苹果视觉 HTML 报告
 10) export_report_pdf.py   Playwright A4 PDF（根目录正式 PDF）

注：EdgeOne/GitHub 的真实发布为一次性、需凭证的副作用操作（URL 记录于
   outputs/offsite_published.json），本编排器只重建可部署目录，不自动重复发布。
   收录提交走站点自带 /api/seo/ping（Bearer CRON_SECRET，见 indexnow_submit.py）。

复现：python run.py                 # 全流程
      python run.py --skip-net      # 跳过联网真测（沿用已有 live_status/lighthouse）
      python run.py --skip-gvi      # 跳过联网 GVI
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
import os

BASE = os.path.dirname(os.path.abspath(__file__))


def step(title, cmd, cwd=BASE, allow_fail=False):
    print("\n" + "=" * 72 + f"\n▶ {title}\n" + "=" * 72)
    t0 = time.time()
    rc = subprocess.run([sys.executable, *cmd], cwd=cwd).returncode
    print(f"  ({title} 用时 {time.time()-t0:.1f}s, exit={rc})")
    if rc != 0 and not allow_fail:
        raise SystemExit(f"步骤失败：{title} (exit {rc})")
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-net", action="store_true", help="跳过联网的线上真测（收录/排名/性能/CRI）")
    ap.add_argument("--skip-gvi", action="store_true", help="跳过联网的真实 GVI 重测")
    ap.add_argument("--gvi-limit", type=int, default=0, help="每模型查询数上限（0=全部）")
    args = ap.parse_args()

    step("1/10 站内重建诚实跳过说明（run_loop.py）", ["run_loop.py"])
    if not args.skip_net:
        step("2/10 线上 CRI 审计（readiness_audit.py）",
             ["readiness_audit.py", "--label", "current_live", "--v2"], allow_fail=True)
    else:
        print("\n[skip] 跳过线上 CRI 审计（--skip-net）")
    step("3/10 站外知识微站（build_offsite_site.py）", ["build_offsite_site.py"])
    step("4/10 GitHub Pages 知识库（build_offsite_github.py）", ["build_offsite_github.py"])
    if not args.skip_net:
        step("5/10 线上收录/排名/技术 SEO 真测（live_audit.py）", ["live_audit.py"], allow_fail=True)
        step("6/10 线上性能真测（lighthouse_psi.py）", ["lighthouse_psi.py"], allow_fail=True)
    else:
        print("\n[skip] 跳过联网线上真测（--skip-net）")
    if not args.skip_gvi:
        cmd = ["gvi_measure.py"]
        if args.gvi_limit:
            cmd += ["--limit", str(args.gvi_limit)]
        step("7/10 真实 GVI 重测（gvi_measure.py）", cmd, allow_fail=True)
    else:
        print("\n[skip] 跳过真实 GVI 重测（--skip-gvi）")
    step("8/10 复现图（charts.py）", ["charts.py"])
    step("9/10 苹果风 HTML 报告（build_report_html.py）", ["build_report_html.py"])
    step("10/10 导出 A4 PDF（export_report_pdf.py）", ["export_report_pdf.py"])
    print("\n✅ 全流程完成。正式 PDF 见仓库根目录：铭信-SEO-GEO提升与站外发布报告.pdf")


if __name__ == "__main__":
    main()
