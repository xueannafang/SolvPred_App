from dataclasses import dataclass, asdict, field
from numpy import ndarray


@dataclass
class Solvent:
    CAS: str | None = None  
    Name: str | None = None 
    D: float  | None = None
    P: float  | None = None
    H: float  | None = None
    # optional additional fields commonly present in the DB
    bp: float | None = None  # boiling point
    No: int | None = None  # index number
    ims_idx: str | None = None  # immiscible solvent index
    # store raw record for other fields if callers need them
    raw: dict[str, object] | None = None

    def __bool__(self) -> bool:
        return all(map(bool, (self.CAS, self.Name, 
                              self.D is not None and self.D >= 0, 
                              self.P is not None and self.P >= 0, 
                              self.H is not None and self.H >= 0)))

@dataclass
class HSPTarget:
    D: float 
    P: float 
    H: float 
    threshold: float = 0.01
    max_cosolvent: int = 2
    n_perturb: int = 50
    perturb_std: float = 0.1
    temperature: float = 25.0
    err_d: float = 0.5
    err_p: float = 0.5
    err_h: float = 0.5


@dataclass
class CContext:
    """Container dataclass used to carry data through the calculation stages."""
    cas_comb: tuple[str, ...]
    cmat: ndarray  # concentration matrix
    emat: ndarray  # error matrix
    hsp_matrix: ndarray  # HSP matrix
    perturbed_targets: ndarray  # perturbed target HSP values
    cmean: ndarray | None = None  # mean concentration vector
    

@dataclass
class CalculationResult:
    cas_comb: list[str]  # List of CAS for the given combination
    c_mean_norm: list[float]  # Normalized pertubated-mean concentrations
    hsp_mixture: list[float]  # Resulting mixture HSP values
    hsp_error: list[float]  # Error in HSP components compared to target

    def get_total_error(self) -> float:
        e_d = self.hsp_error[0]
        e_p = self.hsp_error[1]
        e_h = self.hsp_error[2]
        total = (e_d**2 + e_p**2 + e_h**2) ** 0.5
        return total


@dataclass
class PContext:
    """Container dataclass used to carry data through the pipeline stages.

    This is optional (the pipeline still accepts plain dict contexts) but
    provides a typed, discoverable structure for the main data used by
    the pipeline and UI layers.
    """
    # Without these nothing works.
    selected_cas_list: list[str]
    solvent_info: dict[str, Solvent]
    target: HSPTarget
    # raw results coming from solver
    raw_results: list[CalculationResult] | None = None
    # processed/normalized CalculationResult objects
    processed_results: list[list[CalculationResult]] | None = None
    # final_results convenience pointer
    final_results: list[CalculationResult] | None = None
