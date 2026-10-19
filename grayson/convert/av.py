"""Audio/video conversions. All of these shell out to ffmpeg, located in
this order: $GRAYSON_FFMPEG, a bundled bin/ next to the app, then PATH."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


class FFmpegNotFound(RuntimeError):
    pass

# Grayson runs windowed (pythonw / --windowed exe). Without CREATE_NO_WINDOW,
# every ffmpeg spawn flashes a console on Windows.
_NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}



def find_ffmpeg() -> str:
    env = os.environ.get("GRAYSON_FFMPEG")
    if env and Path(env).exists():
        return env
    bundled = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2])) / "bin"
    for name in ("ffmpeg.exe", "ffmpeg"):
        cand = bundled / name
        if cand.exists():
            return str(cand)
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:  # bundled wheel: imageio-ffmpeg ships a static ffmpeg binary
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    raise FFmpegNotFound(
        "ffmpeg was not found. Install it with 'winget install ffmpeg' or set "
        "the GRAYSON_FFMPEG environment variable to ffmpeg.exe."
    )


def _run(args: list[str]) -> None:
    cmd = [find_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, **_NO_WINDOW)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({proc.returncode}): {proc.stderr.strip()[:500]}")


def video_to_mp4(src, dst, **_):
    _run(["-i", str(src), "-c:v", "libx264", "-preset", "fast", "-crf", "20",
          "-c:a", "aac", "-movflags", "+faststart", str(dst)])
    return Path(dst)


def video_to_webm(src, dst, **_):
    _run(["-i", str(src), "-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0",
          "-c:a", "libopus", str(dst)])
    return Path(dst)


def video_to_gif(src, dst, fps: int = 12, width: int = 480, **_):
    filt = f"fps={fps},scale={width}:-1:flags=lanczos"
    _run(["-i", str(src), "-vf", filt, "-loop", "0", str(dst)])
    return Path(dst)


def compress_video(src, dst, crf: int = 28, **_):
    _run(["-i", str(src), "-c:v", "libx264", "-crf", str(crf), "-preset", "medium",
          "-c:a", "aac", "-b:a", "128k", str(dst)])
    return Path(dst)


def extract_audio(src, dst, **_):
    _run(["-i", str(src), "-vn", "-c:a", "libmp3lame", "-q:a", "2", str(dst)])
    return Path(dst)


def trim(src, dst, start: float = 0.0, end: float = 30.0, **_):
    """Trim any audio/video file to [start, end] seconds.

    Re-encodes (ffmpeg picks the default codec for the container) instead of
    stream-copying: stream copy snaps cut points to keyframes and the result
    can be seconds longer than asked for. Slower, but the cut is accurate.
    """
    if float(end) <= float(start):
        raise ValueError("trim end must be after start")
    _run(["-i", str(src), "-ss", str(start), "-to", str(end), str(dst)])
    return Path(dst)


def merge(srcs, dst, **_):
    """Concatenate videos of the same codec family (concat demuxer, stream copy)."""
    if isinstance(srcs, (str, Path)):
        srcs = [srcs]
    if len(srcs) < 2:
        raise ValueError("merge needs at least two videos")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for s in srcs:
            f.write(f"file '{Path(s).resolve()}'\n")
        list_file = f.name
    try:
        _run(["-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", str(dst)])
    finally:
        os.unlink(list_file)
    return Path(dst)


def audio_to_mp3(src, dst, **_):
    _run(["-i", str(src), "-c:a", "libmp3lame", "-q:a", "2", str(dst)])
    return Path(dst)


def audio_to_wav(src, dst, **_):
    _run(["-i", str(src), "-c:a", "pcm_s16le", str(dst)])
    return Path(dst)


def audio_to_ogg(src, dst, **_):
    _run(["-i", str(src), "-c:a", "libvorbis", "-q:a", "5", str(dst)])
    return Path(dst)


def video_to_mkv(src, dst, **_):
    _run(["-i", str(src), "-c:v", "libx264", "-crf", "20", "-c:a", "aac", str(dst)])
    return Path(dst)


def video_to_mov(src, dst, **_):
    _run(["-i", str(src), "-c:v", "libx264", "-crf", "20", "-c:a", "aac",
          "-pix_fmt", "yuv420p", str(dst)])
    return Path(dst)


def video_to_avi(src, dst, **_):
    _run(["-i", str(src), "-c:v", "mpeg4", "-q:v", "4", "-c:a", "libmp3lame", str(dst)])
    return Path(dst)


def scale_720p(src, dst, **_):
    """Downscale to 720 px tall (width keeps the aspect ratio, forced even)."""
    _run(["-i", str(src), "-vf", "scale=-2:720", "-c:v", "libx264", "-crf", "23",
          "-c:a", "aac", str(dst)])
    return Path(dst)


def mute(src, dst, **_):
    _run(["-i", str(src), "-an", "-c:v", "copy", str(dst)])
    return Path(dst)


def extract_wav(src, dst, **_):
    _run(["-i", str(src), "-vn", "-c:a", "pcm_s16le", str(dst)])
    return Path(dst)


def audio_to_flac(src, dst, **_):
    _run(["-i", str(src), "-c:a", "flac", str(dst)])
    return Path(dst)


def audio_to_m4a(src, dst, **_):
    _run(["-i", str(src), "-vn", "-c:a", "aac", "-b:a", "192k", str(dst)])
    return Path(dst)


def audio_to_aac(src, dst, **_):
    _run(["-i", str(src), "-vn", "-c:a", "aac", "-b:a", "192k", str(dst)])
    return Path(dst)


def audio_to_opus(src, dst, **_):
    _run(["-i", str(src), "-c:a", "libopus", "-b:a", "128k", str(dst)])
    return Path(dst)


def compress_audio(src, dst, **_):
    """Small spoken-word/music file: MP3 at 96 kbit/s."""
    _run(["-i", str(src), "-vn", "-c:a", "libmp3lame", "-b:a", "96k", str(dst)])
    return Path(dst)


def merge_audio(srcs, dst, **_):
    """Join audio files end to end. Re-encodes (the inputs may differ in
    codec), using the default encoder for the output extension."""
    if isinstance(srcs, (str, Path)):
        srcs = [srcs]
    if len(srcs) < 2:
        raise ValueError("merge needs at least two audio files")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for s in srcs:
            f.write("file '" + str(Path(s).resolve()).replace("'", "'\\''") + "'\n")
        list_file = f.name
    try:
        _run(["-f", "concat", "-safe", "0", "-i", list_file, str(dst)])
    finally:
        os.unlink(list_file)
    return Path(dst)
