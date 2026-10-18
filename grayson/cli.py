"""Command line front end: the same conversion engine the ring menu uses.

    python -m grayson --list
    python -m grayson photo.png --action img-to-webp
    python -m grayson a.pdf b.pdf --action pdf-merge
    python -m grayson clip.mp4 --action vid-trim --param start=5 --param end=12
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .core import ACTIONS, ACTION_BY_ID, actions_for, resolve_handler, unique_output

# Actions whose output is a directory of files rather than a single file.
_DIR_OUTPUT = {"pdf-split", "pdf-to-png"}
# Default output extension per action (None keeps the source extension).
_EXT = {
    "img-to-png": "png", "img-to-jpg": "jpg", "img-to-webp": "webp",
    "imgs-to-pdf": "pdf",
    "vid-to-mp4": "mp4", "vid-to-webm": "webm", "vid-to-gif": "gif",
    "vid-compress": "mp4", "vid-extract-audio": "mp3", "vids-merge": "mp4",
    "aud-to-mp3": "mp3", "aud-to-wav": "wav", "aud-to-ogg": "ogg",
    "pdf-merge": "pdf", "pdf-compress": "pdf",
}


def run_action(action_id: str, paths: list[str | Path], params: dict | None = None):
    """Run one action on files; returns the list of written paths.

    Shared by the CLI and the GUI so behaviour is identical in both.
    """
    params = dict(params or {})
    action = ACTION_BY_ID[action_id]
    handler = resolve_handler(action.handler)
    paths = [Path(p) for p in paths]

    if action_id in _DIR_OUTPUT:
        out_dir = unique_output(paths[0], new_ext=None, suffix="-grayson")
        out_dir = out_dir.with_suffix("")  # strip the kept source suffix
        written = handler(paths[0] if len(paths) == 1 else paths, out_dir, **params)
        return list(written)

    if action.multi:
        out = unique_output(paths[0], new_ext=_EXT.get(action_id))
        handler(paths, out, **params)
        return [out]

    written = []
    for p in paths:  # single-file action applied to a multi-selection
        out = unique_output(p, new_ext=_EXT.get(action_id))
        handler(p, out, **params)
        written.append(out)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="grayson",
        description="Grayson - the zero-click offline file converter for Windows.",
    )
    parser.add_argument("files", nargs="*", help="file(s) to convert")
    parser.add_argument("--action", help="action id (see --list)")
    parser.add_argument("--param", action="append", default=[],
                        help="extra parameter as key=value (repeatable)")
    parser.add_argument("--list", action="store_true", help="list all actions and exit")
    parser.add_argument("--gui", action="store_true", help="start the ring-menu app")
    parser.add_argument("--version", action="version", version=f"grayson {__version__}")
    args = parser.parse_args(argv)

    if args.gui:
        from .gui.app import main as gui_main
        return gui_main()

    if args.list:
        for a in ACTIONS:
            extra = []
            if a.multi:
                extra.append("multi-file")
            if a.needs:
                extra.append(f"needs {a.needs}")
            if a.params:
                extra.append("params: " + ", ".join(a.params))
            note = f"  ({'; '.join(extra)})" if extra else ""
            kinds = "/".join(sorted(a.kinds))
            print(f"{a.id:<20} {a.label:<24} [{kinds}]{note}")
        return 0

    if not args.files or not args.action:
        parser.error("give FILES and --action (or --list / --gui)")

    params = {}
    for item in args.param:
        if "=" not in item:
            parser.error(f"--param must be key=value, got {item!r}")
        k, v = item.split("=", 1)
        params[k] = float(v) if v.replace(".", "", 1).isdigit() else v

    valid = {a.id for a in actions_for(args.files)}
    if args.action not in valid:
        parser.error(
            f"action {args.action!r} does not apply to these files. "
            f"Valid here: {', '.join(sorted(valid)) or 'none'}"
        )

    written = run_action(args.action, args.files, params)
    for w in written:
        print(w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
