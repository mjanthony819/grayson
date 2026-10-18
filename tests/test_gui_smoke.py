"""GUI smoke test: builds the real ring menu offscreen and checks the pure
geometry the widget relies on. Runs only where PySide6 is installed."""
import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("PySide6") is None, reason="PySide6 not installed")

try:  # Qt shared libraries can be missing even when the wheel is installed
    from PySide6.QtWidgets import QApplication  # noqa: F401
except Exception as exc:  # pragma: no cover
    pytest.skip(f"Qt runtime unavailable: {exc}", allow_module_level=True)


def test_ring_menu_offscreen(tmp_path):
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from grayson.core import actions_for
    from grayson.gui.ring import RingMenu

    app = QApplication.instance() or QApplication([])
    acts = actions_for(["x.png", "y.jpg"])
    assert acts, "expected image actions"
    ring = RingMenu(acts)
    picked = []
    ring.picked.connect(picked.append)
    ring._pick(0)  # number-key path: no mouse needed
    assert picked == [acts[0].id]


def test_ring_pages_and_labels_fit():
    """Over 8 actions the ring pages with a 'More' slice, and every label fits
    its fixed box on every page (so neighbours cannot collide)."""
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QFontMetrics
    from PySide6.QtWidgets import QApplication
    from grayson.core import actions_for
    from grayson.gui import ring as R

    app = QApplication.instance() or QApplication([])
    acts = actions_for(["x.png"])
    assert len(acts) > R.PAGE_SIZE
    menu = R.RingMenu(acts)
    seen = []
    fm = QFontMetrics(menu.font())
    for _ in range(menu.pages):
        assert len(menu._actions) <= R.PAGE_SIZE
        assert menu._actions[-1].id == R.MORE_ID
        for a in menu._actions[:-1]:
            seen.append(a.id)
            from PySide6.QtCore import QRect
            box = fm.boundingRect(QRect(0, 0, R.LABEL_W, 1000), 0x1000 | 0x0004, a.label)
            assert box.width() <= R.LABEL_W and box.height() <= R.LABEL_H - 16, a.label
        menu._pick(len(menu._actions) - 1)  # 'More' cycles, emits nothing
    assert seen == [a.id for a in acts]  # every action reachable exactly once
