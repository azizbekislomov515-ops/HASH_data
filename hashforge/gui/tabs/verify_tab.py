"""Constant-time verification with explicit digest-length ambiguity."""

from collections.abc import Callable
from pathlib import Path
from typing import Any
from PySide6.QtWidgets import QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton

from hashforge.core.algorithms import registry
from hashforge.core.hasher import decode_input, detect_algorithms, hash_bytes, hash_file, matches
from hashforge.gui.widgets import JobTab
from hashforge.gui.workers import Worker


class VerifyTab(JobTab):
    """Verify a file or the current text tab using one chosen algorithm."""

    def __init__(self, options: Callable, text_snapshot: Callable) -> None:
        super().__init__(options)
        self.text_snapshot = text_snapshot
        self.expected = QLineEdit()
        self.expected.setPlaceholderText("Expected hexadecimal digest")
        self.layout_box.addWidget(self.expected)
        row = QHBoxLayout()
        self.source = QComboBox()
        self.source.addItems(["File", "Text tab"])
        self.algorithm = QComboBox()
        row.addWidget(self.source)
        row.addWidget(self.algorithm, 1)
        verify = QPushButton("Verify")
        row.addWidget(verify)
        self.layout_box.addLayout(row)
        path_row = QHBoxLayout()
        self.path = QLineEdit()
        self.path.setPlaceholderText("File path")
        browse = QPushButton("Browse file")
        path_row.addWidget(self.path, 1)
        path_row.addWidget(browse)
        self.layout_box.addLayout(path_row)
        self.candidates = QLabel("Enter an expected digest")
        self.candidates.setWordWrap(True)
        self.verdict = QLabel("Not verified")
        self.layout_box.addWidget(self.candidates)
        self.layout_box.addWidget(self.verdict)
        self.add_job_widgets()
        self.expected.textChanged.connect(self.detect)
        self.path.textChanged.connect(self.reset_verdict)
        self.algorithm.currentIndexChanged.connect(self.reset_verdict)
        self.source.currentIndexChanged.connect(self.reset_verdict)
        browse.clicked.connect(self.browse)
        verify.clicked.connect(self.verify)

    def reset_verdict(self) -> None:
        """Clear a verdict whenever its inputs change."""
        self.invalidate()
        self.verdict.setText("Not verified")
        self.verdict.setProperty("status", "")
        self.verdict.style().unpolish(self.verdict)
        self.verdict.style().polish(self.verdict)

    def detect(self) -> None:
        """Offer every matching digest size without assuming unique identification."""
        self.reset_verdict()
        previous = self.algorithm.currentData()
        self.algorithm.clear()
        available = registry()
        names = detect_algorithms(self.expected.text())
        for name in names:
            self.algorithm.addItem(available[name].label, name)
        if previous in names:
            self.algorithm.setCurrentIndex(names.index(previous))
        elif "sha256" in names:
            self.algorithm.setCurrentIndex(names.index("sha256"))
        self.candidates.setText(
            "Several algorithms have this length; select the expected algorithm." if len(names) > 1
            else "Algorithm detected" if names else "Invalid or unsupported hexadecimal digest length"
        )

    def browse(self) -> None:
        """Select a verification file."""
        path, _ = QFileDialog.getOpenFileName(self, "Verify file", "", "All files (*)")
        if path:
            self.path.setText(path)

    def verify(self) -> None:
        """Hash a snapshot and compare digest bytes using compare_digest."""
        self.reset_verdict()
        try:
            _, key = self.options()
            algorithm = self.algorithm.currentData()
            if not algorithm:
                raise ValueError("Enter a valid expected hexadecimal digest.")
            is_file = self.source.currentIndex() == 0
            path = self.path.text()
            if is_file and not path:
                raise ValueError("Select a file first.")
        except ValueError as exc:
            self.set_status(str(exc), True)
            return
        expected = self.expected.text()
        snapshot = self.text_snapshot()
        def job(worker: Worker) -> object:
            if is_file:
                total = Path(path).stat().st_size
                results = hash_file(path, [algorithm], key, cancelled=worker.is_cancelled,
                    progress=lambda done, elapsed: worker.progress.emit((done, total, elapsed, Path(path).name)))
            else:
                results = hash_bytes(decode_input(*snapshot), [algorithm], key, worker.is_cancelled)
            return results, matches(results[0], expected)
        self.start_job(job, self.receive)

    def receive(self, value: Any) -> None:
        """Display an unmistakable text verdict as well as color."""
        results, match = value
        self.results.set_results(results)
        self.verdict.setText("MATCH" if match else "MISMATCH")
        self.verdict.setProperty("status", "match" if match else "mismatch")
        self.verdict.style().unpolish(self.verdict)
        self.verdict.style().polish(self.verdict)
