"""Path-aware pipeline state for budget tracking across phases.

Core insight: treating each phase in isolation misses a key signal — if
early phases over-consumed their predicted budget, downstream phases should
receive tighter framing to keep the total run within budget.  Conversely,
if early phases were unusually efficient, downstream phases can be relaxed.

This implements a simple proportional correction:
    cumulative_overrun > +20%  →  increase downstream pressure by 1 tier
    cumulative_overrun < -20%  →  decrease downstream pressure by 1 tier
    otherwise                  →  no correction

The ±20% threshold is a conservative deadband that prevents oscillation
from minor measurement noise.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Fraction thresholds that trigger a tier correction
OVER_BUDGET_THRESHOLD = 0.20
UNDER_BUDGET_THRESHOLD = 0.20

PHASE_ORDER = [
    "research",
    "idea",
    "selection",
    "planning",
    "coding",
    "testing",
    "documentation",
]


@dataclass
class PhaseRecord:
    phase: str
    predicted_tokens: int
    consumed_tokens: int

    @property
    def delta(self) -> int:
        """Consumed minus predicted (positive → over budget)."""
        return self.consumed_tokens - self.predicted_tokens

    @property
    def overrun_fraction(self) -> float:
        """Signed overrun as fraction of predicted budget."""
        if self.predicted_tokens == 0:
            return 0.0
        return self.delta / self.predicted_tokens


@dataclass
class PipelineState:
    """Tracks token budget across completed pipeline phases.

    Usage:
        state = PipelineState()

        # after each phase completes:
        state.record_phase("research", predicted=2000, consumed=2400)

        # before framing the next phase:
        correction = state.get_pressure_correction()   # +1, 0, or -1
    """

    records: list[PhaseRecord] = field(default_factory=list)

    def record_phase(self, phase: str, predicted: int, consumed: int) -> None:
        """Record completion of one phase."""
        self.records.append(PhaseRecord(phase, predicted, consumed))

    def cumulative_overrun_fraction(self) -> float:
        """Total consumed vs. total predicted across all completed phases.

        Positive → agent consumed more than BudgetRouter predicted.
        Negative → agent was more efficient than predicted.
        """
        total_predicted = sum(r.predicted_tokens for r in self.records)
        total_consumed = sum(r.consumed_tokens for r in self.records)
        if total_predicted == 0:
            return 0.0
        return (total_consumed - total_predicted) / total_predicted

    def get_pressure_correction(self) -> int:
        """Return tier correction integer: +1, 0, or -1.

        +1: cumulative overrun > 20%  → tighten downstream framing
        -1: cumulative surplus > 20%  → relax downstream framing
         0: within ±20% deadband      → no correction
        """
        overrun = self.cumulative_overrun_fraction()
        if overrun > OVER_BUDGET_THRESHOLD:
            return +1
        if overrun < -UNDER_BUDGET_THRESHOLD:
            return -1
        return 0

    @property
    def phases_completed(self) -> list[str]:
        return [r.phase for r in self.records]

    def summary(self) -> dict:
        return {
            "phases_completed": self.phases_completed,
            "cumulative_overrun_fraction": round(self.cumulative_overrun_fraction(), 4),
            "pressure_correction": self.get_pressure_correction(),
            "records": [
                {
                    "phase": r.phase,
                    "predicted": r.predicted_tokens,
                    "consumed": r.consumed_tokens,
                    "overrun_fraction": round(r.overrun_fraction, 4),
                }
                for r in self.records
            ],
        }
