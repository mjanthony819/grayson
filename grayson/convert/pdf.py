"""PDF tools powered by PyMuPDF (fitz): merge, split, compress, rasterise."""
from __future__ import annotations

from pathlib import Path

import pymupdf


def merge(srcs, dst, **_):
    if isinstance(srcs, (str, Path)):
        srcs = [srcs]
    if len(srcs) < 2:
        raise ValueError("merge needs at least two PDFs")
    out = pymupdf.open()
    for s in srcs:
        with pymupdf.open(s) as doc:
            out.insert_pdf(doc)
    out.save(dst, garbage=3, deflate=True)
    out.close()
    return Path(dst)


def split_pages(src, dst_dir, **_):
    """Split into one PDF per page inside a folder next to the source."""
    src = Path(src)
    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    written = []
    with pymupdf.open(src) as doc:
        for i, page in enumerate(doc, start=1):
            one = pymupdf.open()
            one.insert_pdf(doc, from_page=i - 1, to_page=i - 1)
            out = dst_dir / f"{src.stem}-page-{i}.pdf"
            one.save(out)
            one.close()
            written.append(out)
    return written


def compress(src, dst, max_dim: int = 1500, quality: int = 70, **_):
    """Shrink a PDF: downsample embedded images above *max_dim* pixels to
    JPEG and rewrite the file with dead objects dropped and streams deflated.
    Images that cannot be re-encoded are left untouched."""
    import io

    from PIL import Image

    src, dst = Path(src), Path(dst)
    with pymupdf.open(src) as doc:
        seen = set()
        for page in doc:
            for img in page.get_images(full=True):
                xref = img[0]
                if xref in seen:
                    continue
                seen.add(xref)
                try:
                    pix = pymupdf.Pixmap(doc, xref)
                    if pix.colorspace and pix.colorspace.n > 3:
                        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                    if pix.alpha:
                        pix = pymupdf.Pixmap(pix, 0)
                    if max(pix.width, pix.height) <= max_dim:
                        continue
                    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    scale = max_dim / max(im.size)
                    im = im.resize(
                        (max(1, int(im.width * scale)), max(1, int(im.height * scale))),
                        Image.LANCZOS,
                    )
                    buf = io.BytesIO()
                    im.save(buf, "JPEG", quality=quality)
                    page.replace_image(xref, stream=buf.getvalue())
                except Exception:
                    continue
        doc.save(dst, garbage=4, deflate=True, clean=True)
    return dst


def pages_to_png(src, dst_dir, dpi: int = 150, **_):
    """Render every page to a PNG inside a folder next to the source."""
    return _render(src, dst_dir, dpi, "png")


def pages_to_jpg(src, dst_dir, dpi: int = 150, **_):
    """Render every page to a JPG inside a folder next to the source."""
    return _render(src, dst_dir, dpi, "jpg")


def _render(src, dst_dir, dpi, ext):
    src = Path(src)
    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    written = []
    zoom = dpi / 72.0
    matrix = pymupdf.Matrix(zoom, zoom)
    with pymupdf.open(src) as doc:
        for i, page in enumerate(doc, start=1):
            out = dst_dir / f"{src.stem}-page-{i}.{ext}"
            page.get_pixmap(matrix=matrix).save(out)
            written.append(out)
    return written


def to_txt(src, dst, **_):
    """Extract the text layer of every page (no OCR: scanned PDFs give nothing)."""
    with pymupdf.open(src) as doc:
        text = "\n\n".join(page.get_text() for page in doc)
    Path(dst).write_text(text, encoding="utf-8")
    return Path(dst)


def to_docx(src, dst, **_):
    """PDF -> Word, text only: one paragraph per text block, a page break
    between pages. Layout, tables and images are NOT reproduced."""
    from docx import Document

    out = Document()
    with pymupdf.open(src) as doc:
        for n, page in enumerate(doc):
            if n:
                out.add_page_break()
            for block in page.get_text("blocks"):
                if block[6] == 0 and block[4].strip():  # type 0 = text block
                    out.add_paragraph(" ".join(block[4].split()))
    out.save(dst)
    return Path(dst)
