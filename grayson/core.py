"""Core of Grayson: file-kind detection, the action registry and ring geometry.

Everything in this module is pure Python with no GUI imports, so it is fully
unit-testable on any platform.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# File kinds
# ---------------------------------------------------------------------------

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".gif"}
VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v"}
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac"}
PDF_EXTS = {".pdf"}

KIND_BY_EXT: dict[str, str] = {}
for _e in IMAGE_EXTS:
    KIND_BY_EXT[_e] = "image"
for _e in VIDEO_EXTS:
    KIND_BY_EXT[_e] = "video"
for _e in AUDIO_EXTS:
    KIND_BY_EXT[_e] = "audio"
for _e in PDF_EXTS:
    KIND_BY_EXT[_e] = "pdf"


def kind_of(path: str | Path) -> Optional[str]:
    """Return 'image' | 'video' | 'audio' | 'pdf' | None for a file path."""
    return KIND_BY_EXT.get(Path(path).suffix.lower())


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Action:
    """One thing Grayson can do to a set of files.

    kinds:    which file kinds this action accepts (a single kind, or 'any'
              for actions like images->PDF that take several of one kind).
    multi:    True if the action can take more than one input file.
    needs:    'ffmpeg' if the action shells out to ffmpeg.
    params:   names of extra parameters the GUI/CLI will ask for.
    handler:  dotted name of the function in grayson.convert.* that runs it.
    """

    id: str
    label: str
    kinds: frozenset[str]
    handler: str
    multi: bool = False
    needs: Optional[str] = None
    params: tuple[str, ...] = ()


ACTIONS: list[Action] = [
    # images ----------------------------------------------------------------
    Action("img-to-png", "Convert to PNG", frozenset({"image"}), "images.to_png"),
    Action("img-to-jpg", "Convert to JPG", frozenset({"image"}), "images.to_jpg"),
    Action("img-to-webp", "Convert to WebP", frozenset({"image"}), "images.to_webp"),
    Action("img-resize-50", "Resize 50%", frozenset({"image"}), "images.resize_half"),
    Action("img-compress", "Compress", frozenset({"image"}), "images.compress"),
    Action("img-grayscale", "Grayscale", frozenset({"image"}), "images.grayscale"),
    Action("imgs-to-pdf", "Images to PDF", frozenset({"image"}), "images.to_pdf", multi=True),
    # video -----------------------------------------------------------------
    Action("vid-to-mp4", "Convert to MP4", frozenset({"video"}), "av.video_to_mp4", needs="ffmpeg"),
    Action("vid-to-webm", "Convert to WebM", frozenset({"video"}), "av.video_to_webm", needs="ffmpeg"),
    Action("vid-to-gif", "Convert to GIF", frozenset({"video"}), "av.video_to_gif", needs="ffmpeg"),
    Action("vid-compress", "Compress video", frozenset({"video"}), "av.compress_video", needs="ffmpeg"),
    Action("vid-extract-audio", "Extract audio (MP3)", frozenset({"video"}), "av.extract_audio", needs="ffmpeg"),
    Action("vid-trim", "Trim clip", frozenset({"video"}), "av.trim", needs="ffmpeg", params=("start", "end")),
    Action("vids-merge", "Merge videos", frozenset({"video"}), "av.merge", multi=True, needs="ffmpeg"),
    # audio -----------------------------------------------------------------
    Action("aud-to-mp3", "Convert to MP3", frozenset({"audio"}), "av.audio_to_mp3", needs="ffmpeg"),
    Action("aud-to-wav", "Convert to WAV", frozenset({"audio"}), "av.audio_to_wav", needs="ffmpeg"),
    Action("aud-to-ogg", "Convert to OGG", frozenset({"audio"}), "av.audio_to_ogg", needs="ffmpeg"),
    Action("aud-trim", "Trim audio", frozenset({"audio"}), "av.trim", needs="ffmpeg", params=("start", "end")),
    # pdf -------------------------------------------------------------------
    Action("pdf-merge", "Merge PDFs", frozenset({"pdf"}), "pdf.merge", multi=True),
    Action("pdf-split", "Split into pages", frozenset({"pdf"}), "pdf.split_pages"),
    Action("pdf-compress", "Compress PDF", frozenset({"pdf"}), "pdf.compress"),
    Action("pdf-to-png", "Pages to PNG", frozenset({"pdf"}), "pdf.pages_to_png"),
]

ACTION_BY_ID: dict[str, Action] = {a.id: a for a in ACTIONS}


def actions_for(paths: list[str | Path]) -> list[Action]:
    """Actions applicable to the given selection of files.

    Rules:
      * every selected file must be a known kind;
      * if kinds are mixed, only nothing is offered (keeps the ring honest);
      * single-file selection hides multi-only actions like merging.
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
        if a.multi and len(paths) == 1 and a.id in {"pdf-merge", "vids-merge", "imgs-to-pdf"}:
            # merging/converting one file into a container of many is pointless
            if a.id != "imgs-to-pdf":  # one image -> pdf is still useful
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
