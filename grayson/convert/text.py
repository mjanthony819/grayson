"""Plain text, Markdown and HTML. PDF/HTML/text outputs are built in (PyMuPDF,
Markdown); only Word output needs LibreOffice."""
from __future__ import annotations

import html as _html
import re
import tempfile
from pathlib import Path

import pymupdf

_CSS = ("body{font-family:sans-serif;font-size:11pt;line-height:1.4}"
        "pre,code{font-family:monospace;font-size:10pt}"
        "h1{font-size:20pt}h2{font-size:16pt}h3{font-size:13pt}"
        "table{border-collapse:collapse}td,th{border:1px solid #888;padding:3px}")


def _to_html(src: Path) -> str:
    raw = src.read_text(encoding="utf-8", errors="replace")
    ext = src.suffix.lower()
    if ext in (".html", ".htm"):
        return raw
    if ext in (".md", ".markdown"):
        import markdown

        body = markdown.markdown(raw, extensions=["extra", "sane_lists"])
    else:
        body = "<pre>" + _html.escape(raw) + "</pre>"
    return f"<html><head><meta charset='utf-8'></head><body>{body}</body></html>"


def to_html(src, dst, **_):
    Path(dst).write_text(_to_html(Path(src)), encoding="utf-8")
    return Path(dst)


def to_txt(src, dst, **_):
    src = Path(src)
    if src.suffix.lower() in (".html", ".htm"):
        raw = _to_html(src)
        raw = re.sub(r"(?is)<(script|style).*?</\1>", "", raw)
        raw = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</h\d>|</li>", "\n", raw)
        text = _html.unescape(re.sub(r"<[^>]+>", "", raw))
    else:
        text = src.read_text(encoding="utf-8", errors="replace")
    Path(dst).write_text(text, encoding="utf-8")
    return Path(dst)


def to_pdf(src, dst, **_):
    story = pymupdf.Story(html=_to_html(Path(src)), user_css=_CSS)
    writer = pymupdf.DocumentWriter(str(dst))
    page = pymupdf.paper_rect("a4")
    area = page + (50, 50, -50, -50)
    more = 1
    while more:
        dev = writer.begin_page(page)
        more, _ = story.place(area)
        story.draw(dev)
        writer.end_page()
    writer.close()
    return Path(dst)


def to_docx(src, dst, **_):
    from . import docs

    with tempfile.TemporaryDirectory(prefix="grayson-txt-") as tmp:
        tmp_html = Path(tmp) / (Path(src).stem + ".html")
        to_html(src, tmp_html)
        return docs._lo_convert_html(tmp_html, Path(dst))
