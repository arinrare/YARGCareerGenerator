"""Background workers (QThread) for long-running core operations."""

from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    """Run a callable on a background thread and emit its result or error.

    The callable must be GUI-free (core logic only); it must not touch Qt
    widgets. Any exception raised is re-emitted via the ``error`` signal so the
    UI can report it.
    """

    result = Signal(object)
    error = Signal(object)  # the exception instance

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            self.result.emit(self._fn(*self._args, **self._kwargs))
        except Exception as exc:  # noqa: BLE001 - forwarded to the UI
            self.error.emit(exc)
