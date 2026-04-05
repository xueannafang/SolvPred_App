from __future__ import annotations

import csv
import json
from dataclasses import asdict
from numpy.linalg import norm

from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QIntValidator, QCursor
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QMessageBox,
    QLineEdit,
    QHBoxLayout,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

from app.api_facade import SetupSession
from app.models import CalculationResult
from app.ui.theme import AppTheme
from app.ui.widgets import h1, PrimaryButton, FloatingTooltip
import app.exceptions as exc
from collections.abc import Callable


class ResultsPage(QWidget):
    def __init__(
        self,
        theme: AppTheme,
        on_restart: Callable[[], None],
        on_edit_selection: Callable[[], None] | None = None,
        on_edit_params: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._theme = theme
        self._on_restart = on_restart
        self._on_edit_selection = on_edit_selection
        self._on_edit_params = on_edit_params
        self._results: list[CalculationResult] = []
        self._filtered_results: list[CalculationResult] = []
        self._solvent_info: dict = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        root.addWidget(h1("Results"))
        self._subtitle = QLabel("No results yet.")
        self._subtitle.setStyleSheet(f"color: {theme.text_muted.name()};")
        root.addWidget(self._subtitle)

        # Add an extra column for a 3D view button
        self._table = QTableWidget(0, 7)  # Updated column count to 7
        self._table.setHorizontalHeaderLabels([
            "CAS combination",
            "Concentrations",
            "Mixture (D,P,H)",
            "Error (D,P,H)",
            "#solvents",
            "Total Error",  # Added new column header
            "View",
        ])
        self._table.setWordWrap(True)
        self._table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self._table, 1)

        # Add filter and sort controls above the results table
        filter_sort_layout = QHBoxLayout()

        # Filter by solvent
        self._filter_solvent = QLineEdit()
        self._filter_solvent.setPlaceholderText("Filter by solvent (CAS or Name)")
        self._filter_solvent.textChanged.connect(self._apply_filters)
        filter_sort_layout.addWidget(self._filter_solvent)

        # Filter by number of solvents
        self._filter_num_solvents = QLineEdit()
        self._filter_num_solvents.setPlaceholderText("Filter by # of solvents")
        self._filter_num_solvents.setValidator(QIntValidator(1, 100))
        self._filter_num_solvents.textChanged.connect(self._apply_filters)
        filter_sort_layout.addWidget(self._filter_num_solvents)

        # Sort by error
        self._sort_by_error = QComboBox()
        self._sort_by_error.addItems(["Sort by total error", "Sort by δD", "Sort by δP", "Sort by δH"])
        self._sort_by_error.currentIndexChanged.connect(self._apply_filters)
        filter_sort_layout.addWidget(self._sort_by_error)

        # Show all / reset filters
        self._show_all_btn = QPushButton("Show all")
        self._show_all_btn.clicked.connect(self._reset_filters)
        filter_sort_layout.addWidget(self._show_all_btn)

        root.addLayout(filter_sort_layout)

        actions = QHBoxLayout()
        self._export_json = PrimaryButton("Export JSON", theme)
        self._export_json.clicked.connect(self._save_json)
        actions.addWidget(self._export_json)

        self._export_csv = PrimaryButton("Export CSV", theme)
        self._export_csv.clicked.connect(self._save_csv)
        actions.addWidget(self._export_csv)

        # Edit buttons to quickly return to setup
        self._edit_selection = PrimaryButton("Edit selection", theme)
        self._edit_selection.clicked.connect(lambda: self._on_edit_selection() if self._on_edit_selection else None)
        actions.addWidget(self._edit_selection)

        self._edit_params = PrimaryButton("Edit params", theme)
        self._edit_params.clicked.connect(lambda: self._on_edit_params() if self._on_edit_params else None)
        actions.addWidget(self._edit_params)

        actions.addStretch(1)
        self._restart = PrimaryButton("New session", theme)
        self._restart.clicked.connect(self._on_restart)
        actions.addWidget(self._restart)

        root.addLayout(actions)

        self._table.setMouseTracking(True)
        self._table.cellEntered.connect(self._show_solvent_tooltip)
        self._table.installEventFilter(self)
        self._tooltip = FloatingTooltip(self)

    def set_results(self, results: list[CalculationResult], session: SetupSession|None = None) -> None:
        # TODO: Maybe should use pctx instead of session?
        self._results = results
        self._filtered_results = list(results)
        self._subtitle.setText(f"Found {len(self._results)} valid combinations.")
        self._table.setRowCount(0)
        self._session = session
        solvent_info = session.get_candidates() if session else None
        self._solvent_info = solvent_info or {}

        for r in self._results:
            row = self._table.rowCount()
            self._table.insertRow(row)
            # Show CAS and solvent Name per line for clarity
            cas_lines: list[str] = []
            for cas in r.cas_comb:
                solvent = solvent_info.get(cas) if solvent_info else None
                name = solvent.Name if solvent else None
                if name:
                    cas_lines.append(f"{cas} — {name}")
                else:
                    cas_lines.append(str(cas))
            cas = "\n".join(cas_lines)

            conc_lines = [f"{v*100:.2f}%" for v in r.c_mean_norm]
            conc = "\n".join(conc_lines)
            mix = f"({r.hsp_mixture[0]:.2f}, {r.hsp_mixture[1]:.2f}, {r.hsp_mixture[2]:.2f})"
            err = f"({r.hsp_error[0]:+.3f}, {r.hsp_error[1]:+.3f}, {r.hsp_error[2]:+.3f})"
            n = str(len(r.cas_comb))
            total_error = norm(r.hsp_error)  # Calculate total error

            for col, text in enumerate([cas, conc, mix, err, n, f"{total_error:.3f}"]):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(row, col, item)

            # Add a view button in the last column to show a 3D HSP plot
            btn = QPushButton("View 3D")
            # capture current result, solvent_info and target in default args
            btn.clicked.connect(lambda _, res=r, ctx=session : self._open_3d_dialog(res, ctx))
            self._table.setCellWidget(row, 6, btn)  # Updated column index for the button

        self._table.resizeColumnsToContents()
        self._table.resizeRowsToContents()

    def _open_3d_dialog(self, result: CalculationResult, session: SetupSession) -> None:
        # TODO: Maybe should use pctx instead of session?
        if not session:
            return
        hsp_target = session.hsp_target
        # Create dialog with matplotlib canvas
        dlg = QDialog(self)
        dlg.setWindowTitle("HSP 3D view")
        layout = QVBoxLayout(dlg)

        fig = Figure(figsize=(6, 5))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111, projection='3d')

        solvent_info = session.get_candidates()

        # Plot all selected solvents in light gray
        all_ds: list[float] = []
        all_ps: list[float] = []
        all_hs: list[float] = []
        for cas, solvent in solvent_info.items():
            if solvent.D is not None:
                all_ds.append(solvent.D)
            if solvent.P is not None:
                all_ps.append(solvent.P)
            if solvent.H is not None:
                all_hs.append(solvent.H)

        ax.scatter(all_ds, all_ps, all_hs, color='gray', marker='o', s=30, label='All Selected Solvents')

        # Plot solvents from the calculation results
        ds, ps, hs, labels = [], [], [], []
        for cas in result.cas_comb:
            solvent = solvent_info[cas]
            ds.append(solvent.D)
            ps.append(solvent.P)
            hs.append(solvent.H)
            labels.append(f"{cas}\n{getattr(solvent, 'Name', '')}")

        # Mixture point
        md, mp, mh, _ = result.hsp_mixture
        ax.scatter([md], [mp], [mh], color='green', marker='^', s=120, label='Mixture')

        # Target point (if provided)
        td:float = hsp_target.D  # type: ignore
        tp:float = hsp_target.P  # type: ignore
        th:float = hsp_target.H  # type: ignore
        ax.scatter(td, tp, th, color='red', marker='*', s=100, label='Target')

        # If available, plot target from result? Not included in CalculationResult.
        # Users can extend to pass target separately.

        ax.scatter(ds, ps, hs, color='blue', marker='o', s=40, label='Solvents')
        # Annotate points
        for d, p, h, lab in zip(ds, ps, hs, labels):
            ax.text(d, p, h, f" {lab}", fontsize=8)

        ax.set_xlabel('D')
        ax.set_ylabel('P')
        ax.set_zlabel('H')
        ax.legend()

        layout.addWidget(canvas)

        def _save_png() -> None:
            path, _ = QFileDialog.getSaveFileName(dlg, "Save figure", "hsp_3d.png", "PNG Images (*.png)")
            if path:
                fig.savefig(path, dpi=150, bbox_inches='tight')

        btn_png = QPushButton("Save PNG")
        btn_png.clicked.connect(_save_png)
        layout.addWidget(btn_png)

        dlg.resize(700, 560)
        dlg.exec()

    def _save_json(self) -> None:
        if not self._results:
            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Information)
            dlg.setWindowTitle("Nothing to export")
            dlg.setText("No results available to export.")
            dlg.setInformativeText("Run a calculation first, or check that results are present before exporting.")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save results", "solvpred_results.json", "JSON (*.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            records = []
            for r in self._filtered_results:
                d = asdict(r)
                d["hsp_mixture"] = d["hsp_mixture"][:3]
                records.append(d)
            json.dump(records, f, indent=2, ensure_ascii=False)

    def _save_csv(self) -> None:
        if not self._results:
            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Information)
            dlg.setWindowTitle("Nothing to export")
            dlg.setText("No results available to export.")
            dlg.setInformativeText("Run a calculation first, or check that results are present before exporting.")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save results", "solvpred_results.csv", "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["group", "cas", "name", "concentration_pct", "mix_D", "mix_P", "mix_H", "err_D", "err_P", "err_H", "n_solvents", "total_error"])
            for group_idx, r in enumerate(self._filtered_results, start=1):
                mix_d, mix_p, mix_h = r.hsp_mixture[0], r.hsp_mixture[1], r.hsp_mixture[2]
                err_d, err_p, err_h = r.hsp_error[0], r.hsp_error[1], r.hsp_error[2]
                n = len(r.cas_comb)
                total_error = r.get_total_error()
                for cas, conc in zip(r.cas_comb, r.c_mean_norm):
                    name = getattr(self._solvent_info.get(cas), "Name", None) or cas
                    w.writerow([
                        group_idx,
                        cas,
                        name,
                        f"{conc*100:.2f}",
                        f"{mix_d:.4f}",
                        f"{mix_p:.4f}",
                        f"{mix_h:.4f}",
                        f"{err_d:+.4f}",
                        f"{err_p:+.4f}",
                        f"{err_h:+.4f}",
                        n,
                        f"{total_error:.4f}",
                    ])

    def _reset_filters(self) -> None:
        self._filter_solvent.blockSignals(True)
        self._filter_num_solvents.blockSignals(True)
        self._sort_by_error.blockSignals(True)
        self._filter_solvent.clear()
        self._filter_num_solvents.clear()
        self._sort_by_error.setCurrentIndex(0)
        self._filter_solvent.blockSignals(False)
        self._filter_num_solvents.blockSignals(False)
        self._sort_by_error.blockSignals(False)
        self._filtered_results = list(self._results)
        self._update_table(self._filtered_results)

    def _apply_filters(self) -> None:
        filtered_results = self._results

        # Filter by solvent (CAS or name)
        solvent_filter = self._filter_solvent.text().strip().lower()
        if solvent_filter:
            filtered_results = [
                r for r in filtered_results
                if any(
                    solvent_filter in cas.lower()
                    or solvent_filter in (getattr(self._solvent_info.get(cas), "Name", "") or "").lower()
                    for cas in r.cas_comb
                )
            ]

        # Filter by number of solvents
        num_solvents_filter = self._filter_num_solvents.text().strip()
        if num_solvents_filter:
            try:
                num_solvents = int(num_solvents_filter)
                filtered_results = [r for r in filtered_results if len(r.cas_comb) == num_solvents]
            except ValueError:
                pass

        # Sort results
        sort_index = self._sort_by_error.currentIndex()
        if sort_index == 0:  # Sort by total error
            filtered_results.sort(key=lambda r: r.get_total_error())
        elif sort_index == 1:  # Sort by δD
            filtered_results.sort(key=lambda r: abs(r.hsp_error[0]))
        elif sort_index == 2:  # Sort by δP
            filtered_results.sort(key=lambda r: abs(r.hsp_error[1]))
        elif sort_index == 3:  # Sort by δH
            filtered_results.sort(key=lambda r: abs(r.hsp_error[2]))
        self._filtered_results = filtered_results
        self._update_table(filtered_results)

    def _update_table(self, results: list[CalculationResult]) -> None:
        self._table.setRowCount(0)
        for r in results:
            row = self._table.rowCount()
            self._table.insertRow(row)
            cas_lines = []
            for cas_id in r.cas_comb:
                solvent = self._solvent_info.get(cas_id)
                name = getattr(solvent, "Name", None) if solvent else None
                cas_lines.append(f"{cas_id} — {name}" if name else cas_id)
            cas = "\n".join(cas_lines)
            conc = "\n".join([f"{v*100:.2f}%" for v in r.c_mean_norm])
            mix = f"({r.hsp_mixture[0]:.2f}, {r.hsp_mixture[1]:.2f}, {r.hsp_mixture[2]:.2f})"
            err = f"({r.hsp_error[0]:+.3f}, {r.hsp_error[1]:+.3f}, {r.hsp_error[2]:+.3f})"
            n = str(len(r.cas_comb))
            total_error = r.get_total_error()  # Calculate total error

            for col, text in enumerate([cas, conc, mix, err, n, f"{total_error:.3f}"]):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(row, col, item)

            btn = QPushButton("View 3D")
            if self._session is None:
                return
            btn.clicked.connect(lambda _, res=r: self._open_3d_dialog(res, self._session))
            self._table.setCellWidget(row, 6, btn)  # Updated column index for the button

        self._table.resizeColumnsToContents()
        self._table.resizeRowsToContents()

    def _show_solvent_tooltip(self, row: int, column: int) -> None:
        if column != 0:
            self._tooltip.hide()
            return

        item = self._table.item(row, column)
        if not item:
            self._tooltip.hide()
            return

        cas_text = item.text()
        solvent_info = self._session.get_candidates() if self._session else {}
        tooltip_texts = []

        for cas_line in cas_text.splitlines():
            cas = cas_line.split("—")[0].strip()
            solvent = solvent_info.get(cas)
            if solvent:
                tooltip_texts.append(
                    f"CAS: {solvent.CAS}\n"
                    f"Name: {solvent.Name}\n"
                    f"D: {solvent.D}\n"
                    f"P: {solvent.P}\n"
                    f"H: {solvent.H}\n"
                    f"Boiling Point: {solvent.bp}\n"
                    f"Index: {solvent.No}\n"
                    f"IMS Index: {solvent.ims_idx}"
                )

        if tooltip_texts:
            self._tooltip.show_at(QCursor.pos(), "\n\n".join(tooltip_texts))
        else:
            self._tooltip.hide()

    def eventFilter(self, obj, event) -> bool:
        if obj is self._table and event.type() == QEvent.Type.Leave:
            self._tooltip.hide()
        return super().eventFilter(obj, event)

    def hideEvent(self, event) -> None:
        self._tooltip.hide()
        super().hideEvent(event)

