from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QStackedWidget,
    QLabel,
    QMessageBox,
    QToolButton,
    QMenu,
)

from app.api_facade import start_setup, SetupSession
from app.models import CalculationResult
from app.ui.theme import LIGHT, AppTheme
from app.ui.widgets import step_row
from app.ui.pages.home_page import HomePage
from app.ui.pages.select_solvents_page import SelectSolventsPage
from app.ui.pages.params_page import ParamsPage
from app.ui.pages.run_page import RunPage
from app.ui.pages.results_page import ResultsPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SolvPred")
        self.resize(960, 640)

        # Use light theme by default and keep plain text black
        self._theme: AppTheme = LIGHT
        self._session: SetupSession = start_setup()

        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar
        self._sidebar = QWidget()
        self._sidebar.setFixedWidth(260)
        sb = QVBoxLayout(self._sidebar)
        sb.setContentsMargins(14, 14, 14, 14)
        sb.setSpacing(6)

        title = QLabel("SolvPred")
        title.setStyleSheet(f"color: {self._theme.text.name()}; font-size: 18px; font-weight: 800;")
        sb.addWidget(title)

        subtitle = QLabel("Co-solvent predictor")
        subtitle.setStyleSheet(f"color: {self._theme.text_muted.name()};")
        sb.addWidget(subtitle)

        sb.addSpacing(10)

        self._steps_box = QVBoxLayout()
        sb.addLayout(self._steps_box)
        sb.addStretch(1)

        layout.addWidget(self._sidebar)

        # Pages
        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1)

        self._page_home = HomePage(self._theme, on_start=self.go_select)
        self._page_select = SelectSolventsPage(self._theme, self._session, on_next=self.go_params)
        self._page_params = ParamsPage(self._theme, self._session, on_back=self.go_select, on_next=self.go_run)
        self._page_run = RunPage(self._theme, self._session, on_done=self.go_results, on_back=self.go_params)
        self._page_results = ResultsPage(
            self._theme,
            on_restart=self.restart,
            on_edit_selection=self.go_select,
            on_edit_params=self.go_params,
        )

        for p in [self._page_home, self._page_select, self._page_params, self._page_run, self._page_results]:
            self._stack.addWidget(p)

        self._step_titles = [
            "Home",
            "Select solvents",
            "Target HSP",
            "Run",
            "Results",
        ]
        self._current_step = 0
        self._refresh_steps()

        self._apply_global_style()
        self.go_home()



    def _apply_global_style(self) -> None:
        t = self._theme
        plain_text = "#000000"

        css = f"""
            QMainWindow {{ background: {t.bg.name()}; }}
            QWidget {{ color: {plain_text}; font-family: Segoe UI; font-size: 11pt; }}
            QLineEdit, QListWidget, QTableWidget, QSpinBox, QDoubleSpinBox {{
                background: {t.panel.name()};
                border: 1px solid {t.border.name()};
                border-radius: 8px;
                padding: 6px;
            }}
            QGroupBox {{
                border: 1px solid {t.border.name()};
                border-radius: 10px;
                margin-top: 10px;
                padding: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: {plain_text};
                font-weight: 700;
            }}
            QLabel {{ background: transparent; color: {plain_text}; }}
            /* Lists */
            QListWidget, QListView, QTreeView {{
                background: {t.panel.name()};
                color: {plain_text};
                border: 1px solid {t.border.name()};
                border-radius: 8px;
            }}
            QListWidget::item {{
                background: transparent;
                color: {plain_text};
                padding: 6px 8px;
            }}
            QListWidget::item:selected {{
                background: {t.primary.name()};
                color: {plain_text};
            }}
            /* GroupBox inner labels (form labels) */
            QGroupBox QLabel {{ color: {plain_text}; background: transparent; }}
            /* Table headers */
            QHeaderView::section {{ background: {t.panel_alt.name()}; color: {plain_text}; padding: 6px; border: 1px solid {t.border.name()}; }}
            QTableWidget QTableCornerButton::section {{ background: {t.panel.name()}; }}
            /* Dialogs and message boxes should match app theme for contrast */
            QDialog, QMessageBox {{
                background: {t.panel.name()};
                color: {plain_text};
            }}
            QMessageBox QLabel {{ color: {plain_text}; }}
            QMenu {{ background: {t.panel.name()}; color: {plain_text}; }}
            QMenu::item:selected {{ background: {t.panel_alt.name()}; color: {plain_text}; }}
            QToolButton {{ color: {plain_text}; background: transparent; }}
        """

        self.setStyleSheet(css)
        self._sidebar.setStyleSheet(f"background: {t.panel_alt.name()}; border-right: 1px solid {t.border.name()};")

    def _refresh_steps(self) -> None:
        # Clear and rebuild
        while self._steps_box.count():
            item = self._steps_box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        for idx, title in enumerate(self._step_titles):
            w = step_row(idx + 1, title, active=(idx == self._current_step), done=(idx < self._current_step), theme=self._theme)
            self._steps_box.addWidget(w)

    def _set_step(self, step_index: int) -> None:
        self._current_step = step_index
        self._refresh_steps()

    def go_home(self) -> None:
        self._set_step(0)
        self._stack.setCurrentWidget(self._page_home)

    def go_select(self) -> None:
        self._set_step(1)
        self._stack.setCurrentWidget(self._page_select)

    def go_params(self) -> None:
        self._set_step(2)
        self._stack.setCurrentWidget(self._page_params)

    def go_run(self) -> None:
        # Ensure some candidates are selected and target exists
        if not self._session.selected:
            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Warning)
            dlg.setWindowTitle("Missing solvents")
            dlg.setText("No solvents selected for calculation.")
            dlg.setInformativeText("Please select one or more solvents on the 'Select solvents' page before running.")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()
            self.go_select()
            return
        if self._session.hsp_target is None:
            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Warning)
            dlg.setWindowTitle("Missing HSP target")
            dlg.setText("Target HSP parameters are not set.")
            dlg.setInformativeText("Please enter the target HSP values on the 'Target HSP' page before running.")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()
            self.go_params()
            return
        self._set_step(3)
        self._stack.setCurrentWidget(self._page_run)

    def go_results(self, results: list[CalculationResult]) -> None:
        # Pass solvent mapping and HSP target so ResultsPage can display names and plot target
        self._page_results.set_results(results, session=self._session)
        self._set_step(4)
        self._stack.setCurrentWidget(self._page_results)

    def restart(self) -> None:
        # Create a fresh backend session and rebind pages to it
        self._session = start_setup()
        # Rebind session to pages
        self._page_select._session = self._session  # noqa: SLF001
        self._page_params._session = self._session  # noqa: SLF001
        self._page_run._session = self._session  # noqa: SLF001

        # Ask each page to reset its UI to reflect a fresh session
        self._page_select.reset_ui()
        self._page_params._reset_defaults()
        self._page_results.set_results([])

        self.go_home()
