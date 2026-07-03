from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QSoundEffect


def export_complete_sound_path() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "export_complete.wav"


class ExportCompleteSound(QObject):
    """Export tamamlaninca kisa bildirim sesi calar."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._effect = QSoundEffect(self)
        self._effect.setVolume(0.42)

    def play(self) -> None:
        path = export_complete_sound_path()
        if not path.exists():
            return
        self._effect.setSource(QUrl.fromLocalFile(str(path.resolve())))
        self._effect.play()
