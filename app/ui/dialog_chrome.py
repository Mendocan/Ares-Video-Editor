"""Modal pencereler icin cerceveli baslik cubugu ve bordo-kirmizi kapatma dugmesi."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.ui.app_theme import BG_PANEL, BORDER, BORDER_DARK, TEXT_PRIMARY

COLOR_CLOSE = "#8B1E2F"
COLOR_CLOSE_HOVER = "#A5283C"
COLOR_CLOSE_PRESSED = "#6E1725"


def close_button_qss() -> str:
    return (
        "QPushButton {"
        f"background: {COLOR_CLOSE};"
        "color: #FFFFFF;"
        f"border: 2px solid {COLOR_CLOSE_PRESSED};"
        "border-radius: 4px;"
        "font-size: 13px;"
        "font-weight: bold;"
        "padding: 0px;"
        "min-width: 26px;"
        "max-width: 26px;"
        "min-height: 26px;"
        "max-height: 26px;"
        "}"
        f"QPushButton:hover {{ background: {COLOR_CLOSE_HOVER}; border-color: {COLOR_CLOSE}; }}"
        f"QPushButton:pressed {{ background: {COLOR_CLOSE_PRESSED}; }}"
    )


def build_dialog_title_bar(dialog: QDialog, title: str) -> QWidget:
    """Bordo cerceveli X dugmeli baslik cubugu."""
    bar = QWidget()
    bar.setFixedHeight(34)
    bar.setStyleSheet(
        f"QWidget {{ background: {BG_PANEL}; border-bottom: 1px solid {BORDER}; }}"
        f"QLabel {{ color: {TEXT_PRIMARY}; font-weight: 600; font-size: 12px; background: transparent; }}"
    )
    layout = QHBoxLayout(bar)
    layout.setContentsMargins(12, 0, 6, 0)
    layout.setSpacing(8)

    label = QLabel(title)
    layout.addWidget(label, 1)

    close_btn = QPushButton("✕")
    close_btn.setToolTip("Kapat")
    close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    close_btn.setStyleSheet(close_button_qss())
    close_btn.clicked.connect(dialog.reject)
    layout.addWidget(close_btn)
    return bar


def apply_frameless_chrome(dialog: QDialog, title: str) -> QVBoxLayout:
    """Dialog'u cercevesiz yapip baslik cubugu ekler; icerik layout'unu dondurur."""
    dialog.setWindowFlags(
        Qt.WindowType.Dialog
        | Qt.WindowType.FramelessWindowHint
    )
    dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

    outer = QVBoxLayout(dialog)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)
    outer.addWidget(build_dialog_title_bar(dialog, title))

    body = QWidget()
    body.setObjectName("dialogBody")
    body.setStyleSheet(
        f"QWidget#dialogBody {{"
        f"background: {BG_PANEL};"
        f"border: 1px solid {BORDER_DARK};"
        "border-top: none;"
        "border-bottom-left-radius: 8px;"
        "border-bottom-right-radius: 8px;"
        "}}"
    )
    content_layout = QVBoxLayout(body)
    content_layout.setContentsMargins(14, 12, 14, 14)
    content_layout.setSpacing(8)
    outer.addWidget(body, 1)
    return content_layout
