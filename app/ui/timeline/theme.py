from __future__ import annotations

from PySide6.QtGui import QColor

from app.core.timeline import TRACK_AUDIO, TRACK_SUBTITLE, TRACK_VIDEO

# ─────────────────────────────────────────────────────────────────────────────
# Colour palette
# ─────────────────────────────────────────────────────────────────────────────
C_BG_DARK   = QColor("#0D1117")
C_BG_MID    = QColor("#131922")
C_BG_PANEL  = QColor("#161D2B")
C_BG_TRACK  = QColor("#1B2333")
C_BORDER    = QColor("#252F42")
C_BORDER2   = QColor("#2A3548")
C_TEXT_DIM  = QColor("#475569")
C_TEXT_MID  = QColor("#64748B")
C_TEXT      = QColor("#94A3B8")
C_TEXT_LT   = QColor("#CBD5E1")
C_TEXT_BRT  = QColor("#F1F5F9")
C_PLAYHEAD  = QColor("#F97316")
C_PLAYHEAD2 = QColor("#FB923C")
C_ACCENT_V  = QColor("#3B82F6")
C_ACCENT_A  = QColor("#10B981")
C_ACCENT_S  = QColor("#8B5CF6")
C_SELECT    = QColor("#F8FAFC")
C_TICK_MAJ  = QColor("#475569")
C_TICK_MIN  = QColor("#2D3A4F")

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
