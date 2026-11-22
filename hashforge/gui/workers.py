"""Cancellable QThread jobs; workers never access GUI objects."""

from collections.abc import Callable
from threading import Event
from typing import Any

from PySide6.QtCore import QThread, Signal

from hashforge.core.hasher import Cancelled


class Worker(QThread):
    """Run a snapshot of a job and emit progress and a single terminal outcome."""

    progress = Signal(object)
    result = Signal(object)
    error = Signal(str)
    cancelled = Signal()

    def __init__(self, job: Callable[["Worker"], Any]) -> None:
        super().__init__()
        self._job = job
        self._cancel = Event()

    def cancel(self) -> None:
        """Request cooperative cancellation."""
        self._cancel.set()

    def is_cancelled(self) -> bool:
        """Return whether cancellation was requested."""
        return self._cancel.is_set()

    def check_cancelled(self) -> None:
        """Abort between operations when requested."""
        if self.is_cancelled():
            raise Cancelled()

    def run(self) -> None:
        """Execute the job, translating expected failures to user-facing errors."""
        try:
            result = self._job(self)
            self.check_cancelled()
            self.result.emit(result)
        except Cancelled:
            self.cancelled.emit()
        except PermissionError as exc:
            self.error.emit(f"Permission denied or file locked: {exc.filename or exc}")
        except FileNotFoundError as exc:
            self.error.emit(f"File no longer exists: {exc.filename or exc}")
        except Exception as exc:
            self.error.emit(str(exc) or type(exc).__name__)
        finally:
            self._job = lambda worker: None
