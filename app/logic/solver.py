"""Solver and validation routines for HSP mixture calculations.

This module now accepts and returns application dataclasses defined in
`app.models` (Solvent, HSPTarget, CalculationResult) so the logic layer
uses structured interfaces instead of loose dicts.
"""
import numpy as np

from .matrix import build_hsp_matrix, generate_perturbed_targets
from .combinations import generate_solvent_combinations
from app.models import Solvent, HSPTarget, CalculationResult, CContext
from app.exceptions import InvalidCalculationResult


def solve_concentration_for_combination(
        cas_comb: tuple[str,...],
        hsp_matrix: np.ndarray,
        perturbed_targets: np.ndarray,
    ) -> CContext:
    """
    Solve concentrations using pseudoinverse and compute error matrix.

    Returns a lightweight dict used internally by this module; higher-level
    functions will convert results into `CalculationResult` dataclasses.
    """
    S = hsp_matrix
    S_pinv = np.linalg.pinv(S)
    concentrations = S_pinv @ perturbed_targets  # (n_solvents, n_samples)
    error_matrix = np.abs(S @ concentrations - perturbed_targets)  # (4, n_samples)
    raw = CContext(
        cmat=concentrations,  # concentration matrix
        emat=error_matrix,  # error matrix
        cas_comb=cas_comb,  # CAS combination
        hsp_matrix=hsp_matrix,  # HSP matrix
        perturbed_targets=perturbed_targets  # perturbed target HSP values
    )
    return raw


def analyze_concentration_and_error_validity(
        cctx: CContext,
        target: HSPTarget,
    ) -> CContext:
    c_mean = cctx.cmat.mean(axis=1)
    c_std = cctx.cmat.std(axis=1)
    perturb_std = float(target.perturb_std)
    if np.any(c_std > perturb_std):
        raise InvalidCalculationResult("Concentration unstable beyond allowance")
    total = c_mean.sum()
    if total < 0.9 or total > 1.1:
        raise InvalidCalculationResult("Concentration should sum to approx. 1.0")
    if cctx.emat is not None:
        error_mean = cctx.emat.mean(axis=1)
        tol_err = np.array([
            target.err_d,
            target.err_p,
            target.err_h,
            0.0
        ], dtype=float)
        if np.any(error_mean[:3] > tol_err[:3]):
            raise InvalidCalculationResult("HSP error exceeds tolerance")
    cctx.cmean = c_mean
    return cctx


def refine_valid_combination_result(
        cctx: CContext, 
        target: HSPTarget
    ) -> CalculationResult:
    cas_comb = cctx.cas_comb
    hsp_matrix = cctx.hsp_matrix  # (4, n_solvents)
    target_hsp = np.array([
        target.D,
        target.P,
        target.H,
        1.0
    ], dtype=float)
    if cctx.cmean is None:  # Should not happen
        raise InvalidCalculationResult("No mean concentration available")
    c_mean: np.ndarray = cctx.cmean  # n_solvents
    c_mean_norm = c_mean / c_mean.sum() if c_mean.sum() != 0 else c_mean
    threshold = float(target.threshold)
    mask = c_mean_norm >= threshold
    if not np.all(mask):  # if any below threshold, zero them out
        c_mean_norm = c_mean_norm * mask
        if c_mean_norm.sum() > 0:
            c_mean_norm = c_mean_norm / c_mean_norm.sum()
        else:  # all zeroed out, should not happen
            raise InvalidCalculationResult("All concentrations below threshold")
    hsp_mixture = hsp_matrix @ c_mean_norm  # (4,)
    hsp_error = hsp_mixture[:3] - target_hsp[:3]  # (d, p, h)
    tol_err = np.array([
        target.err_d,
        target.err_p,
        target.err_h
    ], dtype=float)
    if np.any(np.abs(hsp_error) > tol_err):
        raise InvalidCalculationResult("HSP error exceeds tolerance")
    nonzero_indices = np.where(c_mean_norm > 0)[0]
    if len(nonzero_indices) == 0:
        raise InvalidCalculationResult("All concentrations below threshold")
    cas_comb = [cas_comb[i] for i in nonzero_indices]
    c_mean_norm = c_mean_norm[nonzero_indices]
    # Build a CalculationResult dataclass
    return CalculationResult(
        cas_comb=cas_comb,
        c_mean_norm=[float(x) for x in c_mean_norm.tolist()],
        hsp_mixture=[float(x) for x in hsp_mixture.tolist()],
        hsp_error=[float(x) for x in hsp_error.tolist()]
    )


def run_hsp_mixture_calculation(
        selected_cas: list[str],
        solvent_info: dict[str, Solvent],
        target: HSPTarget,
    ) -> list[CalculationResult]:
    """Main pipeline: prepare matrices, iterate combos, and collect valid results.

    `params` is an `HSPTarget` dataclass instance. `solvent_info_dict` may be
    a mapping of CAS->dict; callers typically pass the DB slice. We construct
    `Solvent` dataclasses when needed.
    """
    # derive settings from HSPTarget
    n_cosolvent = int(target.max_cosolvent)
    n_samples = int(target.n_perturb)
    std = float(target.perturb_std)

    # Build combinations and run
    cas_combinations: list[tuple[str, ...]] = generate_solvent_combinations(selected_cas, n_cosolvent)
    perturbed_targets = generate_perturbed_targets(target, n_samples=n_samples, std=std)
    valid_results: list[CalculationResult] = []
    for cas_comb in cas_combinations:
        try:
            solvent_comb = [solvent_info[cas] for cas in cas_comb]
            hsp_matrix = build_hsp_matrix(solvent_comb)
            cctx = solve_concentration_for_combination(cas_comb, hsp_matrix, perturbed_targets)
            cctx = analyze_concentration_and_error_validity(cctx, target)
            calc_result: CalculationResult = refine_valid_combination_result(cctx, target)
            valid_results.append(calc_result)
        except InvalidCalculationResult as e:
            pass  # TODO: log if needed
            continue  # skip invalid combinations
    return valid_results

