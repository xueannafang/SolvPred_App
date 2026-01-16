from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtGui import QColor


@dataclass(frozen=True)
class AppTheme:
    bg: QColor
    panel: QColor
    panel_alt: QColor
    text: QColor
    text_muted: QColor
    primary: QColor
    danger: QColor
    border: QColor


DARK = AppTheme(
    bg=QColor("#0B1220"),
    panel=QColor("#0F1B2D"),
    panel_alt=QColor("#12233B"),
    text=QColor("#EAF0FF"),
    text_muted=QColor("#9FB3D9"),
    primary=QColor("#4F8CFF"),
    danger=QColor("#FF5C77"),
    border=QColor("#223556"),
)

LIGHT = AppTheme(
    bg=QColor("#F6F8FC"),
    panel=QColor("#FFFFFF"),
    panel_alt=QColor("#F0F4FF"),
    text=QColor("#0B1220"),
    text_muted=QColor("#5B6B86"),
    primary=QColor("#2F6BFF"),
    danger=QColor("#D92D20"),
    border=QColor("#D6DEEE"),
)
