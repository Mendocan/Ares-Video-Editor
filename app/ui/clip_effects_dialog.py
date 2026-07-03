from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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

from app.core.clip_effects import XFADE_TRANSITIONS, ClipEffects
from app.ui.app_theme import TEXT_MUTED


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
        info.setStyleSheet(f"color: {TEXT_MUTED};")
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

        transition_group = QGroupBox("Gecis Efekti (bir onceki klipten gecerken)")
        t_form = QFormLayout(transition_group)

        self.transition_combo = QComboBox()
        self.transition_combo.addItems(list(XFADE_TRANSITIONS.keys()))

        self.transition_duration_spin = QSpinBox()
        self.transition_duration_spin.setRange(100, 3000)
        self.transition_duration_spin.setSingleStep(100)
        self.transition_duration_spin.setSuffix(" ms")

        t_form.addRow("Efekt", self.transition_combo)
        t_form.addRow("Sure", self.transition_duration_spin)
        layout.addWidget(transition_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_effects(self) -> None:
        self.speed_spin.setValue(self.effects.speed)
        self.fade_in_spin.setValue(self.effects.fade_in_ms)
        self.fade_out_spin.setValue(self.effects.fade_out_ms)
        self.volume_spin.setValue(self.effects.volume)
        if self.effects.transition_in in XFADE_TRANSITIONS:
            self.transition_combo.setCurrentText(self.effects.transition_in)
        self.transition_duration_spin.setValue(self.effects.transition_duration_ms)

    def updated_effects(self) -> ClipEffects:
        return ClipEffects(
            speed=self.speed_spin.value(),
            fade_in_ms=self.fade_in_spin.value(),
            fade_out_ms=self.fade_out_spin.value(),
            volume=self.volume_spin.value(),
            transition_in=self.transition_combo.currentText(),
            transition_duration_ms=self.transition_duration_spin.value(),
        )
