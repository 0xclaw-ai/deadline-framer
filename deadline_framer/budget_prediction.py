"""BudgetPrediction dataclass and parser for BudgetRouter control-token output."""
from __future__ import annotations

import re
from dataclasses import dataclass

CONTROL_RE = re.compile(
    r"<PHASE_([A-Z_]+)>\s*"
    r"<(TOKEN_[0-9.]+X)>\s*"
    r"<(TIME_[A-Z_]+)>\s*"
    r"<(THINK_[A-Z_]+)>\s*"
    r"<(REPAIR_[0-9]+)>",
    re.IGNORECASE,
)

VALID_PHASES = frozenset(
    {"research", "idea", "selection", "planning", "coding", "testing", "documentation"}
)
PHASE_ALIASES = {"doc": "documentation"}
VALID_TOKENS = frozenset(
    {"TOKEN_0.25X", "TOKEN_0.5X", "TOKEN_0.75X", "TOKEN_1.0X", "TOKEN_1.25X"}
)
VALID_TIMES = frozenset({"TIME_LOW", "TIME_MEDIUM", "TIME_HIGH", "TIME_CRITICAL"})
VALID_THINKS = frozenset({"THINK_LOW", "THINK_MEDIUM", "THINK_HIGH"})
VALID_REPAIRS = frozenset({0, 1, 2, 3})


@dataclass(frozen=True)
class BudgetPrediction:
    """Structured output from BudgetRouter for a single phase.

    Attributes:
        phase: One of the 7 hackathon pipeline phases.
        token: Relative token budget multiplier (TOKEN_0.25X … TOKEN_1.25X).
        time:  Time urgency signal (TIME_LOW … TIME_CRITICAL).
        think: Reasoning depth instruction (THINK_LOW … THINK_HIGH).
        repair: Number of allowed revision cycles (0 … 3).
    """

    phase: str
    token: str
    time: str
    think: str
    repair: int

    def __post_init__(self) -> None:
        phase = self.phase.lower()
        object.__setattr__(self, "phase", PHASE_ALIASES.get(phase, phase))
        object.__setattr__(self, "token", self.token.upper())
        object.__setattr__(self, "time", self.time.upper())
        object.__setattr__(self, "think", self.think.upper())
        if self.phase not in VALID_PHASES:
            raise ValueError(f"Invalid phase: {self.phase!r}. Must be one of {sorted(VALID_PHASES)}")
        if self.token not in VALID_TOKENS:
            raise ValueError(f"Invalid token tier: {self.token!r}")
        if self.time not in VALID_TIMES:
            raise ValueError(f"Invalid time tier: {self.time!r}")
        if self.think not in VALID_THINKS:
            raise ValueError(f"Invalid think tier: {self.think!r}")
        if self.repair not in VALID_REPAIRS:
            raise ValueError(f"Invalid repair count: {self.repair}. Must be 0-3")

    @classmethod
    def from_control_string(cls, s: str) -> "BudgetPrediction":
        """Parse BudgetRouter output string.

        Example:
            BudgetPrediction.from_control_string(
                "<PHASE_CODING><TOKEN_0.75X><TIME_HIGH><THINK_LOW><REPAIR_1>"
            )
        """
        m = CONTROL_RE.search(s)
        if not m:
            raise ValueError(
                f"Cannot parse control string: {s!r}\n"
                "Expected format: <PHASE_X><TOKEN_YZ><TIME_W><THINK_V><REPAIR_N>"
            )
        phase, token, time, think, repair_tag = m.groups()
        repair = int(repair_tag.split("_")[1])
        return cls(phase=phase, token=token, time=time, think=think, repair=repair)

    def to_control_string(self) -> str:
        return (
            f"<PHASE_{self.phase.upper()}>"
            f"<{self.token}>"
            f"<{self.time}>"
            f"<{self.think}>"
            f"<REPAIR_{self.repair}>"
        )

    @classmethod
    def default(cls, phase: str) -> "BudgetPrediction":
        """Moderate baseline default for a phase (tier 2 — no strong time pressure)."""
        return cls(
            phase=phase,
            token="TOKEN_1.0X",
            time="TIME_MEDIUM",
            think="THINK_MEDIUM",
            repair=1,
        )

    def token_multiplier(self) -> float:
        """Return the numeric multiplier implied by the TOKEN tag."""
        return float(self.token.removeprefix("TOKEN_").removesuffix("X"))
