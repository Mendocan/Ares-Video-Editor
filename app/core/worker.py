from __future__ import annotations

import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    """
    Worker tarafindan tetiklenecek sinyalleri tanimlar.
    """
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(str)


class Worker(QRunnable):
    """
    Arayuzu dondurmadan arka planda uzun sureli isleri calistiran sinif.
    Ornegin Whisper transkripsiyonu gibi.
    """
    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            # Eger gonderilen fonksiyonda "progress_callback" destegi varsa
            # progress sinyalini baglayarak arayuze mesaj gonderebiliriz.
            if "progress_callback" in self.kwargs:
                self.kwargs["progress_callback"] = self.signals.progress.emit

            result = self.fn(*self.args, **self.kwargs)
        except Exception:
            self.signals.error.emit((Exception, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()
