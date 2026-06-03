"""DeadlineFramer: converts BudgetRouter control tokens into NL deadline instructions.

Key design properties:
    1. Zero-shot — no model fine-tuning required ("without retraining").
    2. Phase-aware — different phases get qualitatively different framing,
       not just shorter/longer versions of the same template.
    3. Path-aware — optional PipelineState adjusts framing based on how
       much budget prior phases actually consumed vs. predicted.
    4. Composable — base phase instruction + THINK modifier + REPAIR modifier
       are composed independently, enabling clean ablations.

Paper section: §4.3 Deadline Framer
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from .budget_prediction import BudgetPrediction
from .pipeline_state import PipelineState
from .pressure import (
    apply_path_correction,
    compute_pressure_tier,
    tier_to_condition_label,
)
from .templates import PHASE_TEMPLATES, REPAIR_MODIFIERS, THINK_MODIFIERS


@dataclass(frozen=True)
class DeadlinePolicy:
    phase: str
    pressure_tier: int
    condition_label: str
    token_multiplier: float
    time_signal: str
    think: str
    repair: int
    instruction: str
    max_revision_passes: int
    behavior: dict[str, str | int | float]

    def to_dict(self) -> dict:
        return asdict(self)


class DeadlineFramer:
    """Converts BudgetRouter control-token predictions into NL deadline instructions.

    The framing pipeline:
        1. BudgetPrediction(TOKEN, TIME) → base pressure tier [0..4]
        2. PipelineState.get_pressure_correction() → tier correction ∈ {-1, 0, +1}
        3. effective_tier = clip(base + correction, 0, 4)
        4. NL = PHASE_TEMPLATES[phase][effective_tier]
               + THINK_MODIFIERS[think]
               + REPAIR_MODIFIERS[repair]

    Examples:
        framer = DeadlineFramer()

        # Parse BudgetRouter output
        pred = BudgetPrediction.from_control_string(
            "<PHASE_CODING><TOKEN_0.75X><TIME_HIGH><THINK_LOW><REPAIR_1>"
        )

        # Static framing (no path correction)
        instruction = framer.frame(pred)

        # Path-aware framing (adjusts if prior phases overran budget)
        state = PipelineState()
        state.record_phase("research", predicted=2000, consumed=2600)
        instruction = framer.frame(pred, pipeline_state=state)

        # Inject into existing system prompt
        new_prompt = framer.inject(base_system_prompt, pred, pipeline_state=state)
    """

    _HEADER = "[Deadline Guidance — {phase} phase, pressure={label}]"

    def frame(
        self,
        prediction: BudgetPrediction,
        pipeline_state: Optional[PipelineState] = None,
    ) -> str:
        """Generate the NL deadline instruction for one phase.

        Args:
            prediction:     BudgetRouter output for this phase.
            pipeline_state: Optional path state. If provided, adjusts pressure
                            tier based on cumulative overrun from prior phases.

        Returns:
            Complete NL instruction ready for prompt injection.
        """
        base_tier = compute_pressure_tier(prediction.token, prediction.time)
        correction = pipeline_state.get_pressure_correction() if pipeline_state else 0
        effective_tier = apply_path_correction(base_tier, correction)

        base = PHASE_TEMPLATES[prediction.phase][effective_tier]
        think = THINK_MODIFIERS[prediction.think]
        repair = REPAIR_MODIFIERS[prediction.repair]

        return f"{base} {think} {repair}"

    def inject(
        self,
        system_prompt: str,
        prediction: BudgetPrediction,
        pipeline_state: Optional[PipelineState] = None,
    ) -> str:
        """Prepend deadline framing into an existing agent system prompt.

        The framing block is separated from the original prompt by a
        horizontal rule so agents can clearly distinguish the budget
        guidance from task-specific instructions.

        Args:
            system_prompt:  The base system prompt for this phase.
            prediction:     BudgetRouter output for this phase.
            pipeline_state: Optional path state.

        Returns:
            Modified system prompt with deadline framing prepended.
        """
        base_tier = compute_pressure_tier(prediction.token, prediction.time)
        correction = pipeline_state.get_pressure_correction() if pipeline_state else 0
        effective_tier = apply_path_correction(base_tier, correction)
        label = tier_to_condition_label(effective_tier)

        header = self._HEADER.format(phase=prediction.phase.upper(), label=label)
        framing = self.frame(prediction, pipeline_state)

        if pipeline_state and pipeline_state.records:
            overrun_pct = pipeline_state.cumulative_overrun_fraction() * 100
            path_note = (
                f"[Path correction: {overrun_pct:+.1f}% budget overrun → "
                f"tier {base_tier} → {effective_tier}]"
            )
            block = f"{header}\n{framing}\n{path_note}"
        else:
            block = f"{header}\n{framing}"

        return f"{block}\n\n---\n\n{system_prompt}"

    def pressure_tier(
        self,
        prediction: BudgetPrediction,
        pipeline_state: Optional[PipelineState] = None,
    ) -> int:
        """Return effective pressure tier for logging/ablation analysis."""
        base = compute_pressure_tier(prediction.token, prediction.time)
        correction = pipeline_state.get_pressure_correction() if pipeline_state else 0
        return apply_path_correction(base, correction)

    def make_policy(
        self,
        prediction: BudgetPrediction,
        pipeline_state: Optional[PipelineState] = None,
    ) -> DeadlinePolicy:
        """Return structured policy for BudgetRouter or agent runtime integration."""
        tier = self.pressure_tier(prediction, pipeline_state)
        return DeadlinePolicy(
            phase=prediction.phase,
            pressure_tier=tier,
            condition_label=tier_to_condition_label(tier),
            token_multiplier=prediction.token_multiplier(),
            time_signal=prediction.time,
            think=prediction.think,
            repair=prediction.repair,
            instruction=self.frame(prediction, pipeline_state),
            max_revision_passes=prediction.repair,
            behavior={
                "planning_depth": self._planning_depth(prediction.think, tier),
                "scope": self._scope_label(tier),
                "stop_policy": "satisficing" if tier >= 2 else "quality_first",
            },
        )

    @staticmethod
    def _planning_depth(think: str, tier: int) -> str:
        if think == "THINK_HIGH" and tier <= 2:
            return "high"
        if think == "THINK_LOW" or tier >= 3:
            return "low"
        return "medium"

    @staticmethod
    def _scope_label(tier: int) -> str:
        return {
            0: "full",
            1: "core_features",
            2: "working_mvp",
            3: "critical_path_only",
            4: "minimum_executable",
        }[tier]

    def explain(
        self,
        prediction: BudgetPrediction,
        pipeline_state: Optional[PipelineState] = None,
    ) -> dict:
        """Return a dict explaining the framing decision (for paper/debugging)."""
        base_tier = compute_pressure_tier(prediction.token, prediction.time)
        correction = pipeline_state.get_pressure_correction() if pipeline_state else 0
        effective_tier = apply_path_correction(base_tier, correction)

        return {
            "phase": prediction.phase,
            "input": {
                "token": prediction.token,
                "time": prediction.time,
                "think": prediction.think,
                "repair": prediction.repair,
            },
            "pressure": {
                "base_tier": base_tier,
                "path_correction": correction,
                "effective_tier": effective_tier,
                "condition_equiv": tier_to_condition_label(effective_tier),
            },
            "output": self.frame(prediction, pipeline_state),
        }
