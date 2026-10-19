"""Single-instance guard: the named lock keeps a second launch out, a clean
quit frees the next one, and a repeat launch pings the running instance.
QLockFile/QLocalServer are QtCore/QtNetwork - no display needed."""
import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("PySide6") is None, reason="PySide6 not installed")

try:  # Qt shared libraries can be missing even when the wheel is installed
    from PySide6.QtCore import QLockFile  # noqa: F401
    from PySide6.QtNetwork import QLocalServer  # noqa: F401
except Exception as exc:  # pragma: no cover
    pytest.skip(f"Qt runtime unavailable: {exc}", allow_module_level=True)


def test_second_instance_is_locked_out(tmp_path):
    from grayson.gui.app import SingleInstance

    lock = str(tmp_path / "grayson-test.lock")
    first = SingleInstance(lock)
    assert first.acquire() is True
    second = SingleInstance(lock)
    assert second.acquire() is False  # the running instance keeps its lock
    first.release()
    third = SingleInstance(lock)
    assert third.acquire() is True  # a clean quit frees the next launch
    third.release()


def test_second_launch_pings_the_running_instance(tmp_path):
    import os
    import time
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from grayson.gui.app import SingleInstance

    # QApplication (not bare QCoreApplication) so widget tests can reuse it
    app = QApplication.instance() or QApplication([])
    lock = str(tmp_path / "grayson-ipc.lock")
    first = SingleInstance(lock)
    assert first.acquire() is True
    pings = []
    assert first.listen(lambda: pings.append(1)) is not None

    second = SingleInstance(lock)
    assert second.acquire() is False
    second.notify_running()

    for _ in range(50):  # let the local socket deliver
        app.processEvents()
        if pings:
            break
        time.sleep(0.02)
    assert pings == [1]
