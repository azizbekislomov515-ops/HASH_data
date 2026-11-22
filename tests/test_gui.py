"""Offscreen integration tests exercising real Qt workers and widgets."""

import os
import time
from pathlib import Path
from collections.abc import Callable, Iterator

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["QT_QPA_PLATFORMTHEME"] = ""
os.environ["QT_STYLE_OVERRIDE"] = "Fusion"

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from hashforge.gui.main_window import MainWindow


def wait_for(app: QApplication, predicate: Callable[[], bool]) -> None:
    """Pump Qt until the expected condition, with a bounded timeout."""
    deadline = time.monotonic() + 10
    while not predicate():
        app.processEvents()
        if time.monotonic() > deadline:
            pytest.fail("Qt condition timed out")
        time.sleep(0.005)
    app.processEvents()


@pytest.fixture(scope="session")
def qt_app() -> Iterator[QApplication]:
    """Keep one QApplication alive for the full test session."""
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()


@pytest.fixture
def window(tmp_path: Path, qt_app: QApplication) -> Iterator[tuple[QApplication, MainWindow]]:
    """Create a real window with isolated settings and deterministic cleanup."""
    app = qt_app
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    widget = MainWindow()
    widget.show()
    yield app, widget
    widget.close()
    wait_for(app, lambda: not any(tab.workers for tab in widget.job_tabs))
    widget.close()
    widget.deleteLater()
    app.processEvents()


def test_live_text_and_verify(window: tuple[QApplication, MainWindow]) -> None:
    app, widget = window
    widget.text_tab.editor.setPlainText("abc")
    wait_for(app, lambda: bool(widget.text_tab.results.results))
    sha = next(r for r in widget.text_tab.results.results if r.algorithm == "sha256")
    assert sha.formatted() == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    verify = widget.verify_tab
    verify.source.setCurrentIndex(1)
    verify.expected.setText(sha.formatted())
    verify.verify()
    wait_for(app, lambda: verify.verdict.text() == "MATCH")
    verify.expected.setText("0" * 64)
    assert verify.verdict.text() == "Not verified"
    verify.verify()
    wait_for(app, lambda: verify.verdict.text() == "MISMATCH")


def test_file_and_batch(window: tuple[QApplication, MainWindow], tmp_path: Path) -> None:
    app, widget = window
    path = tmp_path / "capture.pcap"
    path.write_bytes(b"\xd4\xc3\xb2\xa1" + bytes(range(256)) * 100)
    widget.file_tab.path.setText(str(path))
    widget.file_tab.calculate()
    wait_for(app, lambda: bool(widget.file_tab.results.results))
    assert "application/vnd.tcpdump.pcap" in widget.file_tab.info.text()
    widget.batch_tab.paths = (str(path), str(tmp_path / "missing"))
    widget.batch_tab.calculate()
    wait_for(app, lambda: bool(widget.batch_tab.results.results))
    assert "1 file error" in widget.batch_tab.status.text()


def test_invalid_input_and_shutdown(window: tuple[QApplication, MainWindow]) -> None:
    app, widget = window
    widget.text_tab.mode.setCurrentIndex(1)
    widget.text_tab.editor.setPlainText("xyz")
    wait_for(app, lambda: "Invalid hex" in widget.text_tab.status.text())
    assert not widget.text_tab.results.results
    widget.text_tab.mode.setCurrentIndex(0)
    widget.text_tab.editor.setPlainText("a" * 1_000_000)
    widget.text_tab.calculate()
    widget.close()
    wait_for(app, lambda: not any(tab.workers for tab in widget.job_tabs))


def test_hmac_copy_and_key_validation(window: tuple[QApplication, MainWindow]) -> None:
    """Validate keys in the GUI and copy encoded HMAC results."""
    import base64
    import hmac

    app, widget = window
    for name, checkbox in widget.checkboxes.items():
        checkbox.setChecked(name == "sha256")
    widget.text_tab.editor.setPlainText("abc")
    widget.hmac_enabled.setChecked(True)
    wait_for(app, lambda: "must not be empty" in widget.text_tab.status.text())
    widget.key_mode.setCurrentIndex(1)
    widget.key.setText("736563726574")
    wait_for(app, lambda: bool(widget.text_tab.results.results))
    results = widget.text_tab.results
    assert results.results[0].is_hmac
    expected = hmac.digest(b"secret", b"abc", "sha256")
    assert results.results[0].value == expected
    results.encoding.setCurrentText("base64")
    results.table.cellWidget(0, 4).click()
    assert app.clipboard().text() == base64.b64encode(expected).decode("ascii")
    widget.key.setText("not hex")
    wait_for(app, lambda: "Invalid hex" in widget.text_tab.status.text())
    assert not results.results


def test_replaced_text_cannot_publish_stale_results(
    window: tuple[QApplication, MainWindow],
) -> None:
    """An older worker cannot replace the latest text snapshot's output."""
    import hashlib

    app, widget = window
    widget.text_tab.editor.setPlainText("a" * 100_000)
    widget.text_tab.calculate()
    widget.text_tab.editor.setPlainText("latest")
    wait_for(app, lambda: bool(widget.text_tab.results.results))
    wait_for(app, lambda: not widget.text_tab.workers)
    result = next(r for r in widget.text_tab.results.results if r.algorithm == "sha256")
    assert result.value == hashlib.sha256(b"latest").digest()
