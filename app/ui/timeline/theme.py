from __future__ import annotations

from PySide6.QtGui import QColor

from app.core.timeline import TRACK_AUDIO, TRACK_SUBTITLE, TRACK_VIDEO
from app.ui.app_theme import (
    ACCENT,
    ACCENT_BRIGHT,
    BG_HOVER,
    BORDER,
    BORDER_DARK,
    COLOR_PLAYHEAD,
    COLOR_SUCCESS,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TL_BG_DARK,
    TL_BG_MID,
    TL_BG_PANEL,
    TL_BG_TRACK,
)

# ─────────────────────────────────────────────────────────────────────────────
# Metalik gri timeline paleti
# ─────────────────────────────────────────────────────────────────────────────
C_BG_DARK   = QColor(TL_BG_DARK)
C_BG_MID    = QColor(TL_BG_MID)
C_BG_PANEL  = QColor(TL_BG_PANEL)
C_BG_TRACK  = QColor(TL_BG_TRACK)
C_BORDER    = QColor(BORDER_DARK)
C_BORDER2   = QColor(BORDER)
C_TEXT_DIM  = QColor(TEXT_MUTED)
C_TEXT_MID  = QColor(TEXT_SECONDARY)
C_TEXT      = QColor(TEXT_SECONDARY)
C_TEXT_LT   = QColor(TEXT_PRIMARY)
C_TEXT_BRT  = QColor(TEXT_PRIMARY)
C_PLAYHEAD  = QColor(COLOR_PLAYHEAD)
C_PLAYHEAD2 = QColor("#E07020")
C_ACCENT_V  = QColor(ACCENT_BRIGHT)
C_ACCENT_A  = QColor(COLOR_SUCCESS)
C_ACCENT_S  = QColor("#5A4A8A")
C_SELECT    = QColor(TEXT_PRIMARY)
C_TICK_MAJ  = QColor(TEXT_MUTED)
C_TICK_MIN  = QColor(BG_HOVER)

TRACK_COLORS = {
    TRACK_VIDEO: C_ACCENT_V,
    TRACK_AUDIO: C_ACCENT_A,
    TRACK_SUBTITLE: C_ACCENT_S,
}

TRACK_LABELS = {
    TRACK_VIDEO: "V1",
    TRACK_AUDIO: "A1",
    TRACK_SUBTITLE: "S1",
}
