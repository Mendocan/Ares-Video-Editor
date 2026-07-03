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
        self._pending_play = False
        self._effect.statusChanged.connect(self._on_status_changed)
        path = export_complete_sound_path()
        if path.exists():
            self._effect.setSource(QUrl.fromLocalFile(str(path.resolve())))

    def play(self) -> None:
        if not export_complete_sound_path().exists():
            return
        if not self._effect.source().isValid():
            return
        if self._effect.status() == QSoundEffect.Status.Ready:
            if self._effect.isPlaying():
                self._effect.stop()
            self._effect.play()
            return
        self._pending_play = True

    def _on_status_changed(self) -> None:
        if self._effect.status() != QSoundEffect.Status.Ready or not self._pending_play:
            return
        self._pending_play = False
        if self._effect.isPlaying():
            self._effect.stop()
        self._effect.play()
