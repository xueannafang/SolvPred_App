"""Filtering and miscibility/boiling-point checks for candidate results.

This module prefers `Solvent` dataclass instances but remains forward
compatible with raw DB dicts by converting them where needed. The logic is
kept simple and avoids broad try/except blocks; missing or invalid fields
cause a conservative `False` (i.e., fail the check) which is safer for
filtering purposes.

The filter functions themselves should have the signature:
    Callable[[Solvent], bool]
and return `True` if the solvent passes the filter, `False` otherwise.
Additional arguments are passed via closures in the name start with `get_`.
In sum, all filter function generators defined should follow the signature:
    Callable[[SetupSession], dict[str, Callable[[Solvent], bool]]]
"""
from app.models import Solvent
from app.api_facade import SetupSession

from collections.abc import Callable
from typing import Protocol


def get_placeholder_filter(session: SetupSession) -> Callable[[Solvent], bool]:
    def placeholder_filter(solvent: Solvent) -> bool:
        """A placeholder filter function that does nothing."""
        return True
    placeholder_filter.name = "Placeholder"
    placeholder_filter.warning = None
    return placeholder_filter

def get_boiling_point_filter(session: SetupSession) -> Callable[[Solvent], bool]:
    temp = session.hsp_target.temperature if session.hsp_target else 25.0
    def boiling_point_filter(solvent: Solvent) -> bool:
        """Filter function to check if solvent's boiling point is above `temp`."""
        if solvent.bp is None:
            return False
        return solvent.bp >= float(temp)
    boiling_point_filter.name = "Check Boiling Point"
    return boiling_point_filter

def get_miscibility_filter(session: SetupSession) -> Callable[[Solvent], bool]:
    _warning_text = "Note: The miscibility filter may not provide accurate results for mixtures containing more than two solvents."
    def miscibility_filter(solvent: Solvent) -> bool:
        """ Return False if any solvents in the selection are recorded immiscible to the current solvent."""
        ims_list = solvent.ims_idx if solvent.ims_idx else ''
        for ims_idx in ims_list.split(';'):
            ims_idx = ims_idx.strip()
            if not ims_idx.isdigit():
                continue
            ims_no = int(ims_idx)
            for cas in session.selected:
                if cas == solvent.CAS:
                    continue
                other_solvent = session.get_solvent(cas)
                if other_solvent and other_solvent.No == ims_no:
                    return False
        return True
    miscibility_filter.name = "Check Miscibility"
    miscibility_filter.warning = _warning_text if session.hsp_target and session.hsp_target.max_cosolvent > 2 else None
    return miscibility_filter


__all__ = [
    "get_boiling_point_filter",
    "get_miscibility_filter",
]