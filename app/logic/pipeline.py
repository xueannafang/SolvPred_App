from . import solver
from . import temperature_correction
from . import filters as filters_module
from app.models import HSPTarget, Solvent, CalculationResult, PContext

from collections.abc import Callable
# Stages operate on the typed PContext dataclass
Stage = Callable[[PContext], PContext]


class PipelineEngine:
    def __init__(self, stages: list[Stage] = []):
        """Pipeline engine that runs a sequence of stage callables.

        stages: Optional list of callables to initialize the pipeline. New
        stages can still be added with `add_stage`.
        """
        self._stages: list[Stage] = list(stages) if stages else []

    def add_stage(self, stage: Stage) -> None:
        self._stages.append(stage)

    def run(self, context: PContext) -> PContext:
        pctx = context
        for stage in self._stages:
            pctx = stage(pctx)
            if pctx is None:
                # Stage can signal abort by returning None
                raise RuntimeError("Pipeline stage returned None (abort)")
        return pctx


def run_pipeline(pctx: PContext, stages: list[Stage]| None = None) -> PContext:
    """
    Construct pipline engine with default or provided stages and run it.
    """
    if stages is None:
        stages = [
            apply_temperature_correction_stage,
            calculation_stage,
            prepare_process_results_stage,
            final_format_stage,
        ]
    engine = PipelineEngine(stages=stages)
    out = engine.run(pctx)
    return out

def apply_temperature_correction_stage(pctx: PContext) -> PContext:
    """
    Apply temperature correction to solvent_info if requested in params.
    This transforms HSPs in-place in `solvent_info` so downstream stages
    (filters/calculation) operate on temperature-corrected values.
    """
    solvent_info = pctx.solvent_info or {}

    target_temp = pctx.target.temperature if pctx.target is not None else 25.0
    if target_temp != 25.0:
        solvent_info = temperature_correction.correct_hsp_database(solvent_info, 25.0, target_temp)
        pctx.solvent_info = solvent_info
    return pctx

def calculation_stage(pctx: PContext) -> PContext:
    """Call the existing calculation pipeline and attach raw results."""
    selected = pctx.selected_cas_list
    solvent_info = pctx.solvent_info
    hsp_target = pctx.target
    raw = solver.run_hsp_mixture_calculation(selected, solvent_info, hsp_target)
    pctx.raw_results = raw
    return pctx

def prepare_process_results_stage(pctx: PContext) -> PContext:
    """
    Produces `processed_results` in the context.
    """
    if pctx.raw_results is None:
        raise RuntimeError("No raw results to process in pipeline context")
    raw: list[CalculationResult] = pctx.raw_results
    processed_results: list[list[CalculationResult]] = [raw]
    pctx.processed_results = processed_results
    return pctx

def final_format_stage(pctx: PContext) -> PContext:
    """
    Final stage to extract the final results from the processed results.
    """
    processed = pctx.processed_results
    pctx.final_results = processed[-1] if processed else None
    return pctx

