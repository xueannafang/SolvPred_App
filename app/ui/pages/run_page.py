from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QGroupBox,
    QFormLayout,
    QComboBox,
    QListWidget,
    QListWidgetItem,
)
import logging
import traceback

from app.api_facade import SetupSession, calculate_mixture
from app.ui.theme import AppTheme
from app.ui.widgets import h1, PrimaryButton
from collections.abc import Callable
from app.models import CalculationResult


class _CalcWorker(QThread):
    done = pyqtSignal(object, object)  # results, error

    def __init__(
        self,
        session: SetupSession,
        selected_cas_list: list[str] | None = None,
        solvent_info: dict | None = None,
    ):
        super().__init__()
        self._session = session
        self._selected_cas_list = selected_cas_list
        self._solvent_info = solvent_info

    def run(self) -> None:
        try:
            pctx = self._session.finalize()
            selected_cas_list = self._selected_cas_list or pctx.selected_cas_list
            solvent_info = self._solvent_info or pctx.solvent_info
            res = calculate_mixture(selected_cas_list, solvent_info, pctx.target)
            self.done.emit(res, None)
        except Exception as e:  # noqa: BLE001
            tb = traceback.format_exc()
            logging.exception("Calculation worker failed")
            self.done.emit(None, (e, tb))


class RunPage(QWidget):
    def __init__(
        self,
        theme: AppTheme,
        session: SetupSession,
        on_done: Callable[[list[CalculationResult]], None],
        on_back: Callable[[], None],
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._theme = theme
        self._session = session
        self._on_done = on_done
        self._on_back = on_back

        self._worker: _CalcWorker | None = None
        self._results = None

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        root.addWidget(h1("Run calculation"))
        self._status = QLabel("Ready.")
        self._status.setStyleSheet(f"color: {theme.text_muted.name()};")
        root.addWidget(self._status)

        # Filters panel
        self._filters_box = QGroupBox("Filters")
        fb = QFormLayout(self._filters_box)
        self._filter_pick = QComboBox()
        # Delay loading filter functions until the user navigates to this page.
        # The filter map will be populated in showEvent so session can be fully set up.
        self._filter_map: dict[str, object] = {}
        fb.addRow("Available", self._filter_pick)

        self._applied = QListWidget()
        fb.addRow("Applied", self._applied)

        filt_btns = QHBoxLayout()
        self._apply_filter_btn = PrimaryButton("Apply filter", theme)
        self._apply_filter_btn.clicked.connect(self._apply_filter)
        filt_btns.addWidget(self._apply_filter_btn)

        self._clear_filters_btn = PrimaryButton("Clear filters", theme)
        self._clear_filters_btn.clicked.connect(self._clear_filters)
        filt_btns.addWidget(self._clear_filters_btn)
        filt_btns.addStretch(1)
        fb.addRow("", filt_btns)

        self._filter_status = QLabel("Filtered solvents: (not applied)")
        self._filter_status.setStyleSheet(f"color: {theme.text_muted.name()};")
        fb.addRow("", self._filter_status)

        root.addWidget(self._filters_box)

        self._bar = QProgressBar()
        self._bar.setRange(0, 0)  # indeterminate
        self._bar.setVisible(False)
        root.addWidget(self._bar)

        nav = QHBoxLayout()
        self._back_btn = PrimaryButton("Back", theme)
        self._back_btn.clicked.connect(self._on_back)
        nav.addWidget(self._back_btn)
        nav.addStretch(1)

        self._run_btn = PrimaryButton("Run", theme)
        self._run_btn.clicked.connect(self._start)
        nav.addWidget(self._run_btn)

        root.addLayout(nav)
        root.addStretch(1)

        self._applied_filters: list[tuple[str, object]] = []
        self._filtered_cas: list[str] | None = None
        self._refresh_filter_status()

    def _load_filter_functions(self) -> dict[str, object]:
        from app.logic import filters as solv_filters
        # Load all filter functions from logic/filters.py using __all__
        out: dict[str, object] = {}
        for fname in solv_filters.__all__:
            get_fn = getattr(solv_filters, fname)
            fn = get_fn(self._session)
            name = getattr(fn, "name", 'Unnamed Filter')
            out[name] = fn
        return out

    def _reload_filters(self) -> None:
        """Reload filter functions from the logic module and refresh UI.

        This is called when the page is shown so that filters are created
        with a fully-initialized session and any changes to filter factories
        are picked up each time the user visits this page.
        """
        self._filter_map = self._load_filter_functions()
        self._filter_pick.clear()
        self._filter_pick.addItems(self._filter_map.keys())
        # Clear applied filters to avoid stale callables from previous sessions
        self._clear_filters()
        self._status.setText("Filters reloaded.")

    def _apply_filter(self) -> None:
        name = self._filter_pick.currentText()
        fn = self._filter_map.get(name)
        if not fn:
            return
        # If getattr(fn, 'warnings', None) is not None: display warning to user
        warning = getattr(fn, 'warning', None)
        if warning:
            self._status.setStyleSheet("color: orange;")
            self._status.setText(warning)
        self._applied_filters.append((name, fn))
        self._applied.addItem(QListWidgetItem(name))
        self._recompute_filtered()

    def _clear_filters(self) -> None:
        self._applied_filters = []
        self._applied.clear()
        self._filtered_cas = None
        self._refresh_filter_status()

    def _recompute_filtered(self) -> None:
        cas_list = list(self._session.selected)
        for _, fn in self._applied_filters:
            next_list: list[str] = []
            for cas in cas_list:
                s = self._session.get_solvent(cas)
                if fn(s):  # type: ignore
                    next_list.append(cas)
            cas_list = next_list
        self._filtered_cas = cas_list
        self._refresh_filter_status()

    def _refresh_filter_status(self) -> None:
        total = len(self._session.selected)
        if self._filtered_cas is None:
            self._filter_status.setText(f"Filtered solvents: not applied (total {total})")
        else:
            self._filter_status.setText(f"Filtered solvents: {len(self._filtered_cas)} / {total}")

    def _start(self) -> None:
        if self._worker is not None:
            return
        if self._applied_filters:
            self._recompute_filtered()
            if self._filtered_cas is not None and len(self._filtered_cas) == 0:
                dlg = QMessageBox(self)
                dlg.setIcon(QMessageBox.Icon.Warning)
                dlg.setWindowTitle("No solvents after filtering")
                dlg.setText("Your filters removed all selected solvents.")
                dlg.setInformativeText("Clear filters or adjust selection, then run again.")
                dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
                dlg.exec()
                return
        self._run_btn.setEnabled(False)
        self._back_btn.setEnabled(False)
        self._bar.setVisible(True)
        self._status.setText("Running…")

        selected_cas_list = self._filtered_cas
        solvent_info = None
        if selected_cas_list is not None:
            solvent_info = {}
            for cas in selected_cas_list:
                s = self._session.get_solvent(cas)
                if s is not None:
                    solvent_info[cas] = s
        self._worker = _CalcWorker(
            self._session,
            selected_cas_list=selected_cas_list,
            solvent_info=solvent_info,
        )
        self._worker.done.connect(self._finished)
        self._worker.start()

    def _finished(self, results, error) -> None:
        self._bar.setVisible(False)
        self._worker = None
        self._run_btn.setEnabled(True)
        self._back_btn.setEnabled(True)

        if error is not None:
            # error may be an exception or a tuple (exc, traceback_str)
            exc = error
            tb = None
            if isinstance(error, tuple):
                exc, tb = error

            exc_name = type(exc).__name__ if exc is not None else "Error"
            exc_msg = str(exc) if exc is not None else "An unknown error occurred."
            self._status.setText(f"Failed: {exc_name}: {exc_msg}")

            # Show a detailed message box with option to view traceback
            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Critical)
            dlg.setWindowTitle("Calculation failed")
            # Primary visible text
            dlg.setText("Calculation failed while running the solver.")
            # Short informative text (fallback to exception name if empty)
            info_text = f"{exc_name}: {exc_msg}" if exc_msg else exc_name
            dlg.setInformativeText(info_text)
            # Detailed traceback if available
            dlg.setDetailedText(tb or "")
            # Ensure a visible standard button exists
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.setDefaultButton(QMessageBox.StandardButton.Ok)
            dlg.exec()

            return

        self._results = results or []
        self._status.setText(f"Done. Found {len(self._results)} valid combinations.")
        self._on_done(self._results)

    def showEvent(self, event) -> None:
        # When the page becomes visible, reload filters so factories run
        # with an up-to-date session and the latest logic.
        self._reload_filters()
        super().showEvent(event)
