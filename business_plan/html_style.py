# -*- coding: utf-8 -*-
"""HTML 排版工具：与 docx_style 同名 API 的"苹果视觉"HTML 发射器。

通过实现与 docx_style 完全一致的函数签名（init_document/add_h1/add_body/
add_three_line_table/add_metric_cards/add_callout/add_section_divider/add_figure ...），
使 build_docx_v3.py 的 17 章正文函数可被零改动复用，渲染为 HTML（再由 export_pdf.py
经 Playwright/Chromium 打印为世界级视觉 PDF）。

设计语言：Apple Ink (#1D1D1F) + System Blue (#0A84FF)，大留白、细三线表、
章节全幅扉页、metric cards、callout、图注——对齐 Apple Keynote/HIG 视觉。
"""
from __future__ import annotations

import base64
import html as _html
import os

# 颜色常量（与 docx_style 对应；HTML 用十六进制字符串）
COLOR_PRIMARY = "#1D1D1F"   # Apple Ink
COLOR_ACCENT = "#0A84FF"    # System Blue
COLOR_SOFT = "#6E6E73"      # Secondary label

_IMG_CACHE: dict[str, str] = {}


def _data_uri(path: str) -> str:
    """把本地图片转 data URI，保证 PDF 渲染稳定（不依赖加载路径）。"""
    if path in _IMG_CACHE:
        return _IMG_CACHE[path]
    if not path or not os.path.exists(path):
        _IMG_CACHE[path] = ""
        return ""
    ext = os.path.splitext(path)[1].lower().lstrip(".") or "png"
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    uri = f"data:{mime};base64,{b64}"
    _IMG_CACHE[path] = uri
    return uri


def _esc(text) -> str:
    return _html.escape(str(text), quote=False)


def _rich(text) -> str:
    """转义后按 **粗体强调** 标记切分（与 docx_style 一致：奇数段加粗+强调色）。"""
    safe = _esc(text)
    parts = safe.split("**")
    out = []
    for i, seg in enumerate(parts):
        if seg == "":
            continue
        if i % 2 == 1:
            out.append(f'<strong>{seg}</strong>')
        else:
            out.append(seg)
    return "".join(out)


class HtmlDoc:
    def __init__(self):
        self.parts: list[str] = []
        self.header_text = ""
        self.footer_text = ""
        self.fig_captions: list[str] = []
        self.table_captions: list[str] = []

    def add(self, fragment: str):
        self.parts.append(fragment)

    def add_paragraph(self):           # 兼容封面里的 doc.add_paragraph()
        self.parts.append('<div class="spacer"></div>')

    def body_html(self) -> str:
        return "\n".join(self.parts)


# ---------------------------------------------------------------------------
# 文档与页眉页脚
# ---------------------------------------------------------------------------
def init_document() -> HtmlDoc:
    return HtmlDoc()


def add_header_text(doc, text):
    doc.header_text = _esc(text)


def add_footer_pagenumber(doc, text_left=""):
    doc.footer_text = _esc(text_left)


# ---------------------------------------------------------------------------
# 封面与标题
# ---------------------------------------------------------------------------
def add_title(doc, text, size=26):
    doc.add(f'<h1 class="doc-title">{_esc(text)}</h1>')


def add_subtitle(doc, text, size=14, color=None):
    cls = "doc-subtitle"
    style = ""
    if color == COLOR_PRIMARY:
        cls = "doc-subtitle ink"
    elif color == COLOR_SOFT:
        cls = "doc-subtitle soft"
    style = f' style="font-size:{size}px"' if size else ""
    doc.add(f'<p class="{cls}"{style}>{_esc(text)}</p>')


def add_h1(doc, num, text):
    label = f"{num}　{text}" if num else text
    doc.add(f'<h2 class="sec-h1">{_esc(label)}</h2>')


def add_h2(doc, num, text):
    num_html = f'<span class="h2-num">{_esc(num)}</span>' if num else ""
    doc.add(f'<h3 class="h2">{num_html}{_esc(text)}</h3>')


def add_h3(doc, text):
    doc.add(f'<h4 class="h3">{_esc(text)}</h4>')


def add_body(doc, text, indent=True, size=12, align="justify"):
    cls = ["body"]
    if not indent:
        cls.append("noindent")
    if align == "center":
        cls.append("center")
    elif align == "left":
        cls.append("left")
    style = f' style="font-size:{size}px"' if size and size != 12 else ""
    doc.add(f'<p class="{" ".join(cls)}"{style}>{_rich(text)}</p>')


def add_bullet(doc, text, size=12, level=0):
    style = f' style="margin-left:{level * 18}px"' if level else ""
    doc.add(f'<p class="bullet"{style}><span class="dot">•</span>'
            f'<span class="bt">{_rich(text)}</span></p>')


# ---------------------------------------------------------------------------
# 三线表
# ---------------------------------------------------------------------------
def add_three_line_table(doc, headers, rows, caption=None, col_align=None, font_size=10.5,
                         highlight_last=False):
    out = ['<div class="tl-wrap">']
    if caption:
        doc.table_captions.append(str(caption))
        out.append(f'<div class="tl-cap">{_esc(caption)}</div>')
    style = f' style="font-size:{font_size}px"' if font_size else ""
    out.append(f'<table class="tl"{style}>')
    out.append("<thead><tr>")
    for i, h in enumerate(headers):
        a = "center"
        if col_align and i < len(col_align):
            a = "left" if col_align[i] == "l" else "center"
        out.append(f'<th class="{a}">{_esc(h)}</th>')
    out.append("</tr></thead><tbody>")
    n = len(rows)
    for ridx, row in enumerate(rows):
        is_last = highlight_last and ridx == n - 1
        tr_cls = ' class="hl"' if is_last else ""
        out.append(f"<tr{tr_cls}>")
        for i, val in enumerate(row):
            a = "center"
            if col_align and i < len(col_align):
                a = "left" if col_align[i] == "l" else "center"
            out.append(f'<td class="{a}">{_rich(val)}</td>')
        out.append("</tr>")
    out.append("</tbody></table></div>")
    doc.add("".join(out))


# ---------------------------------------------------------------------------
# 图片 / 大图 / 章节扉页
# ---------------------------------------------------------------------------
def add_figure(doc, path, caption=None, width_cm=15.5):
    uri = _data_uri(path)
    if caption:
        doc.fig_captions.append(str(caption))
    cap = f'<figcaption>{_esc(caption)}</figcaption>' if caption else ""
    doc.add(f'<figure class="fig"><img src="{uri}" alt="figure"/>{cap}</figure>')


def add_hero_image(doc, path, width_cm=15.5):
    uri = _data_uri(path)
    doc.add(f'<figure class="hero"><img src="{uri}" alt="hero"/></figure>')


def add_section_divider(doc, num, title_cn, title_en, hero_path, subtitle=""):
    uri = _data_uri(hero_path)
    img = f'<img src="{uri}" alt="hero"/>' if uri else ""
    en = f'<div class="dv-en">{_esc(title_en)}</div>' if title_en else ""
    sub = f'<div class="dv-sub">{_esc(subtitle)}</div>' if subtitle else ""
    doc.add(
        f'<section class="divider" id="ch{_esc(num)}">'
        f'<figure class="dv-hero">{img}</figure>'
        f'<div class="dv-num">第 {_esc(num)} 章</div>'
        f'<div class="dv-cn">{_esc(title_cn)}</div>{en}{sub}'
        f'</section>'
    )


def add_metric_cards(doc, cards, per_row=4):
    out = [f'<div class="cards" style="grid-template-columns:repeat({per_row},1fr)">']
    for card in cards:
        val = card[0]
        label = card[1]
        sub = card[2] if len(card) > 2 else None
        sub_html = f'<div class="card-s">{_esc(sub)}</div>' if sub else ""
        out.append(
            f'<div class="card"><div class="card-v">{_esc(val)}</div>'
            f'<div class="card-l">{_esc(label)}</div>{sub_html}</div>'
        )
    out.append("</div>")
    doc.add("".join(out))


def add_callout(doc, title, text, kind="info"):
    title_html = f'<div class="co-title">{_esc(title)}</div>' if title else ""
    doc.add(
        f'<div class="callout {kind}">{title_html}'
        f'<div class="co-body">{_rich(text)}</div></div>'
    )


def add_formula(doc, latex, name, number=None, width_cm=None):
    """把 LaTeX 公式经 matplotlib mathtext 渲染为 PNG（复用 docx_style 渲染器），居中嵌入。"""
    import docx_style as _D
    path = _D.render_formula(latex, name)
    uri = _data_uri(path)
    num = f'<span class="eq-num">({_esc(number)})</span>' if number else ""
    doc.add(f'<div class="formula"><img src="{uri}" alt="formula"/>{num}</div>')


def add_toc(doc):
    """目录容器（随后由 add_bullet 注入条目）——此处不输出占位文字。"""
    return None


def add_pagebreak(doc):
    doc.add('<div class="pagebreak"></div>')


# ---------------------------------------------------------------------------
# 数值格式化（与 docx_style 一致）
# ---------------------------------------------------------------------------
def yi(x):
    return f"{x/1e8:,.2f} 亿元"


def wan(x):
    return f"{x/1e4:,.0f} 万元"


def pct(x, d=1):
    return f"{x*100:.{d}f}%"
