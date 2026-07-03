"""Ares Editor — parlak metalik gri (cilali kron/aluminyum) arayuz temasi."""

from __future__ import annotations

from PySide6.QtGui import QColor

# ── Arka planlar (PARLAK METALIK GRI) ──────────────────────────────────────
# Duz/mat tek renk yerine, cilali metal yuzeyleri taklit eden coklu-durakli
# (multi-stop) parlaklik bantlari kullanilir: parlak isik -> golge -> ikincil
# yansima -> golge. Bu, klasik "brushed aluminum / chrome" gorunumunu verir.
BG_APP_TOP = "#F4F5F7"
BG_APP_HIGH = "#DEE1E6"
BG_APP_MID = "#C4C9D0"
BG_APP_SHADE = "#9CA2AB"
BG_APP_REFLECT = "#BEC3CA"
BG_APP_BOTTOM = "#868D97"
BG_APP_GRADIENT = (
    f"qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    f"stop:0 {BG_APP_TOP}, stop:0.16 {BG_APP_HIGH}, stop:0.4 {BG_APP_MID}, "
    f"stop:0.58 {BG_APP_SHADE}, stop:0.75 {BG_APP_REFLECT}, stop:1 {BG_APP_BOTTOM})"
)
BG_PANEL = "#D4D8DE"
BG_PANEL_DARK = "#B8BDC5"
BG_SIDEBAR = "#C9CDD4"
BG_STACK = "#CFD3D9"
BG_INPUT = "#F7F8FA"
BG_INPUT_DARK = "#E4E7EB"
BG_HOVER = "#BCC1C9"
BG_PRESSED = "#A2A8B0"
BG_PREVIEW_SHELL = "#C2C7CE"
BG_TRANSPORT = "#BABFC7"
BG_PREVIEW_VIDEO = "#000000"
BG_DROP_ZONE = "#DCE0E5"
BG_DROP_ZONE_HOVER = "#CFD3DA"

# Timeline — ana panelden biraz daha koyu ama yine parlak metalik tonlar
TL_BG = "#A8ADB6"
TL_BG_MID = "#9FA4AD"
TL_BG_PANEL = "#A2A7B0"
TL_BG_TRACK = "#AFB4BC"
TL_BG_DARK = "#989DA6"
TL_BG_MINI = "#949AA2"
TL_TOOLBAR = "#ACB1B9"
TL_HEADER = "#A5AAB2"
TL_HEADER_GRAD_TOP = "#C4C9D0"
TL_HEADER_GRAD_BOTTOM = "#9DA2AB"
TL_SCROLL = "#B0B5BD"
TL_STATUS = "#9FA4AD"
TL_RULER_TOP = "#C4C9D0"
TL_RULER_BOTTOM = "#9DA2AB"

# Kenarliklar (daha keskin kontrast — cilali kenar hissi)
BORDER = "#767D87"
BORDER_LIGHT = "#F7F8FA"
BORDER_DARK = "#5C626B"
BORDER_DASHED = "#6C737C"

# Metin (koyu)
TEXT_PRIMARY = "#14171C"
TEXT_SECONDARY = "#343A42"
TEXT_MUTED = "#555C65"
TEXT_DISABLED = "#7C838C"
TEXT_ON_ACCENT = "#FFFFFF"
TEXT_BRAND = "#1F4D4D"

# Vurgu
ACCENT = "#3D5A80"
ACCENT_HOVER = "#2F4D6E"
ACCENT_BRIGHT = "#5C8AC7"
ACCENT_SELECTION = "#E6E9EE"
ACCENT_TEAL = "#227A7A"

# Fonksiyonel
COLOR_SUCCESS = "#2D7A4F"
COLOR_DANGER = "#C23F3F"
COLOR_WARNING = "#A8781E"
COLOR_INFO = "#3D6A9A"
COLOR_PLAY = "#2A6B88"
COLOR_STOP = "#C23F3F"
COLOR_TRANSPORT = "#454B54"
COLOR_TRANSPORT_DIM = "#5C636C"
COLOR_PLAYHEAD = "#E06A1A"
COLOR_ICON_DEFAULT = "#555C65"
COLOR_ICON_ACTIVE = "#1F4D4D"

# Buton gradyanlari — parlak (glossy) metalik his icin genis kontrastli,
# birden fazla durakli gradyanlar.
BTN_PRIMARY_GRADIENT = (
    f"qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    f"stop:0 {ACCENT_BRIGHT}, stop:0.45 {ACCENT}, stop:1 {ACCENT_HOVER})"
)
BTN_PRIMARY_HOVER = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    f"stop:0 #7CA5DD, stop:0.45 #4A6FA5, stop:1 {ACCENT_HOVER})"
)
BTN_METALLIC_GRADIENT = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    "stop:0 #FBFCFD, stop:0.14 #E8EBEE, stop:0.42 #CBD0D7, "
    "stop:0.55 #AEB4BC, stop:0.72 #C4C9D0, stop:1 #9CA2AB)"
)
BTN_METALLIC_HOVER = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    "stop:0 #FFFFFF, stop:0.14 #F2F4F6, stop:0.42 #D8DCE2, "
    "stop:0.55 #BFC4CC, stop:0.72 #D2D6DD, stop:1 #A8AEB6)"
)
BTN_METALLIC_PRESSED = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    "stop:0 #9CA2AB, stop:0.5 #AEB4BC, stop:1 #CBD0D7)"
)

# Islem paneli — SRT / MP4 / onizleme butonlari
BTN_SRT_GRADIENT = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    "stop:0 #6BB5B5, stop:0.5 #3D9494, stop:1 #227A7A)"
)
BTN_SRT_HOVER = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    "stop:0 #7EC5C5, stop:0.5 #4AA4A4, stop:1 #2A8A8A)"
)
BTN_MP4_GRADIENT = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    f"stop:0 #45A872, stop:0.5 {COLOR_SUCCESS}, stop:1 #1F5F3D)"
)
BTN_MP4_HOVER = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    "stop:0 #5CBA85, stop:0.5 #3A8F5E, stop:1 #287A4A)"
)
BTN_PREVIEW_GRADIENT = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    f"stop:0 #6A9FD4, stop:0.5 {COLOR_INFO}, stop:1 #2A5080)"
)
BTN_PREVIEW_HOVER = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    "stop:0 #7EB0E0, stop:0.5 #4D7FB5, stop:1 #356090)"
)


def action_button_qss(gradient: str, hover: str, border: str) -> str:
    """Islem paneli butonlari — acik/kapali durumda okunakli kontrast."""
    return (
        "QPushButton {"
        f"background: {gradient};"
        f"color: {TEXT_ON_ACCENT};"
        f"border: 1px solid {border};"
        "border-radius: 6px;"
        "padding: 10px 14px;"
        "font-weight: 600;"
        "}"
        f"QPushButton:hover {{ background: {hover}; }}"
        "QPushButton:disabled {"
        f"background: {BG_INPUT_DARK};"
        f"color: {TEXT_MUTED};"
        f"border: 1px solid {BORDER};"
        "}"
    )


QUALITY_RADIO_QSS = f"""
QRadioButton {{
    spacing: 6px;
    padding: 4px 10px;
    margin: 1px 0;
    border: 1px solid {BORDER};
    border-radius: 6px;
    background: {BG_INPUT};
    color: {TEXT_PRIMARY};
    font-weight: 500;
    font-size: 11px;
    min-height: 14px;
}}
QRadioButton:hover {{
    border-color: {ACCENT_BRIGHT};
    background: {BG_PANEL};
}}
QRadioButton:checked {{
    border: 2px solid {ACCENT_TEAL};
    background: {ACCENT_SELECTION};
    color: {TEXT_PRIMARY};
    font-weight: 600;
}}
QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 7px;
    border: 2px solid {BORDER_DARK};
    background: #FFFFFF;
}}
QRadioButton::indicator:hover {{
    border-color: {ACCENT_TEAL};
}}
QRadioButton::indicator:checked {{
    border: 2px solid {ACCENT_TEAL};
    background: {ACCENT_TEAL};
}}
"""

EXPORT_COMPACT_BTN_QSS = (
    "QPushButton {"
    "padding: 4px 12px;"
    "font-size: 11px;"
    "font-weight: 600;"
    "min-height: 24px;"
    "}"
)

APP_STYLE = f"""
QMainWindow, QWidget {{
    background: {BG_APP_GRADIENT};
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', 'Bahnschrift', sans-serif;
}}

QMenuBar {{
    background: {BG_APP_GRADIENT};
    color: {TEXT_PRIMARY};
    border-bottom: 1px solid {BORDER};
}}

QMenuBar::item:selected {{
    background: {BG_HOVER};
}}

QMenu {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
}}

QMenu::item:selected {{
    background-color: {ACCENT_SELECTION};
}}

QStatusBar {{
    background: {BG_PANEL_DARK};
    color: {TEXT_MUTED};
    border-top: 1px solid {BORDER};
}}

QPushButton {{
    background: {BTN_PRIMARY_GRADIENT};
    color: {TEXT_ON_ACCENT};
    border: 1px solid {ACCENT_HOVER};
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 12px;
}}

QPushButton:hover {{
    background: {BTN_PRIMARY_HOVER};
}}

QPushButton:disabled {{
    background: {BG_HOVER};
    color: {TEXT_DISABLED};
    border-color: {BORDER};
}}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 12px;
    color: {TEXT_PRIMARY};
    selection-background-color: {ACCENT_SELECTION};
    selection-color: {TEXT_PRIMARY};
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {ACCENT};
}}

QLineEdit:disabled, QComboBox:disabled {{
    background-color: {BG_HOVER};
    color: {TEXT_DISABLED};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox::down-arrow {{
    width: 8px;
    height: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    outline: 0;
    padding: 2px;
    selection-background-color: {ACCENT_SELECTION};
    selection-color: {TEXT_PRIMARY};
}}

QComboBox QAbstractItemView::item {{
    min-height: 24px;
    padding: 2px 8px;
    border-radius: 3px;
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: {BG_HOVER};
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: {ACCENT_SELECTION};
    color: {TEXT_PRIMARY};
}}

QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background-color: {BG_HOVER};
    border: none;
    width: 16px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {ACCENT_SELECTION};
}}

QToolTip {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    padding: 4px 6px;
}}

QListWidget, QListView, QTreeWidget {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    outline: 0;
}}

QListWidget::item:selected, QListView::item:selected {{
    background-color: {ACCENT_SELECTION};
    color: {TEXT_PRIMARY};
}}

QTabWidget::pane {{
    border: 1px solid {BORDER};
    background: {BG_PANEL};
}}

QTabBar::tab {{
    background: {BG_STACK};
    color: {TEXT_SECONDARY};
    padding: 6px 14px;
    border: 1px solid {BORDER};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}}

QTabBar::tab:selected {{
    background: {BG_PANEL};
    color: {TEXT_PRIMARY};
    font-weight: bold;
}}

QDialog {{
    background: {BG_APP_GRADIENT};
}}

QGroupBox {{
    border: 1px solid {BORDER_DARK};
    border-radius: 6px;
    margin-top: 14px;
    font-weight: bold;
    font-size: 12px;
    color: {TEXT_PRIMARY};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: {TEXT_SECONDARY};
}}

QLabel {{
    color: {TEXT_PRIMARY};
    background: transparent;
}}

QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid {BORDER_DARK};
    background: #FFFFFF;
}}

QCheckBox::indicator:hover {{
    border-color: {ACCENT_TEAL};
}}

QCheckBox::indicator:checked {{
    border: 2px solid {ACCENT_TEAL};
    background: {ACCENT_TEAL};
    image: none;
}}

QCheckBox::indicator:checked:hover {{
    border-color: {ACCENT_HOVER};
    background: {ACCENT_HOVER};
}}

QCheckBox::indicator:disabled {{
    border-color: {BORDER};
    background: {BG_HOVER};
}}

QSlider::groove:horizontal {{
    border: 1px solid {BORDER};
    height: 6px;
    background: {BG_INPUT_DARK};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: {ACCENT};
    border: 1px solid {ACCENT_HOVER};
    width: 14px;
    margin: -4px 0;
    border-radius: 7px;
}}

QSlider::handle:horizontal:disabled {{
    background: {TEXT_DISABLED};
}}

QScrollBar:horizontal {{
    background: {BG_PANEL_DARK};
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background: {BORDER_DARK};
    border-radius: 4px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {ACCENT};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""
