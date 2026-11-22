"""Generate documentation screenshots using real offscreen Qt widgets."""

import os
from pathlib import Path
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_PLATFORMTHEME"] = ""
os.environ["QT_STYLE_OVERRIDE"] = "Fusion"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from hashforge.gui.main_window import MainWindow


def main() -> None:
    """Capture a populated light and dark window into docs/screenshots."""
    root = Path(__file__).resolve().parents[1]
    target = root / "docs" / "screenshots"
    target.mkdir(parents=True, exist_ok=True)
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(root / "build" / "screenshot-settings"))
    app = QApplication([])
    app.setStyle("Fusion")
    window = MainWindow()
    window.resize(1280, 800)
    window.text_tab.mode.setCurrentIndex(0)
    window.text_tab.editor.setPlainText("HashForge\nOffline hash, HMAC and checksum calculator.")
    window.show()
    deadline = time.monotonic() + 10
    while not window.text_tab.results.results:
        app.processEvents()
        if time.monotonic() > deadline:
            raise TimeoutError("Screenshot calculation did not complete")
        time.sleep(0.01)
    for dark, name in ((False, "light"), (True, "dark")):
        window.dark.setChecked(dark)
        app.processEvents()
        window.grab().save(str(target / f"{name}.png"))
    window.close()
    while any(tab.workers for tab in window.job_tabs):
        app.processEvents()
        time.sleep(0.01)
    window.close()


if __name__ == "__main__":
    main()
