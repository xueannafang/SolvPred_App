from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDoubleValidator, QIntValidator
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QGroupBox,
    QMessageBox,
    QSpinBox,
    QDoubleSpinBox,
    QFileDialog,
)

from app.api_facade import SetupSession
from app.models import HSPTarget
from app.ui.theme import AppTheme
from app.ui.widgets import h1, h2, PrimaryButton


class ParamsPage(QWidget):
    def __init__(
        self,
        theme: AppTheme,
        session: SetupSession,
        on_back,
        on_next,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._theme = theme
        self._session = session
        self._on_back = on_back
        self._on_next = on_next

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        root.addWidget(h1("Target HSP + parameters"))

        form_box = QGroupBox("Target HSP")
        form = QFormLayout(form_box)

        # Use line edits with validators instead of spinboxes to avoid accidental
        # mouse-wheel changes.
        self._d = QLineEdit()
        self._d.setPlaceholderText("0.0")
        self._d.setText("0.0")
        self._d.setValidator(QDoubleValidator(-1e9, 1e9, 6))

        self._p = QLineEdit()
        self._p.setPlaceholderText("0.0")
        self._p.setText("0.0")
        self._p.setValidator(QDoubleValidator(-1e9, 1e9, 6))

        self._h = QLineEdit()
        self._h.setPlaceholderText("0.0")
        self._h.setText("0.0")
        self._h.setValidator(QDoubleValidator(-1e9, 1e9, 6))

        # Add HSP inputs and small hint labels for real-time range feedback
        self._d_hint = QLineEdit()  # temporary widget; will replace with QLabel-like usage
        self._d_hint.setReadOnly(True)
        self._d_hint.setFrame(False)
        self._d_hint.setStyleSheet(f"color: {self._theme.text_muted.name()}; background: transparent;")

        self._p_hint = QLineEdit()
        self._p_hint.setReadOnly(True)
        self._p_hint.setFrame(False)
        self._p_hint.setStyleSheet(f"color: {self._theme.text_muted.name()}; background: transparent;")

        self._h_hint = QLineEdit()
        self._h_hint.setReadOnly(True)
        self._h_hint.setFrame(False)
        self._h_hint.setStyleSheet(f"color: {self._theme.text_muted.name()}; background: transparent;")

        form.addRow("δD", self._d)
        form.addRow("", self._d_hint)
        form.addRow("δP", self._p)
        form.addRow("", self._p_hint)
        form.addRow("δH", self._h)
        form.addRow("", self._h_hint)
        root.addWidget(form_box)

        adv = QGroupBox("Parameters")
        adv_form = QFormLayout(adv)

        self._err_d = QLineEdit(); self._err_d.setText("2.0"); self._err_d.setValidator(QDoubleValidator(0.0, 1e6, 6))
        self._err_p = QLineEdit(); self._err_p.setText("2.0"); self._err_p.setValidator(QDoubleValidator(0.0, 1e6, 6))
        self._err_h = QLineEdit(); self._err_h.setText("2.0"); self._err_h.setValidator(QDoubleValidator(0.0, 1e6, 6))

        self._threshold = QLineEdit(); self._threshold.setText("0.01"); self._threshold.setValidator(QDoubleValidator(0.0, 1.0, 6))

        self._max_cosolvent = QLineEdit(); self._max_cosolvent.setText("2"); self._max_cosolvent.setValidator(QIntValidator(2, 6))

        self._n_perturb = QLineEdit(); self._n_perturb.setText("50"); self._n_perturb.setValidator(QIntValidator(1, 2000))

        self._perturb_std = QLineEdit(); self._perturb_std.setText("0.1"); self._perturb_std.setValidator(QDoubleValidator(0.0, 10.0, 6))

        self._temperature = QLineEdit(); self._temperature.setText("25.0"); self._temperature.setValidator(QDoubleValidator(-200.0, 500.0, 4))

        adv_form.addRow("Acceptable error δD", self._err_d)
        adv_form.addRow("Acceptable error δP", self._err_p)
        adv_form.addRow("Acceptable error δH", self._err_h)
        adv_form.addRow("Redundant concentration threshold", self._threshold)
        adv_form.addRow("Max co-solvents", self._max_cosolvent)
        adv_form.addRow("# target perturbations", self._n_perturb)
        adv_form.addRow("Perturb std", self._perturb_std)
        adv_form.addRow("Temperature (°C)", self._temperature)

        root.addWidget(adv)

        nav = QHBoxLayout()
        self._back_btn = PrimaryButton("Back", theme)
        self._back_btn.clicked.connect(self._on_back)
        nav.addWidget(self._back_btn)
        # Add reset before the run button
        nav.addStretch(1)


        # Add buttons to load and save parameter setups
        self._load_params_btn = PrimaryButton("Load", theme)
        self._load_params_btn.clicked.connect(self._load_params_from_file)
        nav.addWidget(self._load_params_btn)

        self._save_params_btn = PrimaryButton("Save", theme)
        self._save_params_btn.clicked.connect(self._save_params_to_file)
        nav.addWidget(self._save_params_btn)

        self._reset_btn = PrimaryButton("Reset", theme)
        self._reset_btn.clicked.connect(self._reset_defaults)
        nav.addWidget(self._reset_btn)

        self._next_btn = PrimaryButton("Run", theme)
        self._next_btn.clicked.connect(self._save_and_next)
        nav.addWidget(self._next_btn)

        root.addLayout(nav)

        # Connect live validation handlers for HSP inputs
        self._d.textChanged.connect(self._on_hsp_changed)
        self._p.textChanged.connect(self._on_hsp_changed)
        self._h.textChanged.connect(self._on_hsp_changed)

    def _parse_float(self, widget: QLineEdit, default: float = 0.0) -> float | None:
        try:
            txt = widget.text().strip()
            if txt == "":
                return default
            return float(txt)
        except (TypeError, ValueError):
            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Warning)
            dlg.setWindowTitle("Invalid input")
            dlg.setText("Please enter a valid number.")
            dlg.setInformativeText(f"Invalid value: {widget.text()}")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()
            return None

    def _parse_int(self, widget: QLineEdit, default: int = 0) -> int | None:
        try:
            txt = widget.text().strip()
            if txt == "":
                return default
            return int(txt)
        except (TypeError, ValueError):
            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Warning)
            dlg.setWindowTitle("Invalid input")
            dlg.setText("Please enter a valid integer.")
            dlg.setInformativeText(f"Invalid value: {widget.text()}")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()
            return None

    def showEvent(self, event) -> None:
        # Update warnings whenever page becomes visible
        super().showEvent(event)
        self._update_hsp_warnings()

    def _on_hsp_changed(self, _=None) -> None:
        # Live input change -- update warnings
        self._update_hsp_warnings()

    def _compute_hsp_ranges(self) -> dict:
        # Compute min/max for D/P/H from current selection (use selected list)
        ranges = { 'D': (None, None), 'P': (None, None), 'H': (None, None) }
        cas_list = list(self._session.selected)
        if not cas_list:
            return ranges
        vals = { 'D': [], 'P': [], 'H': [] }
        for cas in cas_list:
            s = self._session.get_solvent(cas)
            if not s:
                continue
            # These values are expected to be numeric for valid solvents.
            vals['D'].append(float(s.D))
            vals['P'].append(float(s.P))
            vals['H'].append(float(s.H))
        for k in vals:
            if vals[k]:
                ranges[k] = (min(vals[k]), max(vals[k]))
        return ranges

    def _update_hsp_warnings(self) -> None:
        ranges = self._compute_hsp_ranges()

        def update_widget(widget_hint, comp_key, widget_val_str):
            lo, hi = ranges.get(comp_key, (None, None))
            txt = widget_val_str.strip()
            if lo is None or hi is None:
                widget_hint.setText("No solvents selected to compute range.")
                widget_hint.setStyleSheet(f"color: {self._theme.text_muted.name()}; background: transparent;")
                return
            try:
                val = float(txt) if txt != "" else None
            except (TypeError, ValueError):
                widget_hint.setText(f"Invalid number; expected between {lo:.2f} and {hi:.2f}.")
                widget_hint.setStyleSheet(f"color: {self._theme.danger.name()}; background: transparent;")
                return
            if val is None:
                widget_hint.setText(f"Recommended range: {lo:.2f} — {hi:.2f}")
                widget_hint.setStyleSheet(f"color: {self._theme.text_muted.name()}; background: transparent;")
                return
            if val < lo or val > hi:
                widget_hint.setText(f"Out of range: expected {lo:.2f} — {hi:.2f}")
                widget_hint.setStyleSheet(f"color: {self._theme.danger.name()}; background: transparent;")
            else:
                widget_hint.setText(f"In range: {lo:.2f} — {hi:.2f}")
                widget_hint.setStyleSheet(f"color: {self._theme.text_muted.name()}; background: transparent;")

        update_widget(self._d_hint, 'D', self._d.text())
        update_widget(self._p_hint, 'P', self._p.text())
        update_widget(self._h_hint, 'H', self._h.text())

    def _save_and_next(self) -> None:
        d = self._parse_float(self._d, 0.0)
        p = self._parse_float(self._p, 0.0)
        h = self._parse_float(self._h, 0.0)
        threshold = self._parse_float(self._threshold, 0.01)
        err_d = self._parse_float(self._err_d, 2.0)
        err_p = self._parse_float(self._err_p, 2.0)
        err_h = self._parse_float(self._err_h, 2.0)
        max_cosolvent = self._parse_int(self._max_cosolvent, 2)
        n_perturb = self._parse_int(self._n_perturb, 50)
        perturb_std = self._parse_float(self._perturb_std, 0.1)
        temperature = self._parse_float(self._temperature, 25.0)

        target = HSPTarget(
            D=float(d),
            P=float(p),
            H=float(h),
            threshold=float(threshold),
            max_cosolvent=int(max_cosolvent),
            n_perturb=int(n_perturb),
            perturb_std=float(perturb_std),
            temperature=float(temperature),
            err_d=float(err_d),
            err_p=float(err_p),
            err_h=float(err_h),
        )
        self._session.set_hsp_target(target)
        # proceed to next step
        self._on_next()
        self._on_next()

    def _restore_from_snapshot(self, snap: dict) -> None:
        # Apply snapshot values to widgets
        self._d.setText(str(float(snap.get('D', 0.0))))
        self._p.setText(str(float(snap.get('P', 0.0))))
        self._h.setText(str(float(snap.get('H', 0.0))))
        self._err_d.setText(str(float(snap.get('err_d', 2.0))))
        self._err_p.setText(str(float(snap.get('err_p', 2.0))))
        self._err_h.setText(str(float(snap.get('err_h', 2.0))))
        self._threshold.setText(str(float(snap.get('threshold', 0.01))))
        self._max_cosolvent.setText(str(int(snap.get('max_cosolvent', 2))))
        self._n_perturb.setText(str(int(snap.get('n_perturb', 50))))
        self._perturb_std.setText(str(float(snap.get('perturb_std', 0.1))))
        self._temperature.setText(str(float(snap.get('temperature', 25.0))))

    def _reset_defaults(self) -> None:
        # Reset UI widgets to recommended defaults
        defaults = {
            'D': 0.0, 'P': 0.0, 'H': 0.0,
            'err_d': 2.0, 'err_p': 2.0, 'err_h': 2.0,
            'threshold': 0.01, 'max_cosolvent': 2,
            'n_perturb': 50, 'perturb_std': 0.1, 'temperature': 25.0,
        }
        # apply defaults to the UI
        self._restore_from_snapshot(defaults)

    def _load_params_from_file(self) -> None:
        from app.services.data_service import _USER_PARAMS_DIR, load_params_from_path
        path, _ = QFileDialog.getOpenFileName(self, "Load parameters", str(_USER_PARAMS_DIR), "JSON Files (*.json)")
        if not path:
            return

        try:
            params = load_params_from_path(path)
            self._d.setText(str(params.get("D", "0.0")))
            self._p.setText(str(params.get("P", "0.0")))
            self._h.setText(str(params.get("H", "0.0")))
            self._err_d.setText(str(params.get("err_d", "2.0")))
            self._err_p.setText(str(params.get("err_p", "2.0")))
            self._err_h.setText(str(params.get("err_h", "2.0")))
            self._threshold.setText(str(params.get("threshold", "0.01")))
            self._max_cosolvent.setText(str(params.get("max_cosolvent", "2")))
            self._n_perturb.setText(str(params.get("n_perturb", "50")))
            self._perturb_std.setText(str(params.get("perturb_std", "0.1")))
            self._temperature.setText(str(params.get("temperature", "25.0")))

            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Information)
            dlg.setWindowTitle("Parameters loaded")
            dlg.setText("Parameters have been successfully loaded from the file.")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()
        except Exception as e:
            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Warning)
            dlg.setWindowTitle("Load error")
            dlg.setText("Could not load parameters from the file.")
            dlg.setInformativeText(f"An error occurred: {type(e).__name__}: {e}")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()

    def _save_params_to_file(self) -> None:
        from app.services.data_service import _USER_PARAMS_DIR, save_params_to_path
        path, _ = QFileDialog.getSaveFileName(self, "Save parameters", str(_USER_PARAMS_DIR), "JSON Files (*.json)")
        if not path:
            return

        try:
            params = {
                "D": self._d.text(),
                "P": self._p.text(),
                "H": self._h.text(),
                "err_d": self._err_d.text(),
                "err_p": self._err_p.text(),
                "err_h": self._err_h.text(),
                "threshold": self._threshold.text(),
                "max_cosolvent": self._max_cosolvent.text(),
                "n_perturb": self._n_perturb.text(),
                "perturb_std": self._perturb_std.text(),
                "temperature": self._temperature.text(),
            }
            save_params_to_path(path, params)

            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Information)
            dlg.setWindowTitle("Parameters saved")
            dlg.setText("Parameters have been successfully saved to the file.")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()
        except Exception as e:
            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Warning)
            dlg.setWindowTitle("Save error")
            dlg.setText("Could not save parameters to the file.")
            dlg.setInformativeText(f"An error occurred: {type(e).__name__}: {e}")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()
