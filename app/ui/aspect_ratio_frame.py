from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QSizePolicy, QVBoxLayout, QWidget


class AspectRatioFrame(QFrame):
    """Onizleme alanini secilen en-boy oraninda tutar."""

    def __init__(self, ratio_w: int = 16, ratio_h: int = 9, parent=None) -> None:
        super().__init__(parent)
        self._ratio_w = max(1, ratio_w)
        self._ratio_h = max(1, ratio_h)
        self._content = QWidget(self)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_ratio(self, ratio_w: int, ratio_h: int) -> None:
        self._ratio_w = max(1, ratio_w)
        self._ratio_h = max(1, ratio_h)
        self._apply_geometry()

    def set_ratio_from_label(self, label: str) -> None:
        if label == "9:16":
            self.set_ratio(9, 16)
        elif label == "1:1":
            self.set_ratio(1, 1)
        elif label == "4:5":
            self.set_ratio(4, 5)
        else:
            self.set_ratio(16, 9)

    def content_widget(self) -> QWidget:
        return self._content

    def content_layout(self) -> QVBoxLayout:
        return self._content_layout

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_geometry()

    def _apply_geometry(self) -> None:
        available = self.contentsRect()
        if available.width() <= 0 or available.height() <= 0:
            return

        target_ratio = self._ratio_w / self._ratio_h
        avail_ratio = available.width() / available.height()
        if avail_ratio > target_ratio:
            h = available.height()
            w = max(1, int(h * target_ratio))
        else:
            w = available.width()
            h = max(1, int(w / target_ratio))

        x = available.x() + (available.width() - w) // 2
        y = available.y() + (available.height() - h) // 2
        self._content.setGeometry(x, y, w, h)
