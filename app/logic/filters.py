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


# def advanced_filter_results(valid_combinations: Iterable[Dict[str, Any]], solvent_info_dict: Dict[str, Any], temp: float) -> List[Dict[str, Any]]:
#     no_to_cas = {}
#     for cas, info in solvent_info_dict.items():
#         s = info if isinstance(info, Solvent) else data_service.solvent_from_record(info or {})
#         if s.No is not None:
#             no_to_cas[int(s.No)] = cas

#     labeled_results: List[Dict[str, Any]] = []
#     for combo in valid_combinations:
#         # expect `combo` to be a `CalculationResult` dataclass with `.cas_tuple`
#         cas_tuple = getattr(combo, 'cas_tuple')
#         # convert per-cas to Solvent dataclass before checking bp
#         def _to_sol(cas):
#             info = solvent_info_dict.get(cas)
#             return info if isinstance(info, Solvent) else data_service.solvent_from_record(info or {})

#         pass_bp = all(check_boiling_point(_to_sol(cas), temp) for cas in cas_tuple)
#         pass_misc = check_miscibility(cas_tuple, solvent_info_dict, no_to_cas)
#         if pass_bp and pass_misc:
#             label = 'Pass'
#             label_class = 'label-pass'
#             sort_order = 0
#         elif not pass_bp and pass_misc:
#             label = 'Low Boiling Point'
#             label_class = 'label-bp'
#             sort_order = 2
#         elif pass_bp and not pass_misc:
#             label = 'Likely Immiscible'
#             label_class = 'label-misc'
#             sort_order = 1
#         else:
#             label = 'Low Boiling Point, Likely Immiscible'
#             label_class = 'label-fail'
#             sort_order = 3
#         labeled_results.append({
#             'combo': combo,
#             'pass_bp': pass_bp,
#             'pass_misc': pass_misc,
#             'label': label,
#             'label_class': label_class,
#             'sort_order': sort_order
#         })
#     labeled_results.sort(key=lambda x: x['sort_order'])
#     return labeled_results

__all__ = [
    "get_boiling_point_filter",
    "get_miscibility_filter",
    # "advanced_filter_results",
]