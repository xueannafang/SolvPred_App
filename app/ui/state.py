from __future__ import annotations

from dataclasses import dataclass

from app.models import HSPTarget, CalculationResult


@dataclass
class AppState:
    selected_cas: list[str]
    target: HSPTarget | None = None
    results: list[CalculationResult] | None = None

    def reset_results(self) -> None:
        self.results = None
