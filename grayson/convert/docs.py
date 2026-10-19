"""Office document conversions (Word, PowerPoint, Excel, OpenDocument, RTF, CSV).

Engine: LibreOffice in headless mode. Grayson does not bundle it (about 350 MB);
it is detected in this order: $GRAYSON_SOFFICE, a 'libreoffice' folder next to
the app, the standard Windows install folders, then PATH.

For "to PDF" on Windows, if LibreOffice is missing but Microsoft Office is
installed, Word/PowerPoint/Excel are driven through COM (PowerShell) instead.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from ..core import kind_of

# Grayson runs windowed (pythonw / --windowed exe). Without CREATE_NO_WINDOW,
# every soffice/powershell spawn flashes a console on Windows.
_NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}

from . import pdf as _pdf


class OfficeNotFound(RuntimeError):
    pass


def find_soffice() -> str:
    env = os.environ.get("GRAYSON_SOFFICE")
    if env and Path(env).exists():
        return env
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    cands = [base / "libreoffice" / "program" / "soffice.exe"]
    for var in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(var)
        if root:
            cands.append(Path(root) / "LibreOffice" / "program" / "soffice.exe")
    for c in cands:
        if c.exists():
            return str(c)
    for name in ("soffice", "libreoffice", "soffice.exe"):
        found = shutil.which(name)
        if found:
            return found
    raise OfficeNotFound(
        "LibreOffice was not found. Install it (free) with "
        "'winget install TheDocumentFoundation.LibreOffice' or set GRAYSON_SOFFICE "
        "to soffice.exe, then try again.")


# target extension -> LibreOffice --convert-to argument, per source kind
_FILTER = {
    ("word", "pdf"): "pdf:writer_pdf_Export", ("slides", "pdf"): "pdf:impress_pdf_Export",
    ("sheet", "pdf"): "pdf:calc_pdf_Export",
    ("text", "docx"): "docx:MS Word 2007 XML",
    ("word", "docx"): "docx:MS Word 2007 XML", ("word", "odt"): "odt",
    ("word", "rtf"): "rtf", ("word", "txt"): "txt:Text", ("word", "html"): "html",
    ("slides", "pptx"): "pptx:Impress MS PowerPoint 2007 XML", ("slides", "odp"): "odp",
    ("sheet", "xlsx"): "xlsx:Calc MS Excel 2007 XML", ("sheet", "ods"): "ods",
    ("sheet", "csv"): "csv", ("sheet", "html"): "html:HTML (StarCalc)",
}


def _lo_convert(src: Path, ext: str, dst: Path) -> Path:
    return _lo_convert_kind(kind_of(src), src, ext, dst)


def _lo_convert_kind(kind: str, src: Path, ext: str, dst: Path) -> Path:
    flt = _FILTER[(kind, ext)]
    soffice = find_soffice()
    with tempfile.TemporaryDirectory(prefix="grayson-lo-") as tmp:
        tmp = Path(tmp)
        profile = (tmp / "profile").as_uri()  # private profile: no lock clashes
        out_dir = tmp / "out"
        out_dir.mkdir()
        cmd = [soffice, f"-env:UserInstallation={profile}", "--headless",
               "--convert-to", flt, "--outdir", str(out_dir), str(src)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                                 **_NO_WINDOW)
        made = sorted(out_dir.glob(f"*.{ext}"))
        if proc.returncode != 0 or not made:
            raise RuntimeError(f"LibreOffice could not convert {src.name}: "
                               f"{(proc.stderr or proc.stdout).strip()[:300]}")
        shutil.move(str(made[0]), str(dst))
    return Path(dst)


def _com_to_pdf(src: Path, dst: Path) -> Path:
    """Microsoft Office via COM (Windows only, only used when LibreOffice is
    absent). Untested in Grayson's CI, which has no Office."""
    if os.name != "nt":
        raise OfficeNotFound("no office engine available")
    app, open_call, save_call = {
        # Read-only opens with alerts suppressed: a modal prompt (Protected
        # View, format confirm) would otherwise hang the hidden host forever.
        "word": ("Word.Application", "Documents.Open($s,$false,$true)", "SaveAs2($o,17)"),
        "slides": ("PowerPoint.Application", "Presentations.Open($s,$true,$false,$false)", "SaveAs($o,32)"),
        "sheet": ("Excel.Application", "Workbooks.Open($s,0,$true)", "ExportAsFixedFormat(0,$o)"),
    }[kind_of(src)]
    s_ = str(src).replace("'", "''")  # PowerShell single-quote escaping
    o_ = str(dst).replace("'", "''")
    ps = (f"$a=New-Object -ComObject {app};"
          "try{$a.Visible=$false;"
          "if($a.psobject.Properties['DisplayAlerts']){$a.DisplayAlerts=0};"
          f"$s='{s_}';$o='{o_}';$d=$a.{open_call};$d.{save_call};$d.Close()}}"
          f"finally{{$a.Quit()}}")
    proc = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                          capture_output=True, text=True, timeout=300,
                          **_NO_WINDOW)
    if proc.returncode != 0 or not Path(dst).exists():
        detail = (proc.stderr or proc.stdout or "").strip()[:200]
        detail = detail or "the Office app did not answer (it may have shown a prompt)"
        raise OfficeNotFound(
            f"Could not convert '{src.name}' to PDF. LibreOffice is not installed "
            f"and Microsoft Office could not do it either ({detail}). Install "
            "LibreOffice (free) with 'winget install "
            "TheDocumentFoundation.LibreOffice', then try again.")
    return Path(dst)


def _make(ext):
    def convert(src, dst, **_):
        src, dst = Path(src), Path(dst)
        if ext == "pdf":
            try:
                find_soffice()
            except OfficeNotFound:
                return _com_to_pdf(src.resolve(), dst.resolve())
        return _lo_convert(src, ext, dst)
    convert.__name__ = f"to_{ext}"
    return convert


for _ext in ("pdf", "docx", "odt", "rtf", "txt", "html", "pptx", "odp", "xlsx", "ods", "csv"):
    globals()[f"to_{_ext}"] = _make(_ext)


def pages_to_png(src, dst_dir, **_):
    """Document or slides -> PDF (temporary) -> one PNG per page/slide."""
    src = Path(src)
    with tempfile.TemporaryDirectory(prefix="grayson-pdf-") as tmp:
        tmp_pdf = Path(tmp) / (src.stem + ".pdf")
        globals()["to_pdf"](src, tmp_pdf)
        return _pdf.pages_to_png(tmp_pdf, dst_dir)


def _lo_convert_html(src: Path, dst: Path) -> Path:
    """HTML file -> .docx (used for text/Markdown -> Word)."""
    return _lo_convert_kind("text", src, "docx", dst)
