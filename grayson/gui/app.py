"""Grayson desktop app: tray icon, global hotkey, drop zone, worker threads.

Flow: copy file(s) in Explorer -> press Ctrl+Shift+Space -> ring menu opens
at the cursor -> pick a slice -> converted file lands next to the original.
Or drag files onto the drop zone window instead of using the hotkey.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtGui import QAction, QColor, QGuiApplication, QIcon, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QInputDialog, QLabel, QMenu,
                               QSystemTrayIcon, QVBoxLayout, QWidget)

from ..core import ACTION_BY_ID, actions_for
from ..cli import run_action
from .ring import RingMenu

HOTKEY = "<ctrl>+<shift>+<space>"


def _icon() -> QIcon:
    """A simple electric-blue ring, drawn in code so no asset file is needed."""
    from PySide6.QtGui import QPixmap
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(70, 130, 255), 7))
    p.drawEllipse(10, 10, 44, 44)
    p.end()
    return QIcon(pm)


class _Worker(QThread):
    done = Signal(list)
    failed = Signal(str)

    def __init__(self, action_id, paths, params):
        super().__init__()
        self._args = (action_id, paths, params)

    def run(self):
        try:
            self.done.emit(run_action(*self._args))
        except Exception:
            self.failed.emit(traceback.format_exc(limit=3))


class _HotkeyBridge(QObject):
    fired = Signal()


class DropZone(QWidget):
    """Small always-available window: drop files to open the ring for them."""

    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Grayson")
        self.setAcceptDrops(True)
        self.setFixedSize(260, 140)
        self.setStyleSheet(
            "QWidget { background: #0a0e1a; color: #e6eeff; border: 2px dashed #4682ff;"
            " border-radius: 12px; } QLabel { border: none; }")
        layout = QVBoxLayout(self)
        label = QLabel("Drop files here\nor press Ctrl+Shift+Space\nafter copying a file")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

    def dragEnterEvent(self, ev):
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()

    def dropEvent(self, ev):
        files = [u.toLocalFile() for u in ev.mimeData().urls() if u.isLocalFile()]
        files = [f for f in files if Path(f).is_file()]
        if files:
            self.files_dropped.emit(files)


class GraysonApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.tray = QSystemTrayIcon(_icon(), self.app)
        self.tray.setToolTip("Grayson - offline file converter")

        self.dropzone = DropZone()
        self.dropzone.files_dropped.connect(self.open_ring_for)

        menu = QMenu()
        open_act = QAction("Open drop zone", menu)
        open_act.triggered.connect(self.dropzone.show)
        hint = QAction(f"Hotkey: Ctrl+Shift+Space (copy a file first)", menu)
        hint.setEnabled(False)
        quit_act = QAction("Quit", menu)
        quit_act.triggered.connect(self.app.quit)
        menu.addAction(open_act)
        menu.addAction(hint)
        menu.addSeparator()
        menu.addAction(quit_act)
        self.tray.setContextMenu(menu)
        self.tray.show()

        self._ring: RingMenu | None = None
        self._worker: _Worker | None = None
        self._paths: list[str] = []

        # global hotkey on a background thread, bridged into the Qt loop
        self._bridge = _HotkeyBridge()
        self._bridge.fired.connect(self._on_hotkey)
        self._listener = None
        self._start_hotkey()

    # -- hotkey ---------------------------------------------------------------
    def _start_hotkey(self):
        try:
            from pynput import keyboard

            def on_fire():
                self._bridge.fired.emit()

            self._listener = keyboard.GlobalHotKeys({HOTKEY: on_fire})
            self._listener.start()
        except Exception:
            # hotkey is a bonus; the drop zone still works without it
            self._listener = None

    def _on_hotkey(self):
        files = self._clipboard_files()
        if files:
            self.open_ring_for(files, at_cursor=True)
        else:
            self.dropzone.show()
            self.tray.showMessage(
                "Grayson", "No files on the clipboard - copy a file first, or drop files here.",
                QSystemTrayIcon.Information, 3000)

    @staticmethod
    def _clipboard_files() -> list[str]:
        md = QGuiApplication.clipboard().mimeData()
        if not md.hasUrls():
            return []
        return [u.toLocalFile() for u in md.urls()
                if u.isLocalFile() and Path(u.toLocalFile()).is_file()]

    # -- ring -----------------------------------------------------------------
    def open_ring_for(self, files: list[str], at_cursor: bool = False):
        acts = actions_for(files)
        if not acts:
            self.tray.showMessage("Grayson", "Nothing Grayson can do with that selection.",
                                  QSystemTrayIcon.Warning, 3000)
            return
        self._paths = files
        self._ring = RingMenu(acts)
        self._ring.picked.connect(self._on_pick)
        from PySide6.QtGui import QCursor
        self._ring.show_at(QCursor.pos() if at_cursor else
                           self.dropzone.frameGeometry().center())

    def _on_pick(self, action_id: str):
        params = {}
        action = ACTION_BY_ID[action_id]
        if "start" in action.params:  # trim: ask once, small dialog
            text, ok = QInputDialog.getText(
                None, "Grayson - trim", "Start and end in seconds (e.g. 5, 12):",
                text="0, 30")
            if not ok:
                return
            try:
                a, b = [float(x) for x in text.split(",")[:2]]
                params = {"start": a, "end": b}
            except ValueError:
                self.tray.showMessage("Grayson", "Could not read those times.",
                                      QSystemTrayIcon.Warning, 3000)
                return
        if "crop" in action.params:
            text, ok = QInputDialog.getText(
                None, "Grayson - crop",
                "Percent to remove from left, top, right, bottom (e.g. 10, 0, 10, 20):",
                text="10, 10, 10, 10")
            if not ok:
                return
            try:
                vals = [float(x) for x in text.split(",")]
                if len(vals) != 4:
                    raise ValueError
                params = dict(zip(("left", "top", "right", "bottom"), vals))
            except ValueError:
                self.tray.showMessage("Grayson", "Give four numbers, comma separated.",
                                      QSystemTrayIcon.Warning, 3000)
                return
        self._worker = _Worker(action_id, self._paths, params)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    # -- results --------------------------------------------------------------
    def _on_done(self, written: list):
        names = ", ".join(Path(w).name for w in written[:3])
        if len(written) > 3:
            names += f" and {len(written) - 3} more"
        self.tray.showMessage("Grayson", f"Done: {names}",
                              QSystemTrayIcon.Information, 4000)

    def _on_failed(self, err: str):
        last = err.strip().splitlines()[-1] if err.strip() else "unknown error"
        self.tray.showMessage("Grayson - failed", last[:200],
                              QSystemTrayIcon.Critical, 5000)

    def run(self) -> int:
        self.dropzone.show()
        return self.app.exec()


def main() -> int:
    return GraysonApp().run()
