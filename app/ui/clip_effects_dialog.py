from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from app.core.clip_effects import ClipEffects


class ClipEffectsDialog(QDialog):
    def __init__(self, effects: ClipEffects | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Klip Efektleri")
        self.resize(420, 280)
        self.effects = effects or ClipEffects()
        self._build_ui()
        self._load_effects()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        info = QLabel(
            "Secili video/ses klibine hiz, solma ve ses seviyesi uygulanir. "
            "Export sirasinda FFmpeg ile islenir."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #94A3B8;")
        layout.addWidget(info)

        group = QGroupBox("Efekt Ayarlari")
        form = QFormLayout(group)

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.25, 4.0)
        self.speed_spin.setSingleStep(0.25)
        self.speed_spin.setSuffix(" x")

        self.fade_in_spin = QSpinBox()
        self.fade_in_spin.setRange(0, 5000)
        self.fade_in_spin.setSuffix(" ms")

        self.fade_out_spin = QSpinBox()
        self.fade_out_spin.setRange(0, 5000)
        self.fade_out_spin.setSuffix(" ms")

        self.volume_spin = QDoubleSpinBox()
        self.volume_spin.setRange(0.0, 2.0)
        self.volume_spin.setSingleStep(0.1)

        form.addRow("Hiz", self.speed_spin)
        form.addRow("Fade In", self.fade_in_spin)
        form.addRow("Fade Out", self.fade_out_spin)
        form.addRow("Ses Seviyesi", self.volume_spin)
        layout.addWidget(group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_effects(self) -> None:
        self.speed_spin.setValue(self.effects.speed)
        self.fade_in_spin.setValue(self.effects.fade_in_ms)
        self.fade_out_spin.setValue(self.effects.fade_out_ms)
        self.volume_spin.setValue(self.effects.volume)

    def updated_effects(self) -> ClipEffects:
        return ClipEffects(
            speed=self.speed_spin.value(),
            fade_in_ms=self.fade_in_spin.value(),
            fade_out_ms=self.fade_out_spin.value(),
            volume=self.volume_spin.value(),
        )
