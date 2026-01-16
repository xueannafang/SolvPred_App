from dataclasses import asdict

from app.models import HSPTarget, PContext, CalculationResult, Solvent
from app.services import data_service as ds
from app.exceptions import EmptyHSPTarget, EmptySolventSelection

from collections.abc import Callable

class SetupSession:
    """Simple in-memory session to manage candidate solvents.

    The UI can create a session, call `search`, `select`, `deselect`,
    `apply_filter`, and finally `finalize()` to get a list of CAS to
    pass into the calculation stage.
    """
    def __init__(self):
        # Load built-in database only. User DB will be loaded on demand.
        raw_db = ds.load_db()
        self._raw_db: list[dict] = raw_db  
        self._db_map: dict[str, Solvent] = ds.build_solvent_map(raw_db) 
        # Step 1: selected CAS list, this include select/deselect/apply_filter operations
        self.selected: list[str] = []
        # This should only be set after finalize_selection() as confirmation
        self.candidates: dict[str, Solvent] | None = None  
        # TODO: User may occasionally want to go back to step 1 to adjust selection
        # Should prepare for that, but only in the UI layer. 
        # Just recall finalize_selection() afterwards.
        # Step 2: HSP target setup
        self.hsp_target: HSPTarget | None = None
        self._is_finalized: bool = False

    def search(self, key: str, limit: int = 50) -> list[Solvent]:
        # TODO: not sure search through raw db or through db_map
        return ds.search_solvents(self._raw_db, key, limit=limit)

    def get_solvent(self, cas: str) -> Solvent | None:
        return ds.get_solvent_by_cas(self._db_map, cas)

    def select(self, cas: str) -> None:
        if cas in self._db_map and cas not in self.selected:
            self.selected.append(cas)

    def deselect(self, cas: str) -> None:
        if cas in self.selected:
            self.selected.remove(cas)

    def apply_filter(self, filter_func: Callable[[Solvent], bool]) -> None:
        # TODO: filter functions come from logic.filters
        filtered = filter(lambda cas: filter_func(self._db_map[cas]), self.selected)
        self.selected = list(filtered)

    def get_selected(self) -> list[str]:
        # TODO: Exception for UI layer pop up warnings
        if not self.selected:
            raise EmptySolventSelection
        return self.selected

    def get_candidates(self) -> dict[str, Solvent]:
        # TODO: Exception for UI layer pop up warnings
        if not self.selected:
            raise EmptySolventSelection
        if self.candidates is not None:
            return self.candidates
        candidates = {cas: self._db_map[cas] for cas in self.selected}
        return candidates
    
    def finalize_selection(self):
        # Confirm current selection as candidates for calculation
        # TODO: User may want to go back to selection step, should handle that in UI layer
        # Just recall finalize_selection() afterwards.
        if not self.selected:
            raise EmptySolventSelection
        self.candidates = self.get_candidates()

    def clear_selection(self) -> None:
        """Clear current selection and candidates."""
        self.selected = []
        self.candidates = None

    def _get_candidates_hsp_range(self, which: str) -> tuple[float, float]:
        # Internal helper to get min/max of selected candidates for a given HSP component
        if self.candidates is None:
            raise EmptySolventSelection
        if which.upper() not in {'H', 'P', 'D'}:
            raise ValueError(f"Invalid HSP component: {which!r}, expected one of 'H', 'P', 'D'")
        values = [getattr(s, which.upper()) for s in self.candidates.values()]
        return min(values), max(values)

    def set_hsp_target(self, target: HSPTarget) -> None:
        self.hsp_target = target

    def _validate_hsp_target(self, which: str) -> bool:
        # TODO: Should call this each time when a HSP target value is set
        # UI layer use this to give feedback to user in-time to suggest adjustments
        # The feedback should be specific to which component is out of range on what direction.
        # Better call the range function above to get min/max
        if self.hsp_target is None:
            raise EmptyHSPTarget
        if which.upper() not in {'H', 'P', 'D'}:
            raise ValueError(f"Invalid HSP component: {which!r}, expected one of 'H', 'P', 'D'")
        fmin, fmax = self._get_candidates_hsp_range(which)
        value = getattr(self.hsp_target, which.upper())
        if not (fmin <= value <= fmax):
            return False
        return True

    def get_hsp_target(self) -> HSPTarget:
        if self.hsp_target is not None:
            return self.hsp_target
        raise EmptyHSPTarget

    def finalize(self) -> PContext:
        # Finalize setup session into a pipeline context
        selected_cas_list = self.get_selected()
        solvent_info = self.get_candidates()
        hsp_target = self.get_hsp_target()
        pctx = PContext(
            selected_cas_list=selected_cas_list, 
            solvent_info=solvent_info, 
            target=hsp_target
        )
        self._is_finalized = True
        return pctx

    def __bool__(self) -> bool:
        return self._is_finalized

    def register_solvent_db(self, solvent: Solvent) -> None:
        # Add a solvent to the internal user database.
        if solvent and solvent.CAS not in self._db_map:
            self._db_map[solvent.CAS] = solvent  # type: ignore
            self._raw_db.append(asdict(solvent))

    def register_custom_solvent(self, record: dict, persist: bool = False) -> tuple[bool, str]:
        """Register a custom solvent record into the current session.

        If `persist` is True, also save it into the user database.
        Returns (ok, message).
        """
        solvent = ds.solvent_from_record(record)
        if solvent is None:
            return False, "Missing CAS."
        cas = str(solvent.CAS).strip()
        if not cas:
            return False, "Missing CAS."
        if cas in self._db_map:
            return False, f"CAS {cas} already exists in the database."
        self._db_map[cas] = solvent
        self._raw_db.append(asdict(solvent))
        if persist:
            try:
                ds.add_user_solvent(asdict(solvent))
            except OSError:
                return True, "Added to this session, but failed to save to user database."
        return True, "Added custom solvent."

    def load_user_db(self, path: str | None = None) -> tuple[bool, str]:
        """Load user-supplied solvents and append to current session DB.

        If `path` is None, load the default per-user file. Returns (ok, message).
        """
        try:
            if path:
                user = ds.load_user_solvents_from_path(path)
            else:
                user = ds.load_user_solvents()
            if not user:
                return False, "No user records found."
            # Append and rebuild map
            self._raw_db.extend(user)
            self._db_map = ds.build_solvent_map(self._raw_db)
            # remember path if provided
            if path:
                self._user_db_path = path
            else:
                self._user_db_path = str(ds._USER_DB)
            return True, f"Loaded {len(user)} user records."
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

    def save_user_db(self, path: str | None = None) -> tuple[bool, str]:
        """Persist current session's user-added records to path or default.

        Returns (ok, message).
        """
        try:
            builtin = ds.load_db()
            builtin_cas = {rec.get('CAS') for rec in builtin if rec.get('CAS')}
            user_records = [r for r in self._raw_db if r.get('CAS') not in builtin_cas]
            if path:
                ds.save_user_solvents_to_path(path, user_records)
                return True, f"Saved {len(user_records)} records to {path}"
            ds.save_user_solvents(user_records)
            return True, f"Saved {len(user_records)} records to default user DB"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

    def save_user_solvents(self) -> None:
        # Persist current raw DB additions to the user file.
        # Determine which records are likely user-added by comparing against builtin DB
        builtin = ds.load_db()
        builtin_cas = {rec.get('CAS') for rec in builtin if rec.get('CAS')}
        user_records = [r for r in self._raw_db if r.get('CAS') not in builtin_cas]
        ds.save_user_solvents(user_records)

    def load_user_solvent_selection(self, path: str | None = None) -> tuple[bool, str]:
        """
        Load user-supplied solvents and select them in the current session.
        File should be in the format as the default candidate list.

        """
        if path is None:
            path = str(ds._USER_SELECT)
        solvents = ds.load_user_solvents_from_path(path)  # to ensure file exists
        # Select all loaded user solvents
        for solvent in solvents:
            cas = str(solvent.get('CAS', '')).strip()
            if cas and cas in self._db_map and cas not in self.selected:
                self.selected.append(cas)
        return True, f"Selected {len(self.selected)} solvents including user records."



def calculate_mixture(
        selected_cas_list: list[str], 
        solvent_info: dict[str, Solvent],
        hsp_target: HSPTarget
    ) -> list[CalculationResult] | None:
    """Run the pipeline given a list of selected CAS identifiers."""
    from app.logic.pipeline import run_pipeline
    pctx = PContext(selected_cas_list=selected_cas_list, solvent_info=solvent_info, target=hsp_target)
    pctx = run_pipeline(pctx)
    return pctx.final_results


def start_setup() -> SetupSession:
    return SetupSession()