"""Pressure tier computation from BudgetRouter TOKEN × TIME dimensions.

Maps the two primary budget dimensions to a 5-tier pressure scale [0..4]
that corresponds to the C0–C5 experimental conditions:
    tier 0  ≈  C0  (no pressure)
    tier 1  ≈  C2  (4 h deadline, low-moderate)
    tier 2  ≈  C3  (2 h deadline, moderate)
    tier 3  ≈  C4  (1 h deadline, high)
    tier 4  ≈  C5  (30 min deadline, extreme)

C1 (brevity control) is handled separately in the condition runner —
it is NOT a pressure tier; it tests whether deadline framing adds anything
beyond a simple "be concise" instruction.
"""
from __future__ import annotations

NUM_TIERS = 5

# Additive scores: higher → more pressure
_TOKEN_SCORE: dict[str, int] = {
    "TOKEN_1.25X": -1,
    "TOKEN_1.0X":   0,
    "TOKEN_0.75X":  1,
    "TOKEN_0.5X":   2,
    "TOKEN_0.25X":  3,
}

_TIME_SCORE: dict[str, int] = {
    "TIME_LOW":      -1,
    "TIME_MEDIUM":    0,
    "TIME_HIGH":      1,
    "TIME_CRITICAL":  2,
}

# Scoring algebra:
# raw ∈ [-2, 5]; shift +1; clip to [0, 4] → 5 tiers
# Examples:
#   TOKEN_1.25X + TIME_LOW      → raw=-2 → tier 0  (no pressure, ≈ C0)
#   TOKEN_1.0X  + TIME_MEDIUM   → raw= 0 → tier 1  (low-moderate, ≈ C2)
#   TOKEN_1.0X  + TIME_HIGH     → raw= 1 → tier 2  (moderate, ≈ C3)
#   TOKEN_0.75X + TIME_HIGH     → raw= 2 → tier 3  (high pressure, ≈ C4)
#   TOKEN_0.25X + TIME_CRITICAL → raw= 5 → tier 4  (extreme, ≈ C5)
# NOTE: C3-equiv is TOKEN_1.0X+TIME_HIGH or TOKEN_0.75X+TIME_MEDIUM;
#       TOKEN_0.75X+TIME_HIGH is C4-equiv, tier 3.


def compute_pressure_tier(token: str, time: str) -> int:
    """Map TOKEN × TIME → pressure tier [0..4].

    Args:
        token: BudgetPrediction.token value (e.g. 'TOKEN_0.75X')
        time:  BudgetPrediction.time value  (e.g. 'TIME_HIGH')

    Returns:
        Integer in [0, 4] where 0 = no pressure, 4 = extreme.
    """
    raw = _TOKEN_SCORE[token] + _TIME_SCORE[time]
    return max(0, min(NUM_TIERS - 1, raw + 1))


def apply_path_correction(base_tier: int, correction: int) -> int:
    """Adjust base pressure tier by pipeline-state correction, clamped to [0,4]."""
    return max(0, min(NUM_TIERS - 1, base_tier + correction))


def tier_to_condition_label(tier: int) -> str:
    """Human-readable condition label for logging and ablation reporting."""
    return {0: "C0-equiv", 1: "C2-equiv", 2: "C3-equiv", 3: "C4-equiv", 4: "C5-equiv"}[tier]
