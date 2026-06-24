from __future__ import annotations

import random

from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import QWidget

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
                
        # Arkaplan yuvalari
        painter.fillRect(int(lx), 0, int(bar_w), int(h), QColor("#1E293B"))
        painter.fillRect(int(rx), 0, int(bar_w), int(h), QColor("#1E293B"))
        
        draw_bar(lx, self.l_val)
        draw_bar(rx, self.r_val)


COLOR_PLAY_TEAL = "#2DD4BF"
