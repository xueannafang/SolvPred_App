from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtWidgets import QLabel, QPushButton, QWidget, QHBoxLayout

from app.ui.theme import AppTheme


def h1(text: str) -> QLabel:
    lbl = QLabel(text)
    f = QFont()
    f.setPointSize(16)
    f.setBold(True)
    lbl.setFont(f)
    lbl.setWordWrap(True)
    return lbl


def h2(text: str) -> QLabel:
    lbl = QLabel(text)
    f = QFont()
    f.setPointSize(12)
    f.setBold(True)
    lbl.setFont(f)
    lbl.setWordWrap(True)
    return lbl


def muted(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    return lbl


class PrimaryButton(QPushButton):
    def __init__(self, text: str, theme: AppTheme, parent: QWidget | None = None):
        super().__init__(text, parent)
        self._theme = theme
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(34)
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QPushButton {
                border: 1px solid transparent;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 600;
            }
            QPushButton:enabled {
                background: %s;
                color: white;
            }
            QPushButton:disabled {
                background: #5B6B86;
                color: #EAF0FF;
            }
            QPushButton:hover:enabled { background: %s; }
            """
            % (self._theme.primary.name(), self._theme.primary.lighter(120).name())
        )


class DangerButton(QPushButton):
    def __init__(self, text: str, theme: AppTheme, parent: QWidget | None = None):
        super().__init__(text, parent)
        self._theme = theme
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(30)
        self.setStyleSheet(
            """
            QPushButton {
                border: 1px solid transparent;
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: 600;
                background: %s;
                color: white;
            }
            QPushButton:hover { background: %s; }
            """ % (self._theme.danger.name(), self._theme.danger.lighter(120).name())
        )


def step_row(step_no: int, title: str, active: bool, done: bool, theme: AppTheme) -> QWidget:
    w = QWidget()
    layout = QHBoxLayout(w)
    layout.setContentsMargins(10, 8, 10, 8)

    badge = QLabel(str(step_no))
    badge.setFixedSize(22, 22)
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

    bg = theme.primary if active else theme.panel_alt
    fg = QColor("white") if (active or done) else theme.text_muted
    if done:
        bg = theme.primary.darker(130)

    badge.setStyleSheet(
        "border-radius: 11px; background: %s; color: %s; font-weight: 700;"
        % (bg.name(), fg.name())
    )

    lbl = QLabel(title)
    lbl.setWordWrap(True)
    if active:
        lbl.setStyleSheet(f"color: {theme.text.name()}; font-weight: 700;")
    else:
        lbl.setStyleSheet(f"color: {theme.text_muted.name()};")

    layout.addWidget(badge)
    layout.addWidget(lbl, 1)
    return w


from PyQt6.QtGui import QColor  # noqa: E402 (used above)


class FloatingTooltip(QLabel):
    """Frameless floating label used as a persistent solvent info tooltip."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip)
        self.setWordWrap(False)
        self.setStyleSheet(
            "QLabel { background: #ffffc8; border: 1px solid #888; color: #111; padding: 4px 8px; }"
        )
        self.hide()

    def show_at(self, global_pos, text: str) -> None:
        self.setText(text)
        self.adjustSize()
        self.move(global_pos.x() + 14, global_pos.y() + 8)
        self.show()
        self.raise_()
