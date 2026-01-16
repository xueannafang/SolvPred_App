import json
import os
from pathlib import Path
from app.models import Solvent
from shutil import copyfile

# User data storage: keep simple and predictable. Store user-added solvents
# in a per-user config directory under the home folder. This keeps the
# built-in database intact and makes user data portable.
_APP_DIR = Path(__file__).parents[1]
_APP_DATA_DIR = _APP_DIR / 'data'
_DEFAULT_DB = _APP_DATA_DIR / 'solv_pred_db_v2.json'
_DEFAULT_SELECT = _APP_DATA_DIR / 'default_solv_candidate.json'
_TEST_DB = _APP_DATA_DIR / 'test_db.json'
_USER_DIR = Path.home() / '.solvpred_app'
_USER_DIR.mkdir(parents=True, exist_ok=True)
_USER_DB_DIR = _USER_DIR / 'db'
_USER_DB_DIR.mkdir(parents=True, exist_ok=True)
_USER_DB = _USER_DB_DIR / 'test_db.json'
if not _USER_DB.exists():
    copyfile(_TEST_DB, _USER_DB)
_USER_SELECT_DIR = _USER_DIR / 'selection'
_USER_SELECT_DIR.mkdir(parents=True, exist_ok=True)
_USER_SELECT = _USER_SELECT_DIR / 'default.json'
if not _USER_SELECT.exists():
    copyfile(_DEFAULT_SELECT, _USER_SELECT)
_USER_PARAMS_DIR = _USER_DIR / 'params'
_USER_PARAMS_DIR.mkdir(parents=True, exist_ok=True)


def solvent_from_record(rec: dict) -> Solvent | None:
    """Convert a raw DB record (dict) into a `Solvent` dataclass.

    Keep the implementation simple and permissive: prefer direct field
    extraction and light casting (no heavy type checks). If a numeric
    field is missing or cannot be cast, fall back to `None` (or 0.0 for
    core HSP fields to preserve numeric behaviour).
    """
    # Minimal mapping: copy fields into the Solvent dataclass.
    # Keep conversion and validation out of this function; it should be
    # simple and fast. Return a Solvent instance or None if no CAS present.
    cas = rec.get('CAS')
    if not cas:
        return None
    solvent = Solvent(
        CAS=str(cas),
        Name=rec.get('Name'),
        D=rec.get('D'),
        P=rec.get('P'),
        H=rec.get('H'),
        bp=rec.get('bp'),
        No=rec.get('No.'),
        ims_idx=rec.get('ims_idx'),
        raw=rec,
    )
    return solvent

def load_db() -> list[dict]:
    path = _DEFAULT_DB
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_default_candidates() -> list[dict]:
    path = _DEFAULT_SELECT
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_user_solvents() -> list[dict]:
    if not _USER_DB.exists():
        return []
    with open(_USER_DB, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def save_user_solvents(records: list[dict]) -> None:
    with open(_USER_DB, 'w', encoding='utf-8') as fh:
        json.dump(list(records), fh, indent=2, ensure_ascii=False)


def append_user_solvent(rec: dict) -> None:
    all_rec = load_user_solvents()
    all_rec.append(rec)
    save_user_solvents(all_rec)


def add_user_solvent(rec: dict) -> None:
    """Public helper to persist a single user solvent record."""
    append_user_solvent(rec)


def load_user_solvents_from_path(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    with open(p, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def save_user_solvents_to_path(path: str, records: list[dict]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8') as fh:
        json.dump(list(records), fh, indent=2, ensure_ascii=False)


def append_user_solvent_to_path(rec: dict, path: str) -> None:
    all_rec = load_user_solvents_from_path(path)
    all_rec.append(rec)
    save_user_solvents_to_path(path, all_rec)


def load_combined_db() -> list[dict]:
    """Load built-in DB and append user-supplied solvents (user last)."""
    base = load_db()
    user = load_user_solvents()
    if not user:
        return base
    return base + list(user)


def build_solvent_map(db: list[dict]) -> dict[str, Solvent]:
    """Return a dict mapping CAS -> Solvent dataclass for all valid records."""
    out: dict[str, Solvent] = {}
    for rec in db:
        solvent = solvent_from_record(rec)
        if solvent is not None:
            out[str(solvent.CAS)] = solvent
    return out


def search_solvents(db: list[dict], key: str, limit: int = 50) -> list[Solvent]:
    """Simple substring search over Name and CAS. Returns Solvent objects."""
    k = (key or '').strip().lower()
    if not k:
        return []
    matches: list[Solvent] = []
    for rec in db:
        name = str(rec.get('Name', '')).lower()
        cas = str(rec.get('CAS', '')).lower()
        if k in name or k in cas:
            s = solvent_from_record(rec)
            if s:
                matches.append(s)
                if len(matches) >= limit:
                    break
    return matches


def get_solvent_by_cas(db_map: dict[str, Solvent], cas: str) -> Solvent | None:
    return db_map.get(cas)

# Function to load parameters from a file
def load_params_from_path(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"The file {path} does not exist.")
    with open(p, 'r', encoding='utf-8') as fh:
        return json.load(fh)

# Function to save parameters to a file
def save_params_to_path(path: str, params: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8') as fh:
        json.dump(params, fh, indent=2, ensure_ascii=False)
