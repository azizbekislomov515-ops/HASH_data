"""Main application window, shared algorithm choices, and safe shutdown."""

from pathlib import Path
import sys
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QScrollArea, QSplitter, QStyle,
    QTabWidget, QVBoxLayout, QWidget,
)

from hashforge.core.algorithms import preset, registry
from hashforge.core.hasher import decode_key
from .styles import stylesheet
from .tabs.batch_tab import BatchTab
from .tabs.file_tab import FileTab
from .tabs.text_tab import TextTab
from .tabs.verify_tab import VerifyTab


class MainWindow(QMainWindow):
    """Offline multi-algorithm hash and HMAC workbench."""

    def __init__(self) -> None:
        super().__init__()
        self.settings = QSettings("HashForge", "HashForge")
        self.setWindowTitle("HashForge")
        self.resize(1200, 780)
        self.setMinimumSize(850, 560)
        asset_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
        self.setWindowIcon(QIcon(str(asset_root / "assets" / "icon.ico")))
        self._closing = False
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        top = QHBoxLayout()
        title = QLabel("HashForge")
        title.setStyleSheet("font-size: 23px; font-weight: 600;")
        top.addWidget(title)
        top.addStretch()
        self.dark = QCheckBox("Dark theme")
        self.dark.setChecked(self.settings.value("dark", False, type=bool))
        top.addWidget(self.dark)
        layout.addLayout(top)
        splitter = QSplitter()
        layout.addWidget(splitter, 1)
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        self.presets = QComboBox()
        self.presets.addItems(["Common", "Network/Forensics", "All"])
        sidebar_layout.addWidget(QLabel("Algorithms"))
        sidebar_layout.addWidget(self.presets)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        choices = QWidget()
        choices_layout = QVBoxLayout(choices)
        self.checkboxes: dict[str, QCheckBox] = {}
        saved = self.settings.value("algorithms", list(preset("Common")), type=list)
        available = registry()
        for name, algorithm in available.items():
            row = QHBoxLayout()
            checkbox = QCheckBox(algorithm.label)
            checkbox.setChecked(name in saved)
            self.checkboxes[name] = checkbox
            row.addWidget(checkbox, 1)
            if name in {"md5", "sha1"}:
                warning = QLabel()
                warning.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning).pixmap(16, 16))
                warning.setToolTip("Not collision-resistant, use for integrity checks only")
                checkbox.setToolTip(warning.toolTip())
                row.addWidget(warning)
            choices_layout.addLayout(row)
        choices_layout.addStretch()
        scroll.setWidget(choices)
        sidebar_layout.addWidget(scroll, 1)
        hmac_group = QGroupBox("HMAC")
        hmac_layout = QVBoxLayout(hmac_group)
        self.hmac_enabled = QCheckBox("Enable HMAC")
        self.key_mode = QComboBox()
        for label, value in (("UTF-8 text", "text"), ("Hex", "hex"), ("Base64", "base64")):
            self.key_mode.addItem(label, value)
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("Secret key")
        self.key.setToolTip("Secret keys are never saved. Checksums remain unkeyed.")
        hmac_layout.addWidget(self.hmac_enabled)
        hmac_layout.addWidget(self.key_mode)
        hmac_layout.addWidget(self.key)
        sidebar_layout.addWidget(hmac_group)
        splitter.addWidget(sidebar)
        self.tabs = QTabWidget()
        self.text_tab = TextTab(self.options)
        self.file_tab = FileTab(self.options)
        self.batch_tab = BatchTab(self.options)
        self.verify_tab = VerifyTab(self.options, self.text_tab.snapshot)
        for setting, widget in (("input_mode", self.text_tab.mode),
                                ("encoding", self.text_tab.encoding),
                                ("newline", self.text_tab.newline),
                                ("key_mode", self.key_mode)):
            index = self.settings.value(setting, 0, type=int)
            widget.setCurrentIndex(max(0, min(index, widget.count() - 1)))
        self.batch_tab.recursive.setChecked(self.settings.value("recursive", False, type=bool))
        self.job_tabs = (self.text_tab, self.file_tab, self.batch_tab, self.verify_tab)
        for tab, name in zip(self.job_tabs, ("Text", "File", "Batch / Folder", "Compare / Verify")):
            self.tabs.addTab(tab, name)
        splitter.addWidget(self.tabs)
        splitter.setSizes([245, 955])
        splitter.setStretchFactor(1, 1)
        self.presets.currentTextChanged.connect(self.select_preset)
        for checkbox in self.checkboxes.values():
            checkbox.toggled.connect(self.options_changed)
        self.hmac_enabled.toggled.connect(self.options_changed)
        self.key_mode.currentIndexChanged.connect(self.options_changed)
        self.key.textChanged.connect(self.options_changed)
        self.text_tab.editor.textChanged.connect(self.verify_tab.reset_verdict)
        for widget in (self.text_tab.mode, self.text_tab.encoding, self.text_tab.newline):
            widget.currentIndexChanged.connect(self.verify_tab.reset_verdict)
        self.dark.toggled.connect(self.apply_theme)
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        self.apply_theme()
        self.options_changed()
        self.close_timer = QTimer(self)
        self.close_timer.setInterval(50)
        self.close_timer.timeout.connect(self.finish_close)

    def options(self) -> tuple[tuple[str, ...], bytes | None]:
        """Validate and snapshot shared options without storing the secret key."""
        algorithms = tuple(name for name, checkbox in self.checkboxes.items() if checkbox.isChecked())
        if not algorithms:
            raise ValueError("Select at least one algorithm.")
        key = decode_key(self.key.text(), self.key_mode.currentData()) if self.hmac_enabled.isChecked() else None
        return algorithms, key

    def select_preset(self, name: str) -> None:
        """Apply a preset with a single recalculation."""
        selected = preset(name)
        for algorithm, checkbox in self.checkboxes.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(algorithm in selected)
            checkbox.blockSignals(False)
        self.options_changed()

    def options_changed(self) -> None:
        """Invalidate stale results and schedule live text calculation."""
        self.key.setEnabled(self.hmac_enabled.isChecked())
        self.key_mode.setEnabled(self.hmac_enabled.isChecked())
        self.text_tab.schedule()
        self.file_tab.invalidate()
        self.batch_tab.invalidate()
        self.verify_tab.reset_verdict()

    def apply_theme(self) -> None:
        """Apply the current light/dark style to all application widgets."""
        QApplication.instance().setStyleSheet(stylesheet(self.dark.isChecked()))

    def closeEvent(self, event: QCloseEvent) -> None:
        """Cancel jobs and defer destruction until worker threads have exited."""
        self.text_tab.timer.stop()
        if any(tab.workers for tab in self.job_tabs):
            event.ignore()
            self._closing = True
            for tab in self.job_tabs:
                tab.cancel()
            self.setEnabled(False)
            self.close_timer.start()
            return
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("dark", self.dark.isChecked())
        self.settings.setValue("algorithms", [n for n, c in self.checkboxes.items() if c.isChecked()])
        for setting, widget in (("input_mode", self.text_tab.mode),
                                ("encoding", self.text_tab.encoding),
                                ("newline", self.text_tab.newline),
                                ("key_mode", self.key_mode)):
            self.settings.setValue(setting, widget.currentIndex())
        self.settings.setValue("recursive", self.batch_tab.recursive.isChecked())
        self.settings.sync()
        event.accept()

    def finish_close(self) -> None:
        """Complete deferred shutdown once no worker owns a running thread."""
        if not any(tab.workers for tab in self.job_tabs):
            self.close_timer.stop()
            self.close()
