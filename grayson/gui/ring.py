"""The ring menu: a circular pie menu drawn with QPainter.

Geometry math lives in grayson.core (slice_index / slice_mid_angle) so it is
unit-tested without a display; this file is only painting and events.
"""
from __future__ import annotations

import math

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from ..core import Action, slice_index, slice_mid_angle

BG = QColor(10, 14, 26, 235)          # Gotham night
BG_HOVER = QColor(35, 90, 190, 245)   # electric blue
EDGE = QColor(70, 130, 255)
TEXT = QColor(230, 238, 255)

OUTER_R = 215
DEAD_R = 56
PAGE_SIZE = 8          # slices per page; with more actions the 8th is 'More'
MORE_ID = "__more__"
LABEL_W = 86
LABEL_H = 46


class RingMenu(QWidget):
    """Popup circular menu. Emits picked(action_id) or just closes."""

    picked = Signal(str)

    def __init__(self, actions: list[Action]):
        super().__init__(
            None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.Popup,
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._all = list(actions)
        self._page = 0
        self._actions = self._page_items()
        self._hover: int | None = None
        size = OUTER_R * 2 + 24
        self.setFixedSize(size, size)
        self.setMouseTracking(True)

    # -- paging -------------------------------------------------------------
    @property
    def pages(self) -> int:
        n = len(self._all)
        return 1 if n <= PAGE_SIZE else -(-n // (PAGE_SIZE - 1))

    def _page_items(self) -> list[Action]:
        """Slices on the current page. Over PAGE_SIZE actions, each page shows
        PAGE_SIZE-1 of them plus a 'More' slice that cycles to the next page."""
        if len(self._all) <= PAGE_SIZE:
            return list(self._all)
        per = PAGE_SIZE - 1
        items = list(self._all[self._page * per:(self._page + 1) * per])
        items.append(Action(MORE_ID, "More \u203a", frozenset(), ""))
        return items

    def _next_page(self):
        self._page = (self._page + 1) % self.pages
        self._actions = self._page_items()
        self._hover = None
        self.update()

    # -- geometry helpers ---------------------------------------------------
    def _norm(self, pos) -> tuple[float, float]:
        """Widget point -> normalised ring coordinates (radius 1)."""
        cx, cy = self.width() / 2, self.height() / 2
        return ((pos.x() - cx) / OUTER_R, (pos.y() - cy) / OUTER_R)

    # -- painting -------------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        n = len(self._actions)
        rect = self.rect().adjusted(12, 12, -12, -12)

        for i, action in enumerate(self._actions):
            width = 360.0 / n
            gap = 0.9 if n > 1 else 0.0
            # Qt angles: degrees counter-clockwise from 3 o'clock. Slice i
            # covers clock-angles [i*w, (i+1)*w] measured clockwise from 12.
            start_deg = 90 - (i + 1) * width + gap
            span = width - 2 * gap
            inner_rect = rect.adjusted(OUTER_R - DEAD_R, OUTER_R - DEAD_R,
                                       -(OUTER_R - DEAD_R), -(OUTER_R - DEAD_R))
            path = QPainterPath()
            path.arcMoveTo(rect, start_deg)
            path.arcTo(rect, start_deg, span)                      # outer edge
            path.arcTo(inner_rect, start_deg + span, -span)        # inner edge back
            path.closeSubpath()                                    # radial line

            p.setBrush(BG_HOVER if i == self._hover else BG)
            p.setPen(QPen(EDGE, 1.4))
            p.drawPath(path)

            # label at the mid-angle, halfway between dead zone and edge
            mid = slice_mid_angle(i, n)
            r = (DEAD_R + OUTER_R) / 2 + 6
            lx = cx + r * math.sin(mid)
            ly = cy - r * math.cos(mid)
            p.setPen(TEXT)
            font = p.font()
            font.setPointSize(9)
            p.setFont(font)
            # Fixed box narrower than the slice chord at this radius, so labels
            # in neighbouring slices can never touch; long labels wrap to 2 lines.
            p.drawText(QRect(int(lx) - LABEL_W // 2, int(ly) - LABEL_H // 2,
                             LABEL_W, LABEL_H),
                       Qt.AlignCenter | Qt.TextWordWrap, f"{i + 1}\n{action.label}")

        # centre dismiss disc
        p.setBrush(BG)
        p.setPen(QPen(EDGE, 1.6))
        p.drawEllipse(int(cx - DEAD_R), int(cy - DEAD_R), DEAD_R * 2, DEAD_R * 2)
        p.setPen(TEXT)
        font = p.font()
        font.setPointSize(14)
        p.setFont(font)
        p.drawText(int(cx - DEAD_R), int(cy - DEAD_R), DEAD_R * 2, DEAD_R * 2,
                   Qt.AlignCenter, "X")
        if self.pages > 1:
            font.setPointSize(8)
            p.setFont(font)
            p.drawText(int(cx - DEAD_R), int(cy + 18), DEAD_R * 2, 16,
                       Qt.AlignCenter, f"{self._page + 1}/{self.pages}")
        p.end()

    # -- events ---------------------------------------------------------------
    def mouseMoveEvent(self, ev):
        dx, dy = self._norm(ev.position())
        self._hover = slice_index(dx, dy, len(self._actions), dead_radius=DEAD_R / OUTER_R)
        self.update()

    def mouseReleaseEvent(self, ev):
        dx, dy = self._norm(ev.position())
        idx = slice_index(dx, dy, len(self._actions), dead_radius=DEAD_R / OUTER_R)
        if idx is None:
            import math as m
            if m.hypot(dx, dy) <= DEAD_R / OUTER_R + 0.02:
                self.close()  # centre dismiss
            return
        self._pick(idx)

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_Escape:
            self.close()
            return
        if Qt.Key_1 <= ev.key() <= Qt.Key_9:
            idx = ev.key() - Qt.Key_1
            if idx < len(self._actions):
                self._pick(idx)

    def _pick(self, idx: int):
        if self._actions[idx].id == MORE_ID:
            self._next_page()
            return
        self.picked.emit(self._actions[idx].id)
        self.close()

    def show_at(self, global_pos):
        self.move(int(global_pos.x() - self.width() / 2),
                  int(global_pos.y() - self.height() / 2))
        self.show()
        self.raise_()
        self.activateWindow()
