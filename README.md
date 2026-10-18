<p align="center">
  <img src="assets/banner.svg" alt="Grayson banner" width="100%"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows-0a0e1a?style=flat-square&logo=windows&logoColor=4f8dff" alt="Windows"/>
  <img src="https://img.shields.io/badge/python-3.10%2B-0a0e1a?style=flat-square&logo=python&logoColor=4f8dff" alt="Python 3.10+"/>
  <img src="https://img.shields.io/badge/license-MIT-0a0e1a?style=flat-square" alt="MIT"/>
  <img src="https://img.shields.io/badge/network-offline-0a0e1a?style=flat-square" alt="Offline"/>
</p>

<p align="center"><b>Grayson</b> is a zero-click, fully offline file converter for Windows.
Copy a file, tap <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>Space</kbd>, and a ring menu opens at
your cursor with everything you can do to that file. Pick a slice. Done.</p>

---

## What it does

| You give it | The ring offers |
|---|---|
| Images (png, jpg, webp, bmp, tiff, gif) | Convert to PNG / JPG / WebP, resize 50%, compress, grayscale, images to PDF |
| Video (mp4, mkv, mov, webm, avi) | Convert to MP4 / WebM / GIF, compress, extract audio (MP3), trim, merge videos |
| Audio (mp3, wav, ogg, m4a, flac, aac) | Convert to MP3 / WAV / OGG, trim |
| PDF | Merge, split into pages, compress, render pages to PNG |

Every conversion runs **locally** - no upload, no account, no watermark, no
conversion allowance. Output lands next to the original as `name-grayson.ext`
and never overwrites anything.

## Install

**Easiest:** download `Grayson-windows.zip` from the latest
[Actions run](../../actions) (or a Release, when tagged), unzip anywhere, run
`Grayson.exe`. ffmpeg is bundled, nothing else to install.

**From source** (Python 3.10+):

```powershell
git clone https://github.com/mjanthony819/grayson.git
cd grayson
pip install .
grayson --gui
```

For audio/video actions from source you also need ffmpeg
(`winget install ffmpeg`), unless `imageio-ffmpeg` is installed - then it just works.

## Use it

1. **Ring menu** - copy file(s) in Explorer with `Ctrl+C`, press
   `Ctrl+Shift+Space`. The ring opens at your cursor. Click a slice or press
   its number. `Esc` or the centre `X` cancels.
2. **Drop zone** - drag files onto the small Grayson window instead.
3. **Command line** - the same engine, scriptable:

```powershell
grayson --list                                   # every action
grayson photo.png --action img-to-webp
grayson a.pdf b.pdf c.pdf --action pdf-merge
grayson clip.mp4 --action vid-trim --param start=5 --param end=12
```

## How it works

```
Explorer copy / drag-and-drop
        |
   kind detection  (grayson/core.py - extension -> image | video | audio | pdf)
        |
   action registry (one declarative table -> which actions fit the selection)
        |
   ring menu (PySide6, QPainter donut slices, geometry unit-tested headless)
        |
   conversion engine - Pillow (images) | PyMuPDF (PDF) | ffmpeg (audio/video)
        |
   unique output name next to the source -> tray notification
```

The conversion engine is a plain Python library (`grayson/convert/`) with no Qt
imports, so the CLI and the GUI share identical behaviour and the whole engine
is testable without a display.

## Development

```powershell
pip install -e ".[dev]"
python -m pytest tests/ -q
```

30 tests cover kind detection, the action registry, ring slice geometry,
every image/PDF conversion, ffmpeg round-trips (generated clips) and the CLI.
GUI painting is smoke-tested offscreen with Qt's `offscreen` platform.

CI (`.github/workflows/build.yml`) runs the tests on Ubuntu, then builds the
portable `Grayson-windows.zip` with PyInstaller on `windows-latest` and
attaches it to releases.

## Honest limitations

- **Windows-focused.** The engine is cross-platform, but the hotkey +
  Explorer clipboard flow is built and packaged for Windows.
- Trim **re-encodes** instead of stream-copying, so the cut lands exactly
  where you asked (stream copy snaps to keyframes) - slower on long files.
- PDF compress downsamples large embedded images to ~1500px JPEG; it is not a
  lossless archiver.
- Office documents (.docx/.pptx) are out of scope - real conversion there
  needs Word or LibreOffice installed, and Grayson stays self-contained.
- ffmpeg is LGPL/GPL; the Windows bundle pulls it in via `imageio-ffmpeg`.

## Stack

Python - PySide6 (ring menu, tray) - pynput (global hotkey) - Pillow (images) -
PyMuPDF (PDF) - ffmpeg via imageio-ffmpeg (audio/video) - PyInstaller (packaging) -
pytest + GitHub Actions (CI).

---

<p align="center"><i>Built by a dual degree student who got tired of upload-wait-download converters.</i></p>
