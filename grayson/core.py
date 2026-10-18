"""Core of Grayson: file-kind detection, the action registry and ring geometry.

Everything in this module is pure Python with no GUI imports, so it is fully
unit-testable on any platform.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# File kinds
# ---------------------------------------------------------------------------

EXTS_BY_KIND: dict[str, set[str]] = {
    "image": {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".gif",
              ".heic", ".heif", ".avif", ".ico"},
    "video": {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v", ".wmv", ".flv",
              ".mpg", ".mpeg", ".3gp"},
    "audio": {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac", ".opus", ".wma",
              ".aiff", ".aif"},
    "pdf": {".pdf"},
    "word": {".docx", ".doc", ".odt", ".rtf"},
    "slides": {".pptx", ".ppt", ".odp"},
    "sheet": {".xlsx", ".xls", ".ods", ".csv"},
    "text": {".txt", ".md", ".markdown", ".html", ".htm"},
}
IMAGE_EXTS = EXTS_BY_KIND["image"]
VIDEO_EXTS = EXTS_BY_KIND["video"]
AUDIO_EXTS = EXTS_BY_KIND["audio"]
PDF_EXTS = EXTS_BY_KIND["pdf"]

KIND_BY_EXT: dict[str, str] = {
    e: kind for kind, exts in EXTS_BY_KIND.items() for e in exts
}


def kind_of(path: str | Path) -> Optional[str]:
    """Return the kind ('image', 'video', 'audio', 'pdf', 'word', 'slides',
    'sheet', 'text') for a file path, or None if Grayson does not know it."""
    return KIND_BY_EXT.get(Path(path).suffix.lower())


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Action:
    """One thing Grayson can do to a set of files.

    kinds:    which file kinds this action accepts.
    multi:    True if the action can take more than one input file.
    needs:    external program the action shells out to ('ffmpeg', 'office').
    params:   names of extra parameters the GUI/CLI will ask for.
    handler:  dotted name of the function in grayson.convert.* that runs it.
    ext:      output extension (None keeps the source extension).
    dir_out:  True if the output is a folder of files (split, pages -> PNG).
    """

    id: str
    label: str
    kinds: frozenset[str]
    handler: str
    multi: bool = False
    needs: Optional[str] = None
    params: tuple[str, ...] = ()
    ext: Optional[str] = None
    dir_out: bool = False


def _a(id, label, kind, handler, ext=None, **kw) -> Action:
    return Action(id, label, frozenset({kind}), handler, ext=ext, **kw)


FF = "ffmpeg"
OF = "office"

ACTIONS: list[Action] = [
    # images ----------------------------------------------------------------
    _a("img-to-png", "To PNG", "image", "images.to_png", "png"),
    _a("img-to-jpg", "To JPG", "image", "images.to_jpg", "jpg"),
    _a("img-to-webp", "To WebP", "image", "images.to_webp", "webp"),
    _a("img-resize-50", "Resize 50%", "image", "images.resize_half"),
    _a("img-compress", "Compress", "image", "images.compress"),
    _a("imgs-to-pdf", "Images to PDF", "image", "images.to_pdf", "pdf", multi=True),
    _a("img-to-avif", "To AVIF", "image", "images.to_avif", "avif"),
    _a("img-to-heic", "To HEIC", "image", "images.to_heic", "heic"),
    _a("img-to-bmp", "To BMP", "image", "images.to_bmp", "bmp"),
    _a("img-to-tiff", "To TIFF", "image", "images.to_tiff", "tiff"),
    _a("img-to-gif", "To GIF", "image", "images.to_gif", "gif"),
    _a("img-to-ico", "To ICO (icon)", "image", "images.to_ico", "ico"),
    _a("img-grayscale", "Grayscale", "image", "images.grayscale"),
    _a("img-rotate", "Rotate 90\u00b0", "image", "images.rotate_90"),
    _a("img-crop-square", "Crop square", "image", "images.crop_square"),
    _a("img-crop-16x9", "Crop 16:9", "image", "images.crop_16x9"),
    _a("img-crop", "Crop (custom %)", "image", "images.crop", params=("crop",)),
    _a("imgs-to-docx", "Images to Word", "image", "images.to_docx", "docx", multi=True),
    # video -----------------------------------------------------------------
    _a("vid-to-mp4", "To MP4", "video", "av.video_to_mp4", "mp4", needs=FF),
    _a("vid-to-webm", "To WebM", "video", "av.video_to_webm", "webm", needs=FF),
    _a("vid-to-gif", "To GIF", "video", "av.video_to_gif", "gif", needs=FF),
    _a("vid-compress", "Compress video", "video", "av.compress_video", "mp4", needs=FF),
    _a("vid-extract-audio", "Extract MP3", "video", "av.extract_audio", "mp3", needs=FF),
    _a("vid-trim", "Trim clip", "video", "av.trim", needs=FF, params=("start", "end")),
    _a("vids-merge", "Merge videos", "video", "av.merge", "mp4", multi=True, needs=FF),
    _a("vid-to-mkv", "To MKV", "video", "av.video_to_mkv", "mkv", needs=FF),
    _a("vid-to-mov", "To MOV", "video", "av.video_to_mov", "mov", needs=FF),
    _a("vid-to-avi", "To AVI", "video", "av.video_to_avi", "avi", needs=FF),
    _a("vid-720p", "Scale to 720p", "video", "av.scale_720p", "mp4", needs=FF),
    _a("vid-mute", "Remove audio", "video", "av.mute", "mp4", needs=FF),
    _a("vid-extract-wav", "Extract WAV", "video", "av.extract_wav", "wav", needs=FF),
    # audio -----------------------------------------------------------------
    _a("aud-to-mp3", "To MP3", "audio", "av.audio_to_mp3", "mp3", needs=FF),
    _a("aud-to-wav", "To WAV", "audio", "av.audio_to_wav", "wav", needs=FF),
    _a("aud-to-ogg", "To OGG", "audio", "av.audio_to_ogg", "ogg", needs=FF),
    _a("aud-to-flac", "To FLAC", "audio", "av.audio_to_flac", "flac", needs=FF),
    _a("aud-to-m4a", "To M4A", "audio", "av.audio_to_m4a", "m4a", needs=FF),
    _a("aud-to-aac", "To AAC", "audio", "av.audio_to_aac", "aac", needs=FF),
    _a("aud-to-opus", "To Opus", "audio", "av.audio_to_opus", "opus", needs=FF),
    _a("aud-trim", "Trim audio", "audio", "av.trim", needs=FF, params=("start", "end")),
    _a("auds-merge", "Merge audio", "audio", "av.merge_audio", multi=True, needs=FF),
    _a("aud-compress", "Compress audio", "audio", "av.compress_audio", "mp3", needs=FF),
    # pdf -------------------------------------------------------------------
    _a("pdf-merge", "Merge PDFs", "pdf", "pdf.merge", "pdf", multi=True),
    _a("pdf-split", "Split pages", "pdf", "pdf.split_pages", dir_out=True),
    _a("pdf-compress", "Compress PDF", "pdf", "pdf.compress", "pdf"),
    _a("pdf-to-png", "Pages to PNG", "pdf", "pdf.pages_to_png", dir_out=True),
    _a("pdf-to-jpg", "Pages to JPG", "pdf", "pdf.pages_to_jpg", dir_out=True),
    _a("pdf-to-txt", "Extract text", "pdf", "pdf.to_txt", "txt"),
    _a("pdf-to-docx", "To Word (text)", "pdf", "pdf.to_docx", "docx"),
    # word processor documents (docx, doc, odt, rtf) ----------------------
    _a("word-to-pdf", "To PDF", "word", "docs.to_pdf", "pdf", needs=OF),
    _a("word-to-docx", "To Word (.docx)", "word", "docs.to_docx", "docx", needs=OF),
    _a("word-to-odt", "To ODT", "word", "docs.to_odt", "odt", needs=OF),
    _a("word-to-rtf", "To RTF", "word", "docs.to_rtf", "rtf", needs=OF),
    _a("word-to-txt", "To text", "word", "docs.to_txt", "txt", needs=OF),
    _a("word-to-html", "To HTML", "word", "docs.to_html", "html", needs=OF),
    _a("word-to-png", "Pages to PNG", "word", "docs.pages_to_png", needs=OF, dir_out=True),
    # presentations (pptx, ppt, odp) ----------------------------------------
    _a("slides-to-pdf", "To PDF", "slides", "docs.to_pdf", "pdf", needs=OF),
    _a("slides-to-pptx", "To PowerPoint", "slides", "docs.to_pptx", "pptx", needs=OF),
    _a("slides-to-odp", "To ODP", "slides", "docs.to_odp", "odp", needs=OF),
    _a("slides-to-png", "Slides to PNG", "slides", "docs.pages_to_png", needs=OF, dir_out=True),
    # spreadsheets (xlsx, xls, ods, csv) ------------------------------------
    _a("sheet-to-pdf", "To PDF", "sheet", "docs.to_pdf", "pdf", needs=OF),
    _a("sheet-to-xlsx", "To Excel (.xlsx)", "sheet", "docs.to_xlsx", "xlsx", needs=OF),
    _a("sheet-to-ods", "To ODS", "sheet", "docs.to_ods", "ods", needs=OF),
    _a("sheet-to-csv", "To CSV", "sheet", "docs.to_csv", "csv", needs=OF),
    _a("sheet-to-html", "To HTML", "sheet", "docs.to_html", "html", needs=OF),
    # plain text, markdown, html (no Office needed for PDF/HTML/text) -------
    _a("text-to-pdf", "To PDF", "text", "text.to_pdf", "pdf"),
    _a("text-to-html", "To HTML", "text", "text.to_html", "html"),
    _a("text-to-txt", "To plain text", "text", "text.to_txt", "txt"),
    _a("text-to-docx", "To Word (.docx)", "text", "text.to_docx", "docx", needs=OF),
]

ACTION_BY_ID: dict[str, Action] = {a.id: a for a in ACTIONS}
assert len(ACTION_BY_ID) == len(ACTIONS), "duplicate action id"

# Multi-file actions that make no sense for one file (a single image -> PDF
# or Word is still useful, so those two are not listed).
_NEEDS_SEVERAL = {"pdf-merge", "vids-merge", "auds-merge"}


def actions_for(paths: list[str | Path]) -> list[Action]:
    """Actions applicable to the given selection of files.

    Rules:
      * every selected file must be a known kind;
      * if kinds are mixed, nothing is offered (keeps the ring honest);
      * single-file selection hides merge actions.
    """
    if not paths:
        return []
    kinds = {kind_of(p) for p in paths}
    if None in kinds or len(kinds) != 1:
        return []
    kind = kinds.pop()
    out = []
    for a in ACTIONS:
        if kind not in a.kinds:
            continue
        if a.id in _NEEDS_SEVERAL and len(paths) == 1:
            continue
        out.append(a)
    return out


def resolve_handler(dotted: str) -> Callable:
    """Resolve 'images.to_png' -> grayson.convert.images.to_png."""
    mod_name, func_name = dotted.split(".")
    module = __import__(f"grayson.convert.{mod_name}", fromlist=[func_name])
    return getattr(module, func_name)


# ---------------------------------------------------------------------------
# Output naming
# ---------------------------------------------------------------------------


def unique_output(src: str | Path, new_ext: Optional[str] = None, suffix: str = "-grayson") -> Path:
    """Output path next to *src*: name-grayson.ext, never overwriting.

    >>> # photo.png -> photo-grayson.png (or photo-grayson-2.png if taken)
    """
    src = Path(src)
    ext = ("." + new_ext.lstrip(".")) if new_ext else src.suffix
    candidate = src.with_name(f"{src.stem}{suffix}{ext}")
    n = 2
    while candidate.exists():
        candidate = src.with_name(f"{src.stem}{suffix}-{n}{ext}")
        n += 1
    return candidate


# ---------------------------------------------------------------------------
# Ring geometry (pure math - unit tested, reused by the Qt widget)
# ---------------------------------------------------------------------------


def slice_index(dx: float, dy: float, count: int, dead_radius: float = 0.22) -> Optional[int]:
    """Which slice of an n-slice ring is the point (dx, dy) in?

    (dx, dy) are relative to the ring centre and normalised so the ring
    radius is 1.0. Slice 0 starts at 12 o'clock and counts clockwise
    (screen coordinates: +y is DOWN). Returns None inside the dead zone
    (the dismiss button in the middle) or outside the ring.
    """
    if count <= 0:
        return None
    r = math.hypot(dx, dy)
    if r < dead_radius or r > 1.0:
        return None
    # atan2 with y down: 0 rad = east; we want 0 = north, clockwise positive.
    angle = math.atan2(dy, dx)  # -pi..pi, y down
    angle = (angle - (-math.pi / 2)) % (2 * math.pi)  # rotate so 0 = north
    width = 2 * math.pi / count
    return int(angle // width) % count


def slice_mid_angle(i: int, count: int) -> float:
    """Mid-angle (radians, 0 = north, clockwise, y down) of slice i."""
    width = 2 * math.pi / count
    return i * width + width / 2
