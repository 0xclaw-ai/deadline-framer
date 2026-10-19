"""Optional runtime bridge for the separately installed DeadlineFramer package."""

from __future__ import annotations

import json
import os
import re
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from deadline_framer import BudgetPrediction, DeadlineFramer, PipelineState


PHASE_ORDER = [
    "research",
    "idea",
    "selection",
    "planning",
    "coding",
    "testing",
    "documentation",
]
PHASE_ALIASES = {"doc": "documentation"}


@dataclass(slots=True)
class DeadlineFrame:
    active: bool
    message: str
    instruction: str = ""
    policy: dict[str, Any] = field(default_factory=dict)
    explanation: dict[str, Any] = field(default_factory=dict)
    pipeline_state: dict[str, Any] = field(default_factory=dict)
    normalized_control_text: str = ""
    error: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "active": self.active,
            "instruction": self.instruction,
            "policy": self.policy,
            "pipeline_state": self.pipeline_state,
        }
        if self.normalized_control_text:
            payload["normalized_control_text"] = self.normalized_control_text
        if self.explanation:
            payload["explanation"] = self.explanation
        if self.error:
            payload["error"] = self.error
        return payload


class DeadlineFramerRuntime:
    """Applies DeadlineFramer after BudgetRouter emits control tokens."""

    def __init__(
        self,
        config: Any,
        *,
        budget_log_path: Path,
        metrics_path: Path,
        pipeline_state_path: Path | None = None,
    ):
        self.config = config
        self.budget_log_path = budget_log_path
        self.metrics_path = metrics_path
        self.pipeline_state_path = pipeline_state_path

    @property
    def enabled(self) -> bool:
        return bool(getattr(self.config, "enabled", False))

    def apply(
        self,
        *,
        phase: str,
        decision: Any | None,
        base_message: str,
    ) -> DeadlineFrame:
        if not self.enabled:
            return DeadlineFrame(active=False, message=base_message)
        if decision is None or decision.source in {"disabled", "error", "parse_failed"} or not decision.control_text:
            return DeadlineFrame(
                active=False,
                message=base_message,
                error="BudgetRouter did not provide a usable control string.",
            )
        try:
            normalized_control_text = normalize_control_text(decision.control_text)
            prediction = BudgetPrediction.from_control_string(normalized_control_text)
            pipeline_state = self._build_pipeline_state(phase)
            framer = DeadlineFramer()
            framed_message = framer.inject(base_message, prediction, pipeline_state=pipeline_state)
            return DeadlineFrame(
                active=True,
                message=framed_message,
                instruction=framer.frame(prediction, pipeline_state=pipeline_state),
                policy=framer.make_policy(prediction, pipeline_state=pipeline_state).to_dict(),
                explanation=framer.explain(prediction, pipeline_state=pipeline_state),
                pipeline_state=pipeline_state.summary(),
                normalized_control_text=(
                    normalized_control_text if normalized_control_text != decision.control_text else ""
                ),
            )
        except Exception as exc:  # noqa: BLE001
            return DeadlineFrame(active=False, message=base_message, error=str(exc))

    def log(
        self,
        path: Path,
        *,
        phase: str,
        decision: Any | None,
        frame: DeadlineFrame,
    ) -> None:
        if not self.enabled:
            return
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "phase": phase,
            "budget_control_text": decision.control_text if decision else None,
            "deadline_frame": frame.to_payload(),
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            return

    def _build_pipeline_state(self, current_phase: str) -> PipelineState:
        state = PipelineState()
        current = normalize_phase(current_phase)
        current_index = PHASE_ORDER.index(current) if current in PHASE_ORDER else len(PHASE_ORDER)
        predicted = self._previous_output_budgets(current_index)
        consumed = self._previous_completion_usage(current_index)
        consumed = self._remove_output_surplus_relaxation(predicted, consumed)
        completed = self._completed_phases(current_index)
        for phase in PHASE_ORDER[:current_index]:
            if phase not in predicted:
                continue
            if phase in consumed:
                consumed_tokens = consumed[phase]
            elif phase in completed:
                consumed_tokens = predicted[phase]
            else:
                continue
            state.record_phase(
                phase,
                predicted=max(1, int(predicted[phase])),
                consumed=max(0, int(consumed_tokens)),
            )
        return state

    @staticmethod
    def _remove_output_surplus_relaxation(
        predicted: dict[str, int],
        consumed: dict[str, int],
    ) -> dict[str, int]:
        return {
            phase: max(int(predicted.get(phase, 0)), int(tokens))
            for phase, tokens in consumed.items()
        }

    def _previous_output_budgets(self, current_index: int) -> dict[str, int]:
        budgets: dict[str, int] = {}
        if not self.budget_log_path.exists():
            return budgets
        for row in read_jsonl(self.budget_log_path):
            phase = normalize_phase(str(row.get("phase", "")))
            if phase not in PHASE_ORDER or PHASE_ORDER.index(phase) >= current_index:
                continue
            profile = row.get("effective_profile") or {}
            max_tokens = profile.get("max_tokens")
            try:
                budgets[phase] = int(max_tokens)
            except (TypeError, ValueError):
                continue
        return budgets

    def _previous_completion_usage(self, current_index: int) -> dict[str, int]:
        usage: dict[str, int] = {}
        if not self.metrics_path.exists():
            return usage
        for row in read_jsonl(self.metrics_path):
            phase = normalize_phase(str(row.get("phase", "")))
            if phase not in PHASE_ORDER or PHASE_ORDER.index(phase) >= current_index:
                continue
            try:
                completion_tokens = int(row.get("completion_tokens") or 0)
            except (TypeError, ValueError):
                completion_tokens = 0
            usage[phase] = usage.get(phase, 0) + completion_tokens
        return usage

    def _completed_phases(self, current_index: int) -> set[str]:
        if self.pipeline_state_path is None or not self.pipeline_state_path.exists():
            return set()
        try:
            data = json.loads(self.pipeline_state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return set()
        phases = data.get("phases", []) if isinstance(data, dict) else []
        completed: set[str] = set()
        for row in phases:
            if not isinstance(row, dict):
                continue
            phase = normalize_phase(str(row.get("name", "")))
            if phase not in PHASE_ORDER or PHASE_ORDER.index(phase) >= current_index:
                continue
            if str(row.get("status", "")).lower() in {"done", "complete"}:
                completed.add(phase)
        return completed


def normalize_phase(phase: str) -> str:
    cleaned = phase.strip().lower()
    return PHASE_ALIASES.get(cleaned, cleaned)


def normalize_control_text(control_text: str) -> str:
    return re.sub(r"<THINK_OFF>", "<THINK_LOW>", control_text, flags=re.IGNORECASE)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return rows
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def resolve_log_path(raw: str, *, root: Path, workspace: Path) -> Path:
    path = Path(raw or "./workspace/hackathon/deadline_framer.jsonl")
    if path.is_absolute():
        return path
    normalized = str(path).replace("\\", "/").lstrip("./")
    if normalized == "workspace" or normalized.startswith("workspace/"):
        suffix = normalized.removeprefix("workspace").lstrip("/")
        return (workspace / suffix).resolve()
    return (root / path).resolve()


class DeadlineFramerPlugin:
    """0xClaw entry point; accepts router output or an explicit control template."""

    def __init__(self, *, root: Path, workspace: Path):
        self.control_template = os.environ.get("OXCLAW_DEADLINE_CONTROL_TEMPLATE", "")
        self.runtime = DeadlineFramerRuntime(
            SimpleNamespace(enabled=True),
            budget_log_path=workspace / "hackathon" / "budget_router.jsonl",
            metrics_path=workspace / "hackathon" / "metrics.jsonl",
            pipeline_state_path=workspace / "hackathon" / "pipeline_state.json",
        )
        self.log_path = workspace / "hackathon" / "deadline_framer.jsonl"

    def prepare(self, phase: str, command: str, profile: Any, context: dict) -> Any:
        if "budget_decision" not in context:
            if not self.control_template:
                raise ValueError(
                    "Enable budget-router before deadline-framer, or set "
                    "OXCLAW_DEADLINE_CONTROL_TEMPLATE for standalone framing."
                )
            control = self.control_template.format(phase=normalize_phase(phase).upper())
            prediction = BudgetPrediction.from_control_string(normalize_control_text(control))
            if prediction.phase != normalize_phase(phase):
                raise ValueError("Deadline control phase does not match the requested phase")
            context["budget_decision"] = SimpleNamespace(source="manual", control_text=control)
        return profile

    def frame(self, phase: str, message: str, context: dict) -> str:
        if context.get("budget_mode") == "shadow":
            return message
        decision = context.get("budget_decision")
        frame = self.runtime.apply(phase=phase, decision=decision, base_message=message)
        self.runtime.log(self.log_path, phase=phase, decision=decision, frame=frame)
        if frame.error:
            warnings.warn(f"DeadlineFramer skipped: {frame.error}", stacklevel=2)
        return frame.message
