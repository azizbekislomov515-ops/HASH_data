"""Debounced text hashing."""

from collections.abc import Callable
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPlainTextEdit

from hashforge.core.hasher import decode_input, hash_bytes
from hashforge.gui.widgets import JobTab
from hashforge.gui.workers import Worker


class TextTab(JobTab):
    """Hash text, hex, or Base64 in the background after a short debounce."""

    def __init__(self, options: Callable) -> None:
        super().__init__(options)
        row = QHBoxLayout()
        self.mode = QComboBox()
        for label, value in (("Text", "text"), ("Hex bytes", "hex"), ("Base64 bytes", "base64")):
            self.mode.addItem(label, value)
        self.encoding = QComboBox()
        for label, value in (("UTF-8", "utf-8"), ("UTF-16LE", "utf-16le"), ("ASCII", "ascii"), ("Latin-1", "latin-1")):
            self.encoding.addItem(label, value)
        self.newline = QComboBox()
        self.newline.addItems(["keep", "LF", "CRLF"])
        for label, widget in (("Input", self.mode), ("Encoding", self.encoding), ("Newlines", self.newline)):
            row.addWidget(QLabel(label))
            row.addWidget(widget)
        row.addStretch()
        self.layout_box.addLayout(row)
        self.editor = QPlainTextEdit()
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.setPlaceholderText("Text to hash")
        self.editor.setMinimumHeight(130)
        self.layout_box.addWidget(self.editor)
        self.add_job_widgets()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.calculate)
        self.editor.textChanged.connect(self.schedule)
        for widget in (self.mode, self.encoding, self.newline):
            widget.currentIndexChanged.connect(self.schedule)

    def snapshot(self) -> tuple[str, str, str, str]:
        """Capture text and decoding settings on the GUI thread."""
        return (self.editor.toPlainText(), self.mode.currentData(),
                self.encoding.currentData(), self.newline.currentText())

    def schedule(self) -> None:
        """Invalidate old results and debounce fresh input."""
        self.invalidate()
        self.timer.start()

    def calculate(self) -> None:
        """Start a background digest of a frozen input snapshot."""
        try:
            algorithms, key = self.options()
        except ValueError as exc:
            self.set_status(str(exc), True)
            return
        snapshot = self.snapshot()
        def job(worker: Worker) -> object:
            return hash_bytes(decode_input(*snapshot), algorithms, key, worker.is_cancelled)
        self.start_job(job)
