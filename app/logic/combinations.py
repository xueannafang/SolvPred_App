from itertools import combinations

from app.models import Solvent


def generate_solvent_combinations(
        selected_cas_list: list[str], 
        n_cosolvent: int
    ) -> list[tuple[str,...]]:
    """Return all unique solvent combinations (by CAS)"""
    combos = list(combinations(selected_cas_list, n_cosolvent))
    return combos
