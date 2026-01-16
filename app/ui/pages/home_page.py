from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

from collections.abc import Callable

from app.ui.widgets import h1, muted, PrimaryButton
from app.ui.theme import AppTheme


class HomePage(QWidget):
    def __init__(self, theme: AppTheme, on_start: Callable[[], None], parent: QWidget | None = None):
        super().__init__(parent)
        self._theme = theme
        self._on_start = on_start

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(14)

        root.addWidget(h1("SolvPred Desktop"))
        root.addWidget(
            muted(
                "Step-by-step tool for co-solvent prediction using Hansen Solubility Parameters (HSP).\n"
                "You will: (1) select candidate solvents, (2) input target HSP + parameters, (3) run calculation, (4) review and export results."
            )
        )

        row = QHBoxLayout()
        row.addStretch(1)
        btn = PrimaryButton("Start", theme=theme)
        btn.clicked.connect(self._on_start)
        row.addWidget(btn)
        root.addLayout(row)

        root.addStretch(1)
