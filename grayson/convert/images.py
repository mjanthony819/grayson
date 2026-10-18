"""Image conversions powered by Pillow. Fully offline, no external binaries."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

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
    img = img.resize((max(1, img.width // 2), max(1, img.height // 2)), Image.LANCZOS)
    return _save(img, dst, img.format or "PNG")


def compress(src, dst, quality: int = 60, **_):
    """Re-encode at a lower quality. JPEG/WebP get lossy quality; PNG is
    quantised to 256 colours."""
    img = _open(src)
    fmt = (img.format or "PNG").upper()
    if fmt in ("JPEG", "WEBP"):
        return _save(img, dst, fmt, quality=quality, optimize=True)
    if img.mode in ("RGBA", "LA", "P"):
        q = img.convert("RGBA").quantize(colors=256, method=Image.FASTOCTREE)
    else:
        q = img.convert("RGB").quantize(colors=256)
    return _save(q, dst, "PNG", optimize=True)


def grayscale(src, dst, **_):
    img = _open(src)
    fmt = img.format or "PNG"
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
