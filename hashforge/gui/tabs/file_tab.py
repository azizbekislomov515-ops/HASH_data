"""Raw-byte single-file hashing with metadata and drag-and-drop."""

from collections.abc import Callable
from typing import Any
from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton

from hashforge.core.filetypes import metadata
from hashforge.core.hasher import hash_file
from hashforge.gui.widgets import JobTab
from hashforge.gui.workers import Worker


class FileTab(JobTab):
    """Stream files once for every selected algorithm."""

    def __init__(self, options: Callable) -> None:
        super().__init__(options)
        self.setAcceptDrops(True)
        row = QHBoxLayout()
        self.path = QLineEdit()
        self.path.setPlaceholderText("File path")
        browse = QPushButton("Browse file")
        calculate = QPushButton("Calculate")
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        row.addWidget(calculate)
        self.layout_box.addLayout(row)
        self.info = QLabel("No file selected")
        self.info.setWordWrap(True)
        self.info.setTextFormat(Qt.TextFormat.PlainText)
        self.info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.layout_box.addWidget(self.info)
        self.add_job_widgets()
        browse.clicked.connect(self.browse)
        calculate.clicked.connect(self.calculate)
        self.path.returnPressed.connect(self.calculate)
        self.path.textChanged.connect(self.changed)

    def changed(self) -> None:
        """Remove metadata and results belonging to a previous path."""
        self.invalidate()
        self.info.setText("No file calculated")

    def browse(self) -> None:
        """Pick any file type."""
        path, _ = QFileDialog.getOpenFileName(self, "Select file", "", "All files (*)")
        if path:
            self.path.setText(path)
            self.calculate()

    def calculate(self) -> None:
        """Read metadata and compute digests on a worker thread."""
        try:
            algorithms, key = self.options()
            path = self.path.text()
            if not path:
                raise ValueError("Select a file first.")
        except ValueError as exc:
            self.set_status(str(exc), True)
            return
        def job(worker: Worker) -> object:
            info = metadata(path)
            worker.progress.emit(info)
            results = hash_file(path, algorithms, key, cancelled=worker.is_cancelled,
                                progress=lambda done, elapsed: worker.progress.emit(
                                    (done, info["size"], elapsed, info["name"])))
            return info, results
        self.start_job(job, self.receive)

    def receive(self, value: Any) -> None:
        """Display metadata together with the completed digest snapshot."""
        info, results = value
        self.show_metadata(info)
        self.results.set_results(results)

    def show_metadata(self, info: dict[str, str | int]) -> None:
        """Show file information before a long calculation completes."""
        self.info.setText(f"{info['name']}\n{info['path']}\n{info['size']:,} bytes | "
                          f"{info['mime']} | Modified: {info['modified']}")

    def on_progress(self, progress: Any) -> None:
        """Accept initial metadata or subsequent byte progress."""
        if isinstance(progress, dict):
            self.show_metadata(progress)
        else:
            super().on_progress(progress)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept a single local URL."""
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Calculate the dropped path without checking it on the GUI thread."""
        self.path.setText(event.mimeData().urls()[0].toLocalFile())
        self.calculate()
        event.acceptProposedAction()
