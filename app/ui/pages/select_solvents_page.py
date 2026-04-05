from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QMessageBox,
    QDialog,
    QDialogButtonBox,
    QCheckBox,
    QFormLayout,
    QPushButton,
    QFileDialog,
    QToolTip,
)

from app.api_facade import SetupSession
from app.services import data_service as ds
from app.ui.theme import AppTheme
from app.ui.widgets import h1, h2, PrimaryButton, DangerButton
import app.exceptions as exc
from collections.abc import Callable
from json import JSONDecodeError


class SelectSolventsPage(QWidget):
    def __init__(
        self,
        theme: AppTheme,
        session: SetupSession,
        on_next: Callable[[], None],
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._theme = theme
        self._session = session
        self._on_next = on_next

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        root.addWidget(h1("Select solvents"))

        # Full list filter (always available) + quick actions
        top_row = QHBoxLayout()
        self._browse_filter = QLineEdit()
        self._browse_filter.setPlaceholderText("Filter full list (CAS or Name)…")
        self._browse_filter.setClearButtonEnabled(True)
        self._browse_filter.textChanged.connect(self._refresh_full_list)
        top_row.addWidget(self._browse_filter, 1)

        self._add_default = PrimaryButton("Select default list", theme)
        self._add_default.clicked.connect(self._select_default)
        top_row.addWidget(self._add_default)

        self._add_all = PrimaryButton("Select all", theme)
        self._add_all.clicked.connect(self._select_all)
        top_row.addWidget(self._add_all)

        self._advanced = PrimaryButton("Advanced…", theme)
        self._advanced.clicked.connect(self._open_advanced)
        top_row.addWidget(self._advanced)

        root.addLayout(top_row)

        panes = QHBoxLayout()

        left = QVBoxLayout()
        left.addWidget(h2("All solvents"))
        self._full_list = QListWidget()
        self._full_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._full_list.itemDoubleClicked.connect(self._add_from_double_click)
        self._full_list.setMouseTracking(True)
        self._full_list.itemEntered.connect(lambda _: self._show_solvent_tooltip(_, self._full_list))
        left.addWidget(self._full_list, 1)

        add_btns = QHBoxLayout()
        self._add_selected_btn = PrimaryButton("Add selected", theme)
        self._add_selected_btn.clicked.connect(self._add_selected_from_list)
        add_btns.addWidget(self._add_selected_btn)
        add_btns.addStretch(1)
        left.addLayout(add_btns)

        panes.addLayout(left, 1)

        right = QVBoxLayout()
        right.addWidget(h2("Selected"))
        self._selected = QListWidget()
        self._selected.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._selected.itemDoubleClicked.connect(self._remove_from_double_click)
        self._selected.setMouseTracking(True)
        self._selected.itemEntered.connect(lambda _: self._show_solvent_tooltip(_, self._selected))
        right.addWidget(self._selected, 1)

        btns = QHBoxLayout()
        self._remove = DangerButton("Remove", theme)
        self._remove.clicked.connect(self._remove_selected)
        btns.addWidget(self._remove)

        self._clear = PrimaryButton("Clear", theme)
        self._clear.clicked.connect(self._clear_selection)
        btns.addWidget(self._clear)
        btns.addStretch(1)

        # Add a button to save the current solvent selection to a file
        self._save_selection = PrimaryButton("Save selection", theme)
        self._save_selection.clicked.connect(self._save_current_selection)
        btns.addWidget(self._save_selection)

        self._next = PrimaryButton("Next", theme)
        self._next.clicked.connect(self._next_step)
        self._next.setEnabled(False)
        btns.addWidget(self._next)

        right.addLayout(btns)
        panes.addLayout(right, 1)

        root.addLayout(panes, 1)

        hint = QLabel("Tip: double-click to add/remove one. Use Ctrl/Shift + button to add/remove multiple.")
        hint.setStyleSheet(f"color: {theme.text_muted.name()};")
        root.addWidget(hint)

        # Cache a display-friendly full DB list for browsing.
        self._all_records = list(self._session._raw_db)  # noqa: SLF001 (UI convenience)
        self._refresh_full_list()
        self._refresh_selected()

    # fast-search panel removed; browse filter handles search across full list

    def _add_from_double_click(self, item: QListWidgetItem) -> None:
        cas = item.data(Qt.ItemDataRole.UserRole)
        if not cas:
            return
        self._session.select(str(cas).strip())
        self._refresh_selected()

    def _remove_from_double_click(self, item: QListWidgetItem) -> None:
        cas = item.data(Qt.ItemDataRole.UserRole)
        if not cas:
            return
        self._session.deselect(str(cas).strip())
        self._refresh_selected()

    def _add_selected_from_list(self, _item: QListWidgetItem | None = None) -> None:
        items = self._full_list.selectedItems()
        if not items:
            return
        invalid = []
        for item in items:
            cas = item.data(Qt.ItemDataRole.UserRole)
            if not cas:
                continue
            cas = str(cas).strip()
            if self._session.get_solvent(cas) is None:
                invalid.append(cas)
                continue
            self._session.select(cas)
        if invalid:
            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Warning)
            dlg.setWindowTitle("Some solvents skipped")
            dlg.setText("Some selected solvents are not available in the database and were skipped.")
            dlg.setInformativeText("Skipped CAS: " + ", ".join(invalid[:10]) + ("..." if len(invalid) > 10 else ""))
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()
        self._refresh_selected()

    def _refresh_full_list(self) -> None:
        self._full_list.clear()
        query = (self._browse_filter.text() or "").strip().lower()
        # Keep it responsive: cap displayed items.
        shown = 0
        for rec in self._all_records:
            cas = str(rec.get("CAS", "")).strip()
            name = str(rec.get("Name", "")).strip()
            if not cas:
                continue
            if query:
                hay = f"{cas} {name}".lower()
                if query not in hay:
                    continue
            d = rec.get("D", "-")
            p = rec.get("P", "-")
            h = rec.get("H", "-")
            title = f"{cas} — {name}  (D={d}, P={p}, H={h})"
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, cas)
            self._full_list.addItem(item)
            shown += 1
            if shown >= 800:
                self._full_list.addItem(QListWidgetItem("… list truncated (refine filter to see more)."))
                break

    def _select_all(self) -> None:
        # Select everything from DB map (use internal raw list for convenience)
        invalid = []
        for rec in self._all_records:
            cas = rec.get("CAS")
            if not cas:
                continue
            cas = str(cas).strip()
            if self._session.get_solvent(cas) is None:
                invalid.append(cas)
                continue
            self._session.select(cas)
        if invalid:
            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Warning)
            dlg.setWindowTitle("Some solvents skipped")
            dlg.setText("Some solvents could not be selected because they are not available in the database.")
            dlg.setInformativeText(
                "Skipped CAS: " + ", ".join(invalid[:10]) + ("..." if len(invalid) > 10 else "")
            )
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()
        self._refresh_selected()

    def _select_default(self) -> None:
        try:
            default_recs = ds.load_default_candidates()
            invalid = []
            for rec in default_recs:
                cas = str(rec.get("CAS", "")).strip()
                if not cas:
                    continue
                if self._session.get_solvent(cas) is None:
                    invalid.append(cas)
                    continue
                self._session.select(cas)
            if invalid:
                dlg = QMessageBox(self)
                dlg.setIcon(QMessageBox.Icon.Warning)
                dlg.setWindowTitle("Default list partial")
                dlg.setText("Some default solvents were not found and were skipped.")
                dlg.setInformativeText("Skipped CAS: " + ", ".join(invalid[:10]) + ("..." if len(invalid) > 10 else ""))
                dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
                dlg.exec()
        except (FileNotFoundError, OSError, JSONDecodeError) as e:
            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Warning)
            dlg.setWindowTitle("Default list unavailable")
            dlg.setText("Could not load the default solvent list.")
            dlg.setInformativeText(f"The default candidates file may be missing, unreadable, or corrupted.\n\n{type(e).__name__}: {e}")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()
        self._refresh_selected()

    def _remove_selected(self) -> None:
        items = self._selected.selectedItems()
        if not items:
            return
        for item in items:
            cas = item.data(Qt.ItemDataRole.UserRole)
            if cas:
                self._session.deselect(str(cas))
        self._refresh_selected()

    def _clear_selection(self) -> None:
        # Clear all selected solvents
        if not self._session.selected:
            return
        self._session.clear_selection()
        self._refresh_selected()

    def _refresh_selected(self) -> None:
        self._selected.clear()
        for cas in self._session.selected:
            s = self._session.get_solvent(cas)
            name = s.Name if s else "-"
            item = QListWidgetItem(f"{cas} — {name}")
            item.setData(Qt.ItemDataRole.UserRole, cas)
            self._selected.addItem(item)
        self._next.setEnabled(len(self._session.selected) > 0)

    def _next_step(self) -> None:
        if not self._session.selected:
            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Warning)
            dlg.setWindowTitle("No solvents selected")
            dlg.setText("You must select at least one solvent to continue.")
            dlg.setInformativeText("Choose solvents from the 'All solvents' list or use 'Select default list'.")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()
            return
        self._session.finalize_selection()
        self._on_next()

    def reset_ui(self) -> None:
        """Reset the selection page UI to reflect a fresh session.

        This clears filters and selected lists and reloads the full DB.
        """
        # Clear filter
        self._browse_filter.setText("")
        # Rebind records
        self._all_records = list(self._session._raw_db)
        self._refresh_full_list()
        # Clear any selection list
        self._selected.clear()
        self._refresh_selected()

    def _open_advanced(self) -> None:
        # Present a small action dialog that bundles custom-add and user-DB management
        dlg = QDialog(self)
        dlg.setWindowTitle("Advanced: Custom solvents & User Database")
        v = QVBoxLayout(dlg)

        info = QLabel("Advanced actions: add a custom solvent, load a user database, or manage a user database file.")
        info.setWordWrap(True)
        v.addWidget(info)

        btn_add = PrimaryButton("Add custom solvent...", self._theme)
        btn_add.clicked.connect(lambda: self._open_add_custom(dlg))
        v.addWidget(btn_add)

        btn_load_default = PrimaryButton("Load solvents from file...", self._theme)
        # btn_load_default.clicked.connect(lambda: self._load_user_db(None, dlg))
        btn_load_default.clicked.connect(lambda: self._pick_and_load_user_solvent_selection(dlg))
        v.addWidget(btn_load_default)

        btn_load_file = PrimaryButton("Load user database from file...", self._theme)
        btn_load_file.clicked.connect(lambda: self._pick_and_load_user_db(dlg))
        v.addWidget(btn_load_file)

        btn_manage = PrimaryButton("Manage user database...", self._theme)
        btn_manage.clicked.connect(lambda: self._open_user_db_manager(dlg))
        v.addWidget(btn_manage)

        close_btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn.rejected.connect(dlg.reject)
        v.addWidget(close_btn)

        dlg.exec()

    def _open_add_custom(self, parent_dialog: QDialog | None = None) -> None:
        dlg = _AddCustomSolventDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        record, persist, user_db_path = dlg.get_record()
        # First register into current session (non-mutating to builtins)
        ok, msg = self._session.register_custom_solvent(record, persist=False)
        if not ok:
            m = QMessageBox(self)
            m.setIcon(QMessageBox.Icon.Warning)
            m.setWindowTitle("Cannot add solvent")
            m.setText("Failed to add custom solvent.")
            m.setInformativeText(msg)
            m.setStandardButtons(QMessageBox.StandardButton.Ok)
            m.exec()
            return
        # If user requested persistence, try to save into chosen file (or default)
        if persist:
            saved = False
            save_msg = ""
            try:
                if user_db_path:
                    # Append to user-chosen path using data_service helper
                    ds.append_user_solvent_to_path(record, user_db_path)
                    saved = True
                else:
                    # Use default behavior
                    ds.add_user_solvent(record)
                    saved = True
            except (OSError, JSONDecodeError, TypeError, ValueError) as e:
                save_msg = str(e)
            if not saved:
                m = QMessageBox(self)
                m.setIcon(QMessageBox.Icon.Warning)
                m.setWindowTitle("Persistence failed")
                m.setText("Custom solvent added to session but could not be saved to user database.")
                if user_db_path:
                    m.setInformativeText(f"Attempted to save to: {user_db_path}\nError: {save_msg}\nYou can choose to save to another path or let the app save to the default user database (~/.solvpred_app/user_solvents.json).")
                else:
                    m.setInformativeText("Failed to save to the default user database (~/.solvpred_app/user_solvents.json).")
                m.setStandardButtons(QMessageBox.StandardButton.Ok)
                m.exec()
        # refresh DB browsing list
        self._all_records = list(self._session._raw_db)  # noqa: SLF001
        self._refresh_full_list()
        m = QMessageBox(self)
        m.setIcon(QMessageBox.Icon.Information)
        m.setWindowTitle("Custom solvent added")
        m.setText("Custom solvent added to current session.")
        m.setInformativeText("You can now select it from the list.")
        m.setStandardButtons(QMessageBox.StandardButton.Ok)
        m.exec()

    def _open_user_db(self) -> None:
        # Deprecated: merged into Advanced dialog
        return

    def _load_user_db(self, path: str | None, parent_dialog: QDialog | None = None) -> None:
        ok, msg = self._session.load_user_db(path)
        if not ok:
            m = QMessageBox(self)
            m.setIcon(QMessageBox.Icon.Warning)
            m.setWindowTitle("Load failed")
            m.setText("Could not load user database")
            m.setInformativeText(msg)
            m.setStandardButtons(QMessageBox.StandardButton.Ok)
            m.exec()
            return
        # Refresh UI lists
        self._all_records = list(self._session._raw_db)
        self._refresh_full_list()
        m = QMessageBox(self)
        m.setIcon(QMessageBox.Icon.Information)
        m.setWindowTitle("User database loaded")
        m.setText(msg)
        m.setStandardButtons(QMessageBox.StandardButton.Ok)
        m.exec()
        if parent_dialog:
            parent_dialog.accept()

    def _pick_and_load_user_db(self, parent_dialog: QDialog | None = None) -> None:
        fname, _ = QFileDialog.getOpenFileName(self, "Select user database file", str(ds._USER_DB), "JSON files (*.json);;All files (*.*)")
        if not fname:
            return
        self._load_user_db(fname, parent_dialog)

    def _open_user_db_manager(self, parent_dialog: QDialog | None = None) -> None:
        mgr = _UserDBManagerDialog(self)
        mgr.exec()

    def _load_user_solvent_selection(self, path : str | None = None,parent_dialog: QDialog | None = None) -> None:
        ok, msg = self._session.load_user_solvent_selection(path)
        if not ok:
            m = QMessageBox(self)
            m.setIcon(QMessageBox.Icon.Warning)
            m.setWindowTitle("Load failed")
            m.setText("Could not load user database")
            m.setInformativeText(msg)
            m.setStandardButtons(QMessageBox.StandardButton.Ok)
            m.exec()
            return
        # Refresh UI lists
        self._all_records = list(self._session._raw_db)
        self._refresh_full_list()
        self._refresh_selected()
        m = QMessageBox(self)
        m.setIcon(QMessageBox.Icon.Information)
        m.setWindowTitle("User database loaded")
        m.setText(msg)
        m.setStandardButtons(QMessageBox.StandardButton.Ok)
        m.exec()
        if parent_dialog:
            parent_dialog.accept()
    
    def _pick_and_load_user_solvent_selection(self, parent_dialog: QDialog | None = None) -> None:
        fname, _ = QFileDialog.getOpenFileName(self, "Select user database file", str(ds._USER_SELECT), "JSON files (*.json);;All files (*.*)")
        if not fname:
            return
        self._load_user_solvent_selection(fname, parent_dialog)

    def _save_current_selection(self) -> None:
        # Prompt user to select a file to save the current selection
        path, _ = QFileDialog.getSaveFileName(self, 
                "Save solvent selection", 
                str(ds._USER_SELECT_DIR), 
                "JSON Files (*.json)")
        if not path:
            return
        try:
            # Save the current selection to the chosen file
            selected_solvents = [
                {
                    "CAS": cas,
                    "Name": self._session.get_solvent(cas).Name  # type: ignore
                }
                for cas in self._session.selected
            ]
            ds.save_user_solvents_to_path(path, selected_solvents)

            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Information)
            dlg.setWindowTitle("Selection saved")
            dlg.setText("The current solvent selection has been saved successfully.")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()
        except Exception as e:
            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Warning)
            dlg.setWindowTitle("Save error")
            dlg.setText("Could not save the solvent selection to the file.")
            dlg.setInformativeText(f"An error occurred: {type(e).__name__}: {e}")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()

    def _show_solvent_tooltip(self, item: QListWidgetItem, where: QWidget) -> None:
        cas = item.data(Qt.ItemDataRole.UserRole)

        solvent = self._session.get_solvent(cas)
        if not solvent:
            return
        tooltip_text = (
            f"CAS: {solvent.CAS}\n"
            f"Name: {solvent.Name}\n"
            f"D: {solvent.D}\n"
            f"P: {solvent.P}\n"
            f"H: {solvent.H}\n"
            f"Boiling Point: {solvent.bp}\n"
            f"Index: {solvent.No}\n"
            f"IMS Index: {solvent.ims_idx}"
        )
        QToolTip.showText(QCursor.pos(), tooltip_text, where)

        def keep_tooltip_visible():
            QToolTip.showText(QCursor.pos(), tooltip_text, where)

        timer = QTimer(self)
        timer.timeout.connect(keep_tooltip_visible)
        timer.setSingleShot(True)
        timer.start(5000)

class _AddCustomSolventDialog(QDialog):
    def __init__(self, parent=None, initial: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Add custom solvent")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._cas = QLineEdit(); self._cas.setPlaceholderText("e.g. 64-17-5")
        self._name = QLineEdit(); self._name.setPlaceholderText("Solvent name")
        self._d = QLineEdit(); self._d.setPlaceholderText("D")
        self._p = QLineEdit(); self._p.setPlaceholderText("P")
        self._h = QLineEdit(); self._h.setPlaceholderText("H")
        self._bp = QLineEdit(); self._bp.setPlaceholderText("Optional")

        # If initial data provided, prefill fields
        if initial:
            self._cas.setText(str(initial.get('CAS', '')))
            self._name.setText(str(initial.get('Name', '')))
            if initial.get('D') is not None:
                self._d.setText(str(initial.get('D')))
            if initial.get('P') is not None:
                self._p.setText(str(initial.get('P')))
            if initial.get('H') is not None:
                self._h.setText(str(initial.get('H')))
            if initial.get('bp') is not None:
                self._bp.setText(str(initial.get('bp')))

        form.addRow("CAS", self._cas)
        form.addRow("Name", self._name)
        form.addRow("D", self._d)
        form.addRow("P", self._p)
        form.addRow("H", self._h)
        form.addRow("Boiling point", self._bp)

        layout.addLayout(form)

        self._persist = QCheckBox("Save to user database (persist)")
        layout.addWidget(self._persist)

        # Allow user to choose an alternate user DB file to persist into
        self._user_db_btn = QPushButton("Choose user database file...")
        self._user_db_btn.clicked.connect(self._choose_user_db)
        layout.addWidget(self._user_db_btn)

        self._user_db_label = QLabel("(using default user database)")
        self._user_db_label.setWordWrap(True)
        layout.addWidget(self._user_db_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_record(self) -> tuple[dict, bool, str | None]:
        rec: dict = {
            'CAS': self._cas.text().strip(),
            'Name': self._name.text().strip(),
            'D': float(self._d.text().strip()) if self._d.text().strip() else None,
            'P': float(self._p.text().strip()) if self._p.text().strip() else None,
            'H': float(self._h.text().strip()) if self._h.text().strip() else None,
        }
        bp_txt = self._bp.text().strip()
        if bp_txt:
            try:
                rec['bp'] = float(bp_txt)
            except (TypeError, ValueError):
                rec['bp'] = bp_txt
        return rec, bool(self._persist.isChecked()), getattr(self, '_user_db_path', None)

    def _choose_user_db(self) -> None:
        # Let user pick an existing file or choose a new file to create
        fname, _ = QFileDialog.getSaveFileName(self, "Choose or create user database file", str(ds._USER_DB))
        if not fname:
            return
        self._user_db_path = fname
        self._user_db_label.setText(f"User database: {fname}")



class _UserDBManagerDialog(QDialog):
    """Dialog to view/edit a user DB file (JSON list of records)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage user database")
        self._records: list[dict] = []
        self._path: str | None = None

        layout = QVBoxLayout(self)

        hl = QHBoxLayout()
        pick_btn = QPushButton("Choose user database file...")
        pick_btn.clicked.connect(self._choose_file)
        hl.addWidget(pick_btn)
        self._path_label = QLabel("No file selected")
        hl.addWidget(self._path_label, 1)
        layout.addLayout(hl)

        self._list = QListWidget()
        layout.addWidget(self._list, 1)

        btns = QHBoxLayout()
        add_btn = PrimaryButton("Add", parent._theme)  # type: ignore
        add_btn.clicked.connect(self._add_record)
        btns.addWidget(add_btn)
        edit_btn = PrimaryButton("Edit", parent._theme)  # type: ignore
        edit_btn.clicked.connect(self._edit_record)
        btns.addWidget(edit_btn)
        del_btn = DangerButton("Delete", parent._theme)  # type: ignore
        del_btn.clicked.connect(self._delete_record)
        btns.addWidget(del_btn)
        btns.addStretch(1)
        save_btn = PrimaryButton("Save to file", parent._theme)  # type: ignore
        save_btn.clicked.connect(self._save_to_file)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)

    def _choose_file(self) -> None:
        fname, _ = QFileDialog.getOpenFileName(self, "Open user database file", str(ds._USER_DB), "JSON files (*.json);;All files (*.*)")
        if not fname:
            return
        self._path = fname
        self._path_label.setText(fname)
        self._records = ds.load_user_solvents_from_path(fname)
        self._refresh_list()

    def _refresh_list(self) -> None:
        self._list.clear()
        for r in self._records:
            cas = r.get('CAS', '')
            name = r.get('Name', '')
            item = QListWidgetItem(f"{cas} — {name}")
            self._list.addItem(item)

    def _add_record(self) -> None:
        dlg = _AddCustomSolventDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        rec, _, _ = dlg.get_record()
        self._records.append(rec)
        self._refresh_list()

    def _edit_record(self) -> None:
        sel = self._list.currentRow()
        if sel < 0 or sel >= len(self._records):
            return
        rec = self._records[sel]
        dlg = _AddCustomSolventDialog(self, initial=rec)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new_rec, _, _ = dlg.get_record()
        self._records[sel] = new_rec
        self._refresh_list()

    def _delete_record(self) -> None:
        sel = self._list.currentRow()
        if sel < 0 or sel >= len(self._records):
            return
        del self._records[sel]
        self._refresh_list()

    def _save_to_file(self) -> None:
        if not self._path:
            fname, _ = QFileDialog.getSaveFileName(self, "Save user database to", str(ds._USER_DB), "JSON files (*.json);;All files (*.*)")
            if not fname:
                return
            self._path = fname
            self._path_label.setText(fname)
        try:
            ds.save_user_solvents_to_path(self._path, self._records)  # type: ignore 
            m = QMessageBox(self)
            m.setIcon(QMessageBox.Icon.Information)
            m.setWindowTitle("Saved")
            m.setText(f"Saved {len(self._records)} records to {self._path}")
            m.setStandardButtons(QMessageBox.StandardButton.Ok)
            m.exec()
        except (OSError, JSONDecodeError, TypeError, ValueError) as e:
            m = QMessageBox(self)
            m.setIcon(QMessageBox.Icon.Warning)
            m.setWindowTitle("Save failed")
            m.setText(str(e))
            m.setStandardButtons(QMessageBox.StandardButton.Ok)
            m.exec()
