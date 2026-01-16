"""Custom exceptions used across the SolvPred application.

Provide a clear, small hierarchy so callers can catch either broad
application errors (`SolvPredError`) or specific cases (e.g. `SolventNotFound`).
"""

class SolvPredError(Exception):
    """Base class for all SolvPred application errors."""


class DataLoadError(SolvPredError):
    """Raised when a data file cannot be loaded or parsed.

    Attributes
    - `path`: the file path attempted
    - `message`: optional human-readable explanation
    """

    def __init__(self, path: str, message: str | None = None) -> None:
        self.path = path
        self.message = message or f"Failed to load data: {path}"
        super().__init__(self.message)


class InvalidSolventError(SolvPredError):
    """Raised when a solvent record is invalid (missing fields or bad values)."""

    def __init__(self, cas: str | None, reason: str) -> None:
        self.cas = cas
        self.reason = reason
        super().__init__(f"Invalid solvent {cas!r}: {reason}")


class EmptyHSPTarget(SolvPredError):
    """Raised when a calculation target (HSP) is missing or empty."""

    def __init__(self, message: str | None = None) -> None:
        msg = message or "HSP target is empty or not provided"
        super().__init__(msg)


class EmptySolventSelection(SolvPredError):
    """Raised when an operation requires at least one selected solvent."""

    def __init__(self, message: str | None = None) -> None:
        msg = message or "No solvents selected"
        super().__init__(msg)


class SolventNotFound(SolvPredError):
    """Raised when a solvent with given CAS was not found in the DB/map."""

    def __init__(self, cas: str) -> None:
        self.cas = cas
        super().__init__(f"Solvent not found: {cas}")


class CandidateSessionError(SolvPredError):
    """Errors raised by candidate session operations (selection/filtering)."""


class InvalidCalculationResult(SolvPredError):
    """Raised when a calculation result is invalid or inconsistent."""


class PipelineError(SolvPredError):
    """Raised when a pipeline stage fails.

    Optionally carries the stage name and the original exception as `__cause__`.
    """

    def __init__(self, stage: str | None = None, message: str | None = None, *, cause: Exception | None = None) -> None:
        self.stage = stage
        self.message = message or (f"Pipeline stage failed: {stage}" if stage else "Pipeline failure")
        if cause is not None:
            # Attach the original exception as the __cause__ so tracebacks chain
            raise self from cause
        super().__init__(self.message)


__all__ = [
    "SolvPredError",
    "DataLoadError",
    "InvalidSolventError",
    "EmptyHSPTarget",
    "EmptySolventSelection",
    "SolventNotFound",
    "CandidateSessionError",
    "PipelineError",
    "InvalidCalculationResult",
]
