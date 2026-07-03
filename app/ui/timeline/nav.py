from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import (
    QColor, QPainter, QPen, QBrush, QFont, QWheelEvent, QMouseEvent, QLinearGradient,
)
from PySide6.QtWidgets import QLabel, QScrollArea, QWidget, QSizePolicy

from app.core.timeline import TRACK_AUDIO, TRACK_VIDEO
from app.ui.app_theme import (
    ACCENT,
    BG_PRESSED,
    BORDER_DARK,
    COLOR_DANGER,
    COLOR_PLAYHEAD,
    COLOR_WARNING,
    TEXT_ON_ACCENT,
    TEXT_PRIMARY,
    TL_BG_MINI,
    TL_HEADER_GRAD_BOTTOM,
    TL_HEADER_GRAD_TOP,
    TL_SCROLL,
    TL_STATUS,
)
from app.ui.timeline.theme import C_BORDER, C_PLAYHEAD, C_TEXT, C_TEXT_LT, TRACK_COLORS, TRACK_LABELS

class TrackHeader(QWidget):
    """Tek bir track'in sol header'i (etiket + mute/solo)."""

    track_clicked = Signal(str, bool)

    HEADER_WIDTH = 52

    def __init__(self, track_type: str, height: int, parent=None) -> None:
        super().__init__(parent)
        self.track_type = track_type
        self.setFixedSize(self.HEADER_WIDTH, height)
        self._muted  = False
        self._solo   = False
        accent = TRACK_COLORS.get(track_type, C_TEXT)
        self._accent = accent

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0, QColor(TL_HEADER_GRAD_TOP))
        grad.setColorAt(1, QColor(TL_HEADER_GRAD_BOTTOM))
        painter.fillRect(0, 0, w, h, grad)

        # Right border
        painter.setPen(QPen(C_BORDER, 1))
        painter.drawLine(w - 1, 0, w - 1, h)

        # Bottom border
        painter.setPen(QPen(C_BORDER, 1))
        painter.drawLine(0, h - 1, w - 1, h - 1)

        # Left accent stripe
        painter.fillRect(0, 0, 3, h, self._accent)

        # Track label
        label = TRACK_LABELS.get(self.track_type, "?")
        painter.setPen(C_TEXT_LT)
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        fm = painter.fontMetrics()
        painter.drawText((w - fm.horizontalAdvance(label)) // 2 + 2, h // 2 - 8, label)

        # Mute button (M)
        mx, my = 6, h // 2 + 2
        bw, bh = 17, 13
        mute_color = QColor(COLOR_DANGER) if self._muted else QColor(BG_PRESSED)
        painter.setPen(Qt.NoPen)
        painter.setBrush(mute_color)
        painter.drawRoundedRect(mx, my, bw, bh, 3, 3)
        painter.setPen(QColor(TEXT_ON_ACCENT) if self._muted else C_TEXT)
        painter.setFont(QFont("Segoe UI", 6, QFont.Bold))
        painter.drawText(mx + 4, my + bh - 3, "M")

        # Solo button (S)
        sx2 = mx + bw + 4
        solo_color = QColor(COLOR_WARNING) if self._solo else QColor(BG_PRESSED)
        painter.setPen(Qt.NoPen)
        painter.setBrush(solo_color)
        painter.drawRoundedRect(sx2, my, bw, bh, 3, 3)
        painter.setPen(QColor(TEXT_PRIMARY) if self._solo else C_TEXT)
        painter.setFont(QFont("Segoe UI", 6, QFont.Bold))
        painter.drawText(sx2 + 4, my + bh - 3, "S")

    def mousePressEvent(self, event) -> None:
        w, h = self.width(), self.height()
        bw, bh = 17, 13
        mx, my = 6, h // 2 + 2
        sx2 = mx + bw + 4
        x, y = event.pos().x(), event.pos().y()
        if mx <= x <= mx + bw and my <= y <= my + bh:
            self._muted = not self._muted
            self.update()
            return
        if sx2 <= x <= sx2 + bw and my <= y <= my + bh:
            self._solo = not self._solo
            self.update()
            return
        additive = bool(event.modifiers() & Qt.ControlModifier)
        self.track_clicked.emit(self.track_type, additive)

class MiniTimeline(QWidget):
    """Tüm timeline'ın küçük haritası; sürüklenebilir viewport penceresi."""

    seek_requested    = Signal(float)   # normalised 0..1
    scroll_requested  = Signal(float)   # normalised 0..1

    HEIGHT = 24

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(self.HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._view_start: float = 0.0   # normalised
        self._view_end:   float = 1.0
        self._playhead:   float = 0.0   # normalised
        self._clips: list[tuple[float, float, str]] = []  # (start_n, end_n, track)
        self._dragging = False
        self._drag_offset: float = 0.0
        self.setCursor(Qt.ArrowCursor)

    def update_state(
        self,
        view_start_n: float,
        view_end_n:   float,
        playhead_n:   float,
        clips: list[tuple[float, float, str]],
    ) -> None:
        self._view_start = view_start_n
        self._view_end   = view_end_n
        self._playhead   = playhead_n
        self._clips      = clips
        self.update()

    def _n_to_x(self, n: float) -> int:
        return int(n * self.width())

    def _x_to_n(self, x: int) -> float:
        return max(0.0, min(1.0, x / max(1, self.width())))

    # ── Input ──────────────────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton:
            return
        n = self._x_to_n(event.pos().x())
        # Click inside viewport window → drag it
        if self._view_start <= n <= self._view_end:
            self._dragging    = True
            self._drag_offset = n - self._view_start
            self.setCursor(Qt.ClosedHandCursor)
        else:
            # Jump — centre viewport on click
            half = (self._view_end - self._view_start) / 2.0
            start = max(0.0, min(1.0 - 2 * half, n - half))
            self.scroll_requested.emit(start)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        n = self._x_to_n(event.pos().x())
        if self._dragging:
            span  = self._view_end - self._view_start
            start = max(0.0, min(1.0 - span, n - self._drag_offset))
            self.scroll_requested.emit(start)
        else:
            if self._view_start <= n <= self._view_end:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._dragging = False
        self.setCursor(Qt.ArrowCursor)

    # ── Paint ──────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor(TL_BG_MINI))
        painter.setPen(QPen(C_BORDER, 1))
        painter.drawLine(0, 0, w, 0)

        # Mini clips
        LANE_H = 4
        for s_n, e_n, track in self._clips:
            x1 = self._n_to_x(s_n)
            x2 = self._n_to_x(e_n)
            cw = max(2, x2 - x1)
            color = TRACK_COLORS.get(track, C_TEXT)
            if track == TRACK_VIDEO:
                cy = 6
            elif track == TRACK_AUDIO:
                cy = 12
            else:
                cy = 18
            painter.fillRect(x1, cy, cw, LANE_H, color.darker(120))

        # Viewport window
        x1 = self._n_to_x(self._view_start)
        x2 = self._n_to_x(self._view_end)
        vw = max(4, x2 - x1)
        painter.fillRect(x1, 0, vw, h, QColor(255, 255, 255, 40))
        painter.setPen(QPen(QColor(60, 66, 74, 140), 1))
        painter.drawRect(x1, 0, vw - 1, h - 1)

        # Playhead
        px = self._n_to_x(self._playhead)
        painter.setPen(QPen(QColor(COLOR_PLAYHEAD), 2))
        painter.drawLine(px, 0, px, h)


# ─────────────────────────────────────────────────────────────────────────────
# TimecodeLabel — toolbar'daki HH:MM:SS:ff göstergesi
# ─────────────────────────────────────────────────────────────────────────────

class TimecodeLabel(QLabel):
    def __init__(self, parent=None) -> None:
        super().__init__("00:00:00", parent)
        self.setFont(QFont("Consolas", 9))
        self.setStyleSheet(
            f"color: {TEXT_PRIMARY};"
            "background: transparent;"
            "border: none;"
            "padding: 0px 4px;"
            "letter-spacing: 0.5px;"
        )
        self.setAlignment(Qt.AlignCenter)
        self.setFixedWidth(88)

    def set_ms(self, ms: int) -> None:
        s, _ = divmod(max(0, ms), 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        self.setText(f"{h:02d}:{m:02d}:{s:02d}")


# ─────────────────────────────────────────────────────────────────────────────
# TimelineScrollArea — Ctrl+scroll zoom, scroll kaydırma
# ─────────────────────────────────────────────────────────────────────────────

class TimelineScrollArea(QScrollArea):
    zoom_changed   = Signal(float)   # new zoom level
    scroll_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._zoom_level: float = 1.0
        self.setStyleSheet(
            f"QScrollArea {{"
            f"  background-color: {TL_SCROLL};"
            f"  border: none;"
            f"}}"
            f"QScrollBar:horizontal {{"
            f"  background: {TL_STATUS};"
            f"  height: 8px;"
            f"  margin: 0px;"
            f"  border-radius: 4px;"
            f"}}"
            f"QScrollBar::handle:horizontal {{"
            f"  background: {BORDER_DARK};"
            f"  border-radius: 4px;"
            f"  min-width: 30px;"
            f"}}"
            f"QScrollBar::handle:horizontal:hover {{"
            f"  background: {ACCENT};"
            f"}}"
            f"QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{"
            f"  width: 0px;"
            f"}}"
            f"QScrollBar:vertical {{ width: 0px; }}"
        )
        self.horizontalScrollBar().valueChanged.connect(lambda _: self.scroll_changed.emit())

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if event.modifiers() & Qt.ControlModifier:
            # Zoom
            factor = 1.15 if delta > 0 else (1 / 1.15)
            new_zoom = max(0.25, min(8.0, self._zoom_level * factor))
            if abs(new_zoom - self._zoom_level) > 0.001:
                # Keep mouse position stable
                mouse_x   = event.position().x()
                sb        = self.horizontalScrollBar()
                old_scroll = sb.value()
                old_zoom   = self._zoom_level
                self._zoom_level = new_zoom
                self.zoom_changed.emit(new_zoom)
                # After zoom the content width changes; adjust scroll
                QTimer.singleShot(0, lambda: self._adjust_scroll_after_zoom(
                    mouse_x, old_scroll, old_zoom, new_zoom
                ))
            event.accept()
        else:
            # Horizontal scroll
            sb = self.horizontalScrollBar()
            sb.setValue(sb.value() - delta // 2)
            event.accept()

    def _adjust_scroll_after_zoom(
        self,
        mouse_x: float,
        old_scroll: int,
        old_zoom: float,
        new_zoom: float,
    ) -> None:
        sb = self.horizontalScrollBar()
        ratio = new_zoom / max(old_zoom, 0.001)
        new_scroll = int((old_scroll + mouse_x) * ratio - mouse_x)
        sb.setValue(max(0, min(sb.maximum(), new_scroll)))
