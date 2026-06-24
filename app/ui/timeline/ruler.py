from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import (
    QColor, QPainter, QPen, QPolygonF, QBrush, QFont, QMouseEvent, QLinearGradient,
)
from PySide6.QtWidgets import QWidget

from app.ui.timeline.theme import C_BORDER, C_TEXT, C_TICK_MAJ, C_TICK_MIN

# Movavi tarzı playhead sabitleri
PLAYHEAD_LINE_COLOR = QColor("#FF6A1A")
PLAYHEAD_HIT_HALF = 9          # Sürükleme alanı ±9px (toplam 18px)
PLAYHEAD_LINE_WIDTH = 2
PLAYHEAD_HANDLE_HALF_W = 8     # Üçgen yarı genişlik
PLAYHEAD_HANDLE_HEIGHT = 11    # Üçgen yükseklik


def _draw_playhead_handle(painter: QPainter, px: int, tip_y: int) -> None:
    """Cetvel üstünde Movavi tarzı turuncu üçgen tutamaç (beyaz çerçeve)."""
    tri = QPolygonF([
        QPointF(px - PLAYHEAD_HANDLE_HALF_W, 0),
        QPointF(px + PLAYHEAD_HANDLE_HALF_W, 0),
        QPointF(px, tip_y),
    ])
    painter.setPen(QPen(QColor(255, 255, 255, 200), 1.2))
    painter.setBrush(QBrush(PLAYHEAD_LINE_COLOR))
    painter.drawPolygon(tri)


def _draw_playhead_line(painter: QPainter, px: int, y1: int, y2: int) -> None:
    """Dikey turuncu çizgi + hafif glow."""
    for offset, alpha in ((4, 25), (2, 55), (1, 90)):
        painter.setPen(QPen(QColor(255, 106, 26, alpha), offset * 2))
        painter.drawLine(px, y1, px, y2)
    painter.setPen(QPen(PLAYHEAD_LINE_COLOR, PLAYHEAD_LINE_WIDTH))
    painter.drawLine(px, y1, px, y2)


class TimeRuler(QWidget):
    """Zaman cetveli — tıklanabilir ve sürüklenebilir playhead."""

    seek_requested = Signal(int)

    HEIGHT = 32

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(self.HEIGHT)
        self.duration_ms: int = 0
        self.px_per_ms: float = 0.1
        self.playhead_ms: int = 0
        self._dragging = False
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

    def configure(self, duration_ms: int, px_per_ms: float, playhead_ms: int) -> None:
        self.duration_ms = duration_ms
        self.px_per_ms = px_per_ms
        self.playhead_ms = playhead_ms
        self.setMinimumWidth(max(100, int(duration_ms * px_per_ms)))
        self.update()

    def _playhead_px(self) -> int:
        return int(self.playhead_ms * self.px_per_ms)

    def _x_to_ms(self, x: int) -> int:
        if self.px_per_ms <= 0:
            return 0
        return max(0, min(self.duration_ms, int(x / self.px_per_ms)))

    def _near_playhead(self, x: int) -> bool:
        return abs(x - self._playhead_px()) <= PLAYHEAD_HIT_HALF

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton:
            return
        x = event.pos().x()
        self._dragging = True
        if self._near_playhead(x):
            self.setCursor(Qt.SizeHorCursor)
        ms = self._x_to_ms(x)
        self.playhead_ms = ms
        self.update()
        self.seek_requested.emit(ms)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        x = event.pos().x()
        if self._dragging:
            ms = self._x_to_ms(x)
            self.playhead_ms = ms
            self.update()
            self.seek_requested.emit(ms)
            self.setCursor(Qt.SizeHorCursor)
        elif self._near_playhead(x):
            self.setCursor(Qt.SizeHorCursor)
        else:
            self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._dragging = False
        if self._near_playhead(event.pos().x()):
            self.setCursor(Qt.SizeHorCursor)
        else:
            self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor("#1A2235"))
        grad.setColorAt(1.0, QColor("#111827"))
        painter.fillRect(0, 0, w, h, grad)

        painter.setPen(QPen(C_BORDER, 1))
        painter.drawLine(0, h - 1, w, h - 1)

        if self.duration_ms <= 0:
            return

        step_ms = self._pick_step()
        minor_ms = step_ms // 5 if step_ms >= 500 else step_ms

        painter.setPen(QPen(C_TICK_MIN, 1))
        ms = 0
        while ms <= self.duration_ms:
            x = int(ms * self.px_per_ms)
            if ms % step_ms != 0:
                painter.drawLine(x, h - 6, x, h - 1)
            ms += minor_ms

        ms = 0
        label_font = QFont("Segoe UI", 7)
        painter.setFont(label_font)
        while ms <= self.duration_ms:
            x = int(ms * self.px_per_ms)
            painter.setPen(QPen(C_TICK_MAJ, 1))
            painter.drawLine(x, h - 14, x, h - 1)
            painter.setPen(QColor("#CBD5E1"))
            painter.drawText(x + 3, h - 16, self._format_ms(ms))
            ms += step_ms

        px = self._playhead_px()
        tip_y = PLAYHEAD_HANDLE_HEIGHT + 1
        _draw_playhead_handle(painter, px, tip_y)
        _draw_playhead_line(painter, px, tip_y, h)

    def _pick_step(self) -> int:
        candidates = [100, 250, 500, 1000, 2000, 5000, 10000, 30000, 60000, 300000]
        for s in candidates:
            if self.px_per_ms * s >= 50:
                return s
        return candidates[-1]

    @staticmethod
    def _format_ms(ms: int) -> str:
        s, _ = divmod(ms, 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"


class PlayheadScrubber(QWidget):
    """Track alanında sürüklenebilir playhead — klip üstünde kolay tutma."""

    seek_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.playhead_ms: int = 0
        self.px_per_ms: float = 0.1
        self.duration_ms: int = 0
        self._dragging = False
        self.setCursor(Qt.SizeHorCursor)

    def configure(self, playhead_ms: int, px_per_ms: float, duration_ms: int) -> None:
        self.playhead_ms = playhead_ms
        self.px_per_ms = px_per_ms
        self.duration_ms = duration_ms
        self.update()

    def _x_to_ms(self, x: int) -> int:
        if self.px_per_ms <= 0:
            return self.playhead_ms
        global_x = self.x() + x
        return max(0, min(self.duration_ms, int(global_x / self.px_per_ms)))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        cx = self.width() // 2
        _draw_playhead_line(painter, cx, 0, self.height())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging = True
            ms = self._x_to_ms(event.pos().x())
            self.playhead_ms = ms
            self.seek_requested.emit(ms)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            ms = self._x_to_ms(event.pos().x())
            self.playhead_ms = ms
            self.seek_requested.emit(ms)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._dragging = False


class TimelineContainer(QWidget):
    """Clip track'leri içeren widget; playhead scrubber overlay olarak üstte durur."""

    playhead_seek = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.playhead_ms: int = 0
        self.px_per_ms: float = 0.1
        self.duration_ms: int = 0
        self.ruler_height: int = TimeRuler.HEIGHT
        self._scrubber = PlayheadScrubber(self)
        self._scrubber.seek_requested.connect(self._on_scrubber_seek)
        self._scrubber.hide()

    def _on_scrubber_seek(self, ms: int) -> None:
        self.playhead_ms = ms
        self.playhead_seek.emit(ms)

    def set_playhead(self, ms: int, px_per_ms: float, duration_ms: int = 0) -> None:
        self.playhead_ms = ms
        self.px_per_ms = px_per_ms
        if duration_ms > 0:
            self.duration_ms = duration_ms
        self._position_scrubber()
        self.update()

    def _position_scrubber(self) -> None:
        if self.px_per_ms <= 0 or self.height() <= self.ruler_height:
            self._scrubber.hide()
            return
        x = int(self.playhead_ms * self.px_per_ms)
        top = self.ruler_height
        h = max(1, self.height() - top)
        half = PLAYHEAD_HIT_HALF
        self._scrubber.setGeometry(x - half, top, half * 2, h)
        self._scrubber.configure(self.playhead_ms, self.px_per_ms, self.duration_ms)
        self._scrubber.show()
        self._scrubber.raise_()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_scrubber()

    def raise_playhead(self) -> None:
        """Klip yenilendikten sonra scrubber'ı en üste taşı."""
        self._position_scrubber()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
