"""Folder discovery and batch calculation off the GUI thread."""

from collections.abc import Callable
import os
from pathlib import Path
import time
from typing import Any
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QFileDialog, QHBoxLayout, QLabel, QPushButton

from hashforge.core.hasher import hash_file
from hashforge.gui.widgets import JobTab
from hashforge.gui.workers import Worker


class BatchTab(JobTab):
    """Compute batches with individual file failures and aggregate progress."""

    def __init__(self, options: Callable) -> None:
        super().__init__(options)
        self.paths: tuple[str, ...] = ()
        self.folder = ""
        row = QHBoxLayout()
        files = QPushButton("Select files")
        folder = QPushButton("Select folder")
        self.recursive = QCheckBox("Recursive")
        calculate = QPushButton("Calculate batch")
        for widget in (files, folder, self.recursive, calculate):
            row.addWidget(widget)
        row.addStretch()
        self.layout_box.addLayout(row)
        self.selection = QLabel("No files selected")
        self.selection.setTextFormat(Qt.TextFormat.PlainText)
        self.selection.setWordWrap(True)
        self.layout_box.addWidget(self.selection)
        self.add_job_widgets()
        files.clicked.connect(self.select_files)
        folder.clicked.connect(self.select_folder)
        calculate.clicked.connect(self.calculate)
        self.recursive.toggled.connect(self.invalidate)

    def select_files(self) -> None:
        """Choose multiple arbitrary files."""
        paths, _ = QFileDialog.getOpenFileNames(self, "Select files", "", "All files (*)")
        if paths:
            self.invalidate()
            self.paths, self.folder = tuple(paths), ""
            self.selection.setText(f"{len(paths)} files selected")

    def select_folder(self) -> None:
        """Select a folder; enumeration happens only in a worker."""
        folder = QFileDialog.getExistingDirectory(self, "Select folder")
        if folder:
            self.invalidate()
            self.folder, self.paths = folder, ()
            self.selection.setText(folder)

    def calculate(self) -> None:
        """Run discovery and hashing as one cancellable job."""
        try:
            algorithms, key = self.options()
            if not self.paths and not self.folder:
                raise ValueError("Select files or a folder first.")
        except ValueError as exc:
            self.set_status(str(exc), True)
            return
        paths, folder, recursive = self.paths, self.folder, self.recursive.isChecked()
        def job(worker: Worker) -> object:
            files = list(paths)
            errors: list[str] = []
            if folder:
                def walk_error(exc: OSError) -> None:
                    errors.append(str(exc))
                for root, dirs, names in os.walk(folder, onerror=walk_error, followlinks=False):
                    worker.check_cancelled()
                    for name in sorted(names):
                        path = Path(root) / name
                        if not path.is_symlink():
                            files.append(str(path))
                    if not recursive:
                        break
            sizes = []
            for path in files:
                worker.check_cancelled()
                try:
                    sizes.append((path, Path(path).stat().st_size))
                except OSError as exc:
                    errors.append(f"{path}: {exc}")
            total = sum(size for _, size in sizes)
            completed = 0
            start = time.monotonic()
            results = []
            for path, size in sizes:
                worker.check_cancelled()
                try:
                    results.extend(hash_file(path, algorithms, key, cancelled=worker.is_cancelled,
                        progress=lambda done, elapsed: worker.progress.emit(
                            (completed + done, total, time.monotonic() - start, Path(path).name))))
                except OSError as exc:
                    errors.append(f"{path}: {exc}")
                completed += size
            return results, errors
        self.start_job(job, self.receive)

    def receive(self, value: Any) -> None:
        """Keep successful files and make partial failures explicit."""
        results, errors = value
        self.results.set_results(results)
        if errors:
            self.set_status(f"{len(errors)} file error(s):\n" + "\n".join(errors[:5]), True)
            self.status.setToolTip("\n".join(errors))
        elif not results:
            self.set_status("No files found.")
