"""PyInstaller entry point: no arguments -> GUI, arguments -> CLI."""
import sys

from grayson.cli import main

if len(sys.argv) == 1:
    sys.argv = [sys.argv[0], "--gui"]

raise SystemExit(main())
