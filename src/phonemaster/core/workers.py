"""Thread workers for running blocking operations off the UI thread."""

import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThread, Signal, Slot


class WorkerSignals(QObject):
    """Signals emitted by Worker runnables."""
    started = Signal()
    progress = Signal(int)           # 0-100
    status = Signal(str)             # Status text
    result = Signal(object)          # Return value
    error = Signal(str)              # Error message
    finished = Signal()


class Worker(QRunnable):
    """
    Generic worker that runs a callable in the thread pool.

    Usage:
        worker = Worker(some_function, arg1, arg2, kwarg1=val)
        worker.signals.result.connect(handle_result)
        worker.signals.error.connect(handle_error)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        self.signals.started.emit()
        try:
            result = self.fn(*self.args, **self.kwargs, 
                           progress_callback=self.signals.progress,
                           status_callback=self.signals.status)
            self.signals.result.emit(result)
        except TypeError:
            # fn doesn't accept callbacks — call without them
            try:
                result = self.fn(*self.args, **self.kwargs)
                self.signals.result.emit(result)
            except Exception as e:
                self.signals.error.emit(f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
        except Exception as e:
            self.signals.error.emit(f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
        finally:
            self.signals.finished.emit()


class DevicePollingThread(QThread):
    """Background thread that polls for connected devices at regular intervals."""

    devices_updated = Signal(list)

    def __init__(self, poll_fn: Callable, interval_ms: int = 3000, parent=None):
        super().__init__(parent)
        self.poll_fn = poll_fn
        self.interval_ms = interval_ms
        self._running = True

    def run(self):
        while self._running:
            try:
                devices = self.poll_fn()
                self.devices_updated.emit(devices)
            except Exception:
                self.devices_updated.emit([])
            self.msleep(self.interval_ms)

    def stop(self):
        self._running = False
        self.wait(5000)
