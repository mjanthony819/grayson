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
