import subprocess

import pytest

from grayson.cli import run_action
from grayson.convert.av import FFmpegNotFound, find_ffmpeg

try:
    FFMPEG = find_ffmpeg()
except FFmpegNotFound:
    FFMPEG = None

pytestmark = pytest.mark.skipif(FFMPEG is None, reason="ffmpeg not installed")


def _make_video(path, seconds=2):
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error",
         "-f", "lavfi", "-i", f"testsrc=duration={seconds}:size=160x120:rate=10",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
         str(path)], check=True)


def _probe_duration(path):
    out = subprocess.run(
        [FFMPEG, "-i", str(path), "-hide_banner"],
        capture_output=True, text=True).stderr
    for line in out.splitlines():
        if "Duration" in line:
            hms = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = hms.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise AssertionError("no duration in ffmpeg output")


@pytest.fixture
def clip(tmp_path):
    p = tmp_path / "clip.mp4"
    _make_video(p)
    return p


def test_video_to_webm(clip):
    [out] = run_action("vid-to-webm", [clip])
    assert out.suffix == ".webm" and out.stat().st_size > 1000


def test_video_to_gif(clip):
    [out] = run_action("vid-to-gif", [clip])
    assert out.suffix == ".gif" and out.stat().st_size > 1000


def test_extract_audio(clip):
    [out] = run_action("vid-extract-audio", [clip])
    assert out.suffix == ".mp3" and _probe_duration(out) == pytest.approx(2, abs=0.6)


def test_trim(clip):
    [out] = run_action("vid-trim", [clip], {"start": 0.0, "end": 1.0})
    assert _probe_duration(out) == pytest.approx(1, abs=0.6)


def test_merge(tmp_path, clip):
    other = tmp_path / "clip2.mp4"
    _make_video(other)
    [out] = run_action("vids-merge", [clip, other])
    assert _probe_duration(out) == pytest.approx(4, abs=1.0)


def test_audio_roundtrip(clip):
    [mp3] = run_action("vid-extract-audio", [clip])
    [wav] = run_action("aud-to-wav", [mp3])
    assert wav.suffix == ".wav"
    [ogg] = run_action("aud-to-ogg", [wav])
    assert ogg.suffix == ".ogg"
    [back] = run_action("aud-to-mp3", [ogg])
    assert back.suffix == ".mp3"
