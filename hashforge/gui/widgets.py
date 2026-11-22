"""Shared result table and asynchronous job lifecycle."""

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QHBoxLayout,
    QHeaderView, QLabel, QMessageBox, QProgressBar, QPushButton,
    QStyle, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget,
)

from hashforge.core.export import save_results
from hashforge.core.hasher import Result
from .workers import Worker


class Results(QWidget):
    """Read-only results with encodings, per-row copy, and export actions."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[Result] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        toolbar = QHBoxLayout()
        self.encoding = QComboBox()
        self.encoding.addItems(["hex", "base64", "decimal"])
        self.uppercase = QCheckBox("Uppercase hex")
        toolbar.addWidget(QLabel("Output"))
        toolbar.addWidget(self.encoding)
        toolbar.addWidget(self.uppercase)
        toolbar.addStretch()
        copy = QPushButton("Copy all")
        save = QPushButton("Save results")
        save.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        toolbar.addWidget(copy)
        toolbar.addWidget(save)
        layout.addLayout(toolbar)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["File", "Size", "Algorithm", "Hash", ""])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 155)
        self.table.setColumnWidth(1, 85)
        self.table.setColumnWidth(2, 145)
        self.table.setColumnWidth(4, 44)
        layout.addWidget(self.table)
        self.encoding.currentTextChanged.connect(self.render)
        self.uppercase.toggled.connect(self.render)
        copy.clicked.connect(self.copy_all)
        save.clicked.connect(self.save)

    def set_results(self, results: list[Result]) -> None:
        """Replace displayed results."""
        self.results = results
        self.render()

    def render(self) -> None:
        """Render the selected encoding; decimal applies only to checksums."""
        from pathlib import Path
        self.table.setRowCount(len(self.results))
        for row, result in enumerate(self.results):
            value = result.formatted(self.encoding.currentText(), self.uppercase.isChecked())
            fields = (Path(result.source).name, f"{result.size:,}", result.label, value)
            for column, text in enumerate(fields):
                item = QTableWidgetItem(text)
                item.setToolTip(result.source if column == 0 else text)
                self.table.setItem(row, column, item)
            button = QToolButton()
            button.setText("Copy")
            button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
            button.setToolTip("Copy this digest")
            button.clicked.connect(lambda checked=False, v=value: QApplication.clipboard().setText(v))
            self.table.setCellWidget(row, 4, button)

    def copy_all(self) -> None:
        """Copy all rows using the displayed encoding."""
        QApplication.clipboard().setText("\n".join(
            f"{r.label}: {r.formatted(self.encoding.currentText(), self.uppercase.isChecked())}  {r.source}"
            for r in self.results
        ))

    def save(self) -> None:
        """Export a snapshot in a user-selected format."""
        if not self.results:
            return
        filters = "JSON (*.json);;CSV (*.csv);;Text (*.txt);;Checksum manifest (*.sha256 *.md5 *.sum)"
        path, selected = QFileDialog.getSaveFileName(self, "Save results", "", filters)
        if not path:
            return
        format = "sum" if selected.startswith("Checksum") else selected.split()[0].lower()
        if format == "text":
            format = "txt"
        results = self.results
        if format == "sum":
            from PySide6.QtWidgets import QInputDialog
            options = sorted({r.algorithm for r in results if not r.is_hmac and not r.checksum})
            if not options:
                QMessageBox.warning(self, "Cannot export", "Select an ordinary file hash for a checksum manifest.")
                return
            choice, ok = QInputDialog.getItem(self, "Checksum algorithm", "Algorithm", options, 0, False)
            if not ok:
                return
            results = [r for r in results if r.algorithm == choice and not r.is_hmac]
        try:
            save_results(path, results, format)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Export failed", str(exc))


class JobTab(QWidget):
    """Own one active job, replacing stale work without blocking the event loop."""

    busy_changed = Signal(bool)

    def __init__(self, options: Callable[[], tuple[tuple[str, ...], bytes | None]]) -> None:
        super().__init__()
        self.options = options
        self.workers: list[Worker] = []
        self.generation = 0
        self.layout_box = QVBoxLayout(self)
        self.status = QLabel("Ready")
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)
        self.results = Results()

    def add_job_widgets(self) -> None:
        """Append progress, status, and results after tab-specific controls."""
        row = QHBoxLayout()
        row.addWidget(self.progress, 1)
        row.addWidget(self.cancel_button)
        self.layout_box.addLayout(row)
        self.layout_box.addWidget(self.status)
        self.layout_box.addWidget(self.results, 1)

    def set_status(self, text: str, error: bool = False) -> None:
        """Update a wrapped status label."""
        self.status.setText(text)
        self.status.setProperty("status", "error" if error else "")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def cancel(self) -> None:
        """Cancel active work and invalidate pending signals."""
        self.generation += 1
        for worker in self.workers:
            worker.cancel()
        self.cancel_button.setEnabled(False)
        self.progress.setValue(0)
        self.set_status("Cancelled")
        self.busy_changed.emit(False)

    def invalidate(self) -> None:
        """Clear results when their input or options change."""
        self.cancel()
        self.results.set_results([])
        self.set_status("Ready")

    def start_job(self, job: Callable[[Worker], Any],
                  receive: Callable[[Any], None] | None = None) -> None:
        """Start a job and discard results from replaced jobs."""
        self.invalidate()
        generation = self.generation
        worker = Worker(job)
        self.workers.append(worker)
        self.cancel_button.setEnabled(True)
        self.busy_changed.emit(True)
        self.set_status("Working...")
        def complete(value: Any) -> None:
            if generation == self.generation:
                self.cancel_button.setEnabled(False)
                self.progress.setValue(1000)
                self.set_status("Complete")
                (receive or self.results.set_results)(value)
                self.busy_changed.emit(False)
        def failure(message: str) -> None:
            if generation == self.generation:
                self.set_status(message, True)
                self.cancel_button.setEnabled(False)
                self.busy_changed.emit(False)
        worker.result.connect(complete)
        worker.error.connect(failure)
        worker.progress.connect(lambda value: self.on_progress(value) if generation == self.generation else None)
        worker.finished.connect(lambda: self._release(worker))
        worker.start()

    def _release(self, worker: Worker) -> None:
        self.workers.remove(worker)
        worker.deleteLater()

    def on_progress(self, progress: tuple[int, int, float, str]) -> None:
        """Display processed bytes, speed, ETA, and the current source."""
        done, total, elapsed, name = progress
        speed = done / max(elapsed, 0.001)
        eta = max(0, total - done) / speed if speed else 0
        self.progress.setValue(int(min(1, done / max(1, total)) * 1000))
        self.set_status(f"{name} | {done / 1048576:.1f} / {total / 1048576:.1f} MiB | "
                        f"{speed / 1048576:.1f} MiB/s | ETA {eta:.0f}s")
