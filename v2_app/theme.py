from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon, QPixmap


APP_TITLE = "PNG 로고 파생본 자동 생성기 V2"
BRAND_NAME = "LOGOPLANET"
BRAND_TAGLINE = "PNG Brand Asset Studio"
DEFAULT_CUSTOM_HEX = "#1B4797"

COLOR_BG = "#F4F7FB"
COLOR_CARD = "#FFFFFF"
COLOR_CARD_SOFT = "#F8FBFF"
COLOR_BORDER = "#D9E3F0"
COLOR_TEXT = "#162237"
COLOR_MUTED = "#6A7A92"
COLOR_PRIMARY = "#1B4797"
COLOR_PRIMARY_DARK = "#143973"
COLOR_PRIMARY_SOFT = "#E9F1FB"
COLOR_SUCCESS = "#127A4B"


def resource_path(relative_path: str) -> Path:
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / relative_path  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent / relative_path


def load_app_icon() -> QIcon:
    for relative in ("assets/app_icon.ico", "assets/app_icon.png"):
        path = resource_path(relative)
        if path.exists():
            return QIcon(str(path))
    return QIcon()


def load_brand_pixmap(max_width: int = 32, max_height: int = 32) -> QPixmap | None:
    path = resource_path("assets/logoplanet_mark.png")
    if not path.exists():
        return None

    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return None
    return pixmap.scaled(
        max_width,
        max_height,
    )


APP_STYLESHEET = f"""
QMainWindow {{
    background: {COLOR_BG};
}}
QWidget {{
    color: {COLOR_TEXT};
    font-family: 'Malgun Gothic';
    font-size: 10pt;
}}
QFrame#card {{
    background: {COLOR_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 20px;
}}
QFrame#softCard {{
    background: {COLOR_CARD_SOFT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 18px;
}}
QLabel#eyebrow {{
    color: {COLOR_PRIMARY};
    font-size: 9pt;
    font-weight: 700;
}}
QLabel#title {{
    color: {COLOR_TEXT};
    font-size: 24pt;
    font-weight: 700;
}}
QLabel#sectionTitle {{
    color: {COLOR_TEXT};
    font-size: 13pt;
    font-weight: 700;
}}
QLabel#heroTag {{
    color: {COLOR_PRIMARY};
    font-size: 9pt;
    font-weight: 700;
}}
QLabel#muted {{
    color: {COLOR_MUTED};
}}
QFrame#dropZone {{
    background: {COLOR_CARD_SOFT};
    border: 1px dashed #C8D8F1;
    border-radius: 18px;
}}
QLineEdit, QPlainTextEdit {{
    background: {COLOR_CARD_SOFT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 14px;
    padding: 12px 14px;
}}
QLineEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {COLOR_PRIMARY};
}}
QPushButton {{
    background: {COLOR_PRIMARY};
    color: white;
    border: none;
    border-radius: 14px;
    padding: 12px 18px;
    font-weight: 700;
}}
QPushButton:hover {{
    background: {COLOR_PRIMARY_DARK};
}}
QPushButton:disabled {{
    background: #BFCBE0;
    color: #F4F7FB;
}}
QPushButton[role="secondary"] {{
    background: {COLOR_CARD_SOFT};
    color: {COLOR_PRIMARY};
    border: 1px solid {COLOR_BORDER};
}}
QPushButton[role="secondary"]:hover {{
    background: #EEF4FD;
}}
QToolButton {{
    background: {COLOR_CARD_SOFT};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 14px;
    padding: 10px 14px;
    font-weight: 600;
}}
QToolButton:checked {{
    background: {COLOR_PRIMARY_SOFT};
    color: {COLOR_PRIMARY};
    border: 1px solid #C8D8F1;
}}
QToolButton[role="ghost"] {{
    background: transparent;
    border: 1px solid {COLOR_BORDER};
    color: {COLOR_MUTED};
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 12px;
    margin: 4px 0 4px 0;
}}
QScrollBar::handle:vertical {{
    background: #C7D5E9;
    border-radius: 6px;
    min-height: 28px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QProgressBar {{
    background: {COLOR_CARD_SOFT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: {COLOR_PRIMARY};
    border-radius: 9px;
}}
"""
