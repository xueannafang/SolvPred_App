"""
temperature_correction.py

Provides functions for temperature correction of HSP values for solvents.
TODO: Check and validate formulas with literature.
"""

import math
from dataclasses import asdict

from app.models import Solvent
from app.exceptions import InvalidSolventError

def correct_hsp_d(d: float, delta_temp: float) -> float:
    """Return temperature-corrected δD."""
    tml_expn_coeff = 0.0007  # K^-1, from HSPiP
    return float(d) * math.exp(-1.25 * tml_expn_coeff * delta_temp)

def correct_hsp_p(p: float, delta_temp: float) -> float:
    """Return temperature-corrected δP."""
    tml_expn_coeff = 0.0007
    return float(p) * math.exp(-0.5 * tml_expn_coeff * delta_temp)

def correct_hsp_h(h: float, delta_temp: float) -> float:
    """Return temperature-corrected δH."""
    tml_expn_coeff = 0.0007
    return float(h) * math.exp(-(0.00122 + 0.5 * tml_expn_coeff) * delta_temp)

def correct_solvent_hsp(solvent: Solvent, current_temp: float, target_temp: float) -> Solvent:
    """
    Return a new solvent dict with temperature-corrected HSP values.
    Assumes solvent dict has keys 'D', 'P', 'H'.
    """
    if not solvent:
        # make sure we have valid solvent data
        raise InvalidSolventError(solvent.CAS, "Invalid solvent data for temperature correction.")
    delta_temp = target_temp - current_temp
    d = correct_hsp_d(solvent.D, delta_temp) # type: ignore
    p = correct_hsp_p(solvent.P, delta_temp) # type: ignore
    h = correct_hsp_h(solvent.H, delta_temp) # type: ignore
    data = asdict(solvent)
    data.update({'D': d, 'P': p, 'H': h})
    corrected_solvent = Solvent(**data)
    return corrected_solvent

def correct_hsp_database(solvent_info: dict, current_temp: float, target_temp: float) -> dict:
    """
    Return a new solvent_info dict with temperature-corrected HSP values for all solvents.
    """
    return {
        cas: correct_solvent_hsp(solvent, current_temp, target_temp)
        for cas, solvent in solvent_info.items()
    }
