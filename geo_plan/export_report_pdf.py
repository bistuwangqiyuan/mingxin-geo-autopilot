# -*- coding: utf-8 -*-
"""把 outputs/铭信-GEO提升计划.html 经 Playwright(Chromium) 打印为 A4 PDF。

苹果风格页眉页脚与打印设置。
输出：根目录 铭信-GEO提升计划与基线报告.pdf。

复现链：python build_report_html.py → python export_report_pdf.py
"""
from __future__ import annotations

import json
import os

from playwright.sync_api import sync_playwright

BASE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(BASE, "outputs", "铭信-GEO提升计划.html")
META = os.path.join(BASE, "outputs", "report_meta.json")
OUT_PDF = os.path.join(os.path.dirname(BASE), "铭信-GEO提升计划与基线报告.pdf")


def _meta():
    try:
        with open(META, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"header": "铭信 · GEO 提升计划", "footer": "铭信 Mingxin Technology"}


def export():
    meta = _meta()
    header = meta.get("header", "")
    footer = meta.get("footer", "铭信 Mingxin Technology")

    header_tpl = (
        '<div style="width:100%;font-size:8px;color:#9A9AA0;'
        'font-family:-apple-system,\'Segoe UI\',\'Microsoft YaHei\',sans-serif;'
        'padding:0 14mm;text-align:center;border-bottom:0.4px solid #E8E8ED;">'
        f'<span>{header}</span></div>'
    )
    footer_tpl = (
        '<div style="width:100%;font-size:8px;color:#9A9AA0;'
        'font-family:-apple-system,\'Segoe UI\',\'Microsoft YaHei\',sans-serif;'
        'padding:0 14mm;display:flex;justify-content:space-between;align-items:center;">'
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
            path=OUT_PDF,
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template=header_tpl,
            footer_template=footer_tpl,
            margin={"top": "16mm", "bottom": "15mm", "left": "12mm", "right": "12mm"},
            prefer_css_page_size=False,
        )
        browser.close()

    size_mb = os.path.getsize(OUT_PDF) / 1e6
    print(f"Saved: {OUT_PDF}  ({size_mb:.2f} MB)")


if __name__ == "__main__":
    export()
