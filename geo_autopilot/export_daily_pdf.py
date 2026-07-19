# -*- coding: utf-8 -*-
"""铭信 GEO Autopilot · 日报 HTML→A4 PDF（苹果视觉页眉页脚）。

复现：python build_daily_report.py → python export_daily_pdf.py
"""
from __future__ import annotations

import datetime as dt
import json
import os

from playwright.sync_api import sync_playwright

import paths

HTML = os.path.join(paths.REPORTS, "铭信-GEO自动驾驶日报.html")
META = os.path.join(paths.REPORTS, "daily_report_meta.json")


def export():
    try:
        with open(META, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        meta = {"header": "铭信 · GEO 自动驾驶日报", "footer": "铭信 Mingxin Technology"}
    header, footer = meta.get("header", ""), meta.get("footer", "铭信 Mingxin Technology")

    today = dt.date.today().isoformat()
    out_pdf = os.path.join(paths.REPORTS, f"铭信-GEO自动驾驶日报-{today}.pdf")

    header_tpl = (
        '<div style="width:100%;font-size:8px;color:#9A9AA0;'
        'font-family:-apple-system,\'Segoe UI\',\'Microsoft YaHei\',sans-serif;'
        'padding:0 14mm;text-align:center;border-bottom:0.4px solid #E8E8ED;">'
        f'<span>{header}</span></div>'
    )
    footer_tpl = (
        '<div style="width:100%;font-size:8px;color:#9A9AA0;'
        'font-family:-apple-system,\'Segoe UI\',\'Microsoft YaHei\',sans-serif;'
        'padding:0 14mm;display:flex;justify-content:space-between;">'
        f'<span>{footer}</span>'
        '<span>第 <span class="pageNumber"></span> 页 / 共 <span class="totalPages"></span> 页</span>'
        '</div>'
    )
    url = "file:///" + HTML.replace("\\", "/")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=120000)
        page.emulate_media(media="print")
        page.pdf(
            path=out_pdf, format="A4", print_background=True,
            display_header_footer=True,
            header_template=header_tpl, footer_template=footer_tpl,
            margin={"top": "16mm", "bottom": "15mm", "left": "12mm", "right": "12mm"},
        )
        browser.close()
    # latest 指针副本
    latest = os.path.join(paths.REPORTS, "铭信-GEO自动驾驶日报-latest.pdf")
    try:
        import shutil
        shutil.copy2(out_pdf, latest)
    except Exception:
        pass
    print(f"Saved: {out_pdf}  ({os.path.getsize(out_pdf)/1e6:.2f} MB)")
    return out_pdf


if __name__ == "__main__":
    export()
