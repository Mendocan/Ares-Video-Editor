from __future__ import annotations

import random

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsProxyWidget,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.ui.app_theme import ACCENT_TEAL, BG_INPUT_DARK, BG_PREVIEW_VIDEO


class PreviewVideoHost(QWidget):
    """QGraphicsVideoItem + QLabel proxy; Windows'ta QVideoWidget üstünde altyazı görünmez sorununu önler."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.scene = QGraphicsScene(self)
        self.graphics_view = QGraphicsView(self.scene)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.graphics_view.setFrameShape(QFrame.Shape.NoFrame)
        self.graphics_view.setStyleSheet(f"background: {BG_PREVIEW_VIDEO};")
        layout.addWidget(self.graphics_view)

        self.video_item = QGraphicsVideoItem()
        self.scene.addItem(self.video_item)
        self.video_item.nativeSizeChanged.connect(self._on_video_geometry_changed)

        self.subtitle_preview = QLabel()
        self.subtitle_preview.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom
        )
        self.subtitle_preview.setWordWrap(True)
        self.subtitle_preview.setTextFormat(Qt.TextFormat.RichText)
        self.subtitle_preview.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.subtitle_preview.setStyleSheet("background: transparent;")

        self.subtitle_proxy = QGraphicsProxyWidget()
        self.subtitle_proxy.setWidget(self.subtitle_preview)
        self.subtitle_proxy.setParentItem(self.video_item)
        self.subtitle_proxy.setZValue(10)

    @property
    def video_output(self) -> QGraphicsVideoItem:
        return self.video_item

    @property
    def video_widget(self) -> QGraphicsVideoItem:
        """Geriye dönük uyumluluk."""
        return self.video_item

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_video_view()

    def showEvent(self, event):
        super().showEvent(event)
        self._fit_video_view()

    def _on_video_geometry_changed(self, *_args) -> None:
        self._fit_video_view()

    def _fit_video_view(self) -> None:
        if self.video_item.nativeSize().isValid():
            self.graphics_view.fitInView(self.video_item, Qt.AspectRatioMode.KeepAspectRatio)
        self._sync_subtitle_geometry()

    def _sync_subtitle_geometry(self) -> None:
        self.update_subtitle_position("Alt Orta")

    def update_subtitle_position(self, position_name: str) -> None:
        rect = self.video_item.boundingRect()
        if rect.width() <= 1 or rect.height() <= 1:
            return
        width = max(120, int(rect.width() * 0.92))
        self.subtitle_preview.setFixedWidth(width)
        x = (rect.width() - width) / 2
        margin = rect.height() * 0.08
        if position_name == "Ust Orta":
            y = margin
        elif position_name == "Orta":
            y = max(margin, (rect.height() - self.subtitle_preview.sizeHint().height()) / 2)
        else:
            y = max(margin, rect.height() * 0.72)
        self.subtitle_proxy.setPos(x, y)


class AudioVisualizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 30)
        self.l_val = 0.0
        self.r_val = 0.0
        self.is_playing = False

    def update_wave(self, is_playing: bool):
        self.is_playing = is_playing
        if self.is_playing:
            self.l_val = random.uniform(0.1, 1.0)
            self.r_val = random.uniform(0.1, 1.0)
        else:
            self.l_val = max(0.0, self.l_val - 0.15)
            self.r_val = max(0.0, self.r_val - 0.15)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        bar_w = 6
        spacing = 4
        lx = (w - (2 * bar_w + spacing)) / 2
        rx = lx + bar_w + spacing

        gradient = QLinearGradient(0, h, 0, 0)
        gradient.setColorAt(0.0, QColor("#10B981"))
        gradient.setColorAt(0.6, QColor("#F59E0B"))
        gradient.setColorAt(1.0, QColor("#EF4444"))

        def draw_bar(x, val):
            if val > 0:
                bh = h * val
                by = h - bh
                painter.fillRect(int(x), int(by), int(bar_w), int(bh), gradient)

        painter.fillRect(int(lx), 0, int(bar_w), int(h), QColor(BG_INPUT_DARK))
        painter.fillRect(int(rx), 0, int(bar_w), int(h), QColor(BG_INPUT_DARK))

        draw_bar(lx, self.l_val)
        draw_bar(rx, self.r_val)


COLOR_PLAY_TEAL = ACCENT_TEAL
