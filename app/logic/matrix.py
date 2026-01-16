"""Matrix and perturbation utilities for HSP calculations."""
import numpy as np
from app.models import Solvent, HSPTarget


def build_hsp_matrix(solvent_comb: list[Solvent]):
    """
    Construct a solvent HSP matrix of shape (4, n_solvents) 
    for each given solvent combination.
    """
    cols = solvent_comb
    n = len(cols)
    matrix = np.zeros((4, n), dtype=float)
    for i, solvent in enumerate(cols):
        matrix[0, i] = solvent.D
        matrix[1, i] = solvent.P
        matrix[2, i] = solvent.H
        matrix[3, i] = 1.0
    return matrix


def generate_perturbed_targets(target: HSPTarget, n_samples=50, std=0.1):
    """
    Generate perturbed target HSPs by adding Gaussian noise.
    Returns a (4, n_samples) array where each column is a perturbed target.
    """
    hsp = [target.D, target.P, target.H, 1.0]
    target_hsp = np.asarray(hsp, dtype=float)
    noise = np.random.normal(0.0, std, size=(n_samples, 3))
    perturbed = np.tile(target_hsp, (n_samples, 1))
    perturbed[:, :3] += noise
    # perturbed[:, 3] = 1.0
    return perturbed.T
