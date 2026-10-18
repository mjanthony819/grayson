"""Image conversions powered by Pillow. Fully offline, no external binaries."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

try:  # HEIC/HEIF read + write; optional so the engine still runs without it
    import pillow_heif

    pillow_heif.register_heif_opener()
except Exception:  # pragma: no cover
    pillow_heif = None

# Formats Pillow cannot save an alpha channel to directly.
_NO_ALPHA = {"JPEG"}


def _open(src: str | Path) -> Image.Image:
    img = Image.open(src)
    img.load()
    return img


def _flatten(img: Image.Image, fmt: str) -> Image.Image:
    """Drop alpha onto white when the target format has no alpha channel."""
    if fmt in _NO_ALPHA and img.mode in ("RGBA", "LA", "P"):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    if fmt in _NO_ALPHA and img.mode != "RGB":
        return img.convert("RGB")
    return img


_FMT_BY_EXT = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP",
               ".bmp": "BMP", ".tif": "TIFF", ".tiff": "TIFF", ".gif": "GIF",
               ".ico": "ICO", ".avif": "AVIF", ".heic": "HEIF", ".heif": "HEIF"}


def _fmt_of(img: Image.Image, dst) -> str:
    """Pick the save format: the image's own, else from the output extension."""
    return (img.format or _FMT_BY_EXT.get(Path(dst).suffix.lower(), "PNG")).upper()


def _save(img: Image.Image, dst: str | Path, fmt: str, **kw) -> Path:
    dst = Path(dst)
    _flatten(img, fmt).save(dst, format=fmt, **kw)
    return dst


def to_png(src, dst, **_):
    return _save(_open(src), dst, "PNG", optimize=True)


def to_jpg(src, dst, **_):
    return _save(_open(src), dst, "JPEG", quality=92)


def to_webp(src, dst, **_):
    return _save(_open(src), dst, "WEBP", quality=90)


def resize_half(src, dst, **_):
    img = _open(src)
    fmt = _fmt_of(img, dst)
    img = img.resize((max(1, img.width // 2), max(1, img.height // 2)), Image.LANCZOS)
    return _save(img, dst, fmt)


def compress(src, dst, quality: int = 60, **_):
    """Re-encode at a lower quality. JPEG/WebP get lossy quality; PNG is
    quantised to 256 colours."""
    img = _open(src)
    fmt = _fmt_of(img, dst)
    if fmt in ("JPEG", "WEBP", "AVIF", "HEIF"):
        kw = {"optimize": True} if fmt in ("JPEG", "WEBP") else {}
        return _save(img, dst, fmt, quality=quality, **kw)
    if fmt != "PNG":  # BMP/GIF/TIFF/ICO: nothing lossy to tune, re-save as is
        return _save(img, dst, fmt)
    if img.mode in ("RGBA", "LA", "P"):
        q = img.convert("RGBA").quantize(colors=256, method=Image.FASTOCTREE)
    else:
        q = img.convert("RGB").quantize(colors=256)
    return _save(q, dst, "PNG", optimize=True)


def grayscale(src, dst, **_):
    img = _open(src)
    fmt = _fmt_of(img, dst)
    grey = img.convert("LA" if "A" in img.getbands() else "L")
    return _save(grey, dst, fmt)


def to_pdf(srcs, dst, **_):
    """One or more images -> a single PDF, one image per page."""
    if isinstance(srcs, (str, Path)):
        srcs = [srcs]
    pages = [_flatten(_open(s), "JPEG") for s in srcs]
    if not pages:
        raise ValueError("no images given")
    first, rest = pages[0], pages[1:]
    first.save(dst, format="PDF", save_all=True, append_images=rest)
    return Path(dst)


# -- more output formats ------------------------------------------------------


def to_bmp(src, dst, **_):
    return _save(_open(src), dst, "BMP")


def to_tiff(src, dst, **_):
    return _save(_open(src), dst, "TIFF", compression="tiff_lzw")


def to_gif(src, dst, **_):
    return _save(_open(src).convert("RGBA" if "A" in _open(src).getbands() else "RGB"),
                 dst, "GIF")


def to_avif(src, dst, **_):
    return _save(_open(src), dst, "AVIF", quality=80)


def to_heic(src, dst, **_):
    if pillow_heif is None:
        raise RuntimeError("HEIC output needs the pillow-heif package.")
    return _save(_open(src), dst, "HEIF", quality=85)


def to_ico(src, dst, **_):
    """Windows icon: image centred on a transparent square, up to 256 px, with
    the usual embedded sizes."""
    img = _open(src).convert("RGBA")
    side = min(256, max(img.size))
    img.thumbnail((side, side), Image.LANCZOS)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    sizes = [(s, s) for s in (16, 32, 48, 64, 128, 256) if s <= side] or [(side, side)]
    canvas.save(dst, format="ICO", sizes=sizes)
    return Path(dst)


# -- geometry: rotate and crop ----------------------------------------------


def rotate_90(src, dst, **_):
    img = _open(src)
    fmt = _fmt_of(img, dst)
    return _save(img.rotate(-90, expand=True), dst, fmt)


def _center_crop(img: Image.Image, ratio: float) -> Image.Image:
    """Largest centred box of width/height == ratio."""
    w, h = img.size
    if w / h > ratio:
        nw, nh = int(round(h * ratio)), h
    else:
        nw, nh = w, int(round(w / ratio))
    left, top = (w - nw) // 2, (h - nh) // 2
    return img.crop((left, top, left + nw, top + nh))


def crop_square(src, dst, **_):
    img = _open(src)
    return _save(_center_crop(img, 1.0), dst, _fmt_of(img, dst))


def crop_16x9(src, dst, **_):
    img = _open(src)
    return _save(_center_crop(img, 16 / 9), dst, _fmt_of(img, dst))


def crop(src, dst, left: float = 0, top: float = 0, right: float = 0,
         bottom: float = 0, **_):
    """Remove a percentage from each edge (0-49 per axis pair)."""
    left, top, right, bottom = (float(v) for v in (left, top, right, bottom))
    if min(left, top, right, bottom) < 0 or left + right >= 100 or top + bottom >= 100:
        raise ValueError("crop percentages must be >= 0 and leave some image")
    img = _open(src)
    w, h = img.size
    box = (int(w * left / 100), int(h * top / 100),
           w - int(w * right / 100), h - int(h * bottom / 100))
    return _save(img.crop(box), dst, _fmt_of(img, dst))


def to_docx(srcs, dst, **_):
    """One or more images -> a Word document, one image per page, scaled to fit."""
    import io

    from docx import Document
    from docx.shared import Inches

    if isinstance(srcs, (str, Path)):
        srcs = [srcs]
    doc = Document()
    sec = doc.sections[0]
    max_w = sec.page_width - sec.left_margin - sec.right_margin
    max_h = sec.page_height - sec.top_margin - sec.bottom_margin
    for n, s in enumerate(srcs):
        if n:
            doc.add_page_break()
        img = _flatten(_open(s), "JPEG") if _open(s).mode not in ("RGB", "L") else _open(s)
        buf = io.BytesIO()
        img.save(buf, "PNG")
        buf.seek(0)
        ratio = img.width / img.height
        width = min(max_w, int(max_h * ratio))
        doc.add_picture(buf, width=width)
    doc.save(dst)
    return Path(dst)
