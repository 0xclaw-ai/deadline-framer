"""DeadlineFramer — zero-shot NL deadline instruction generator for LLM agents.

Converts BudgetRouter control-token predictions into natural-language
deadline framing that is injected into agent system prompts per phase.

Quick start:
    from deadline_framer import DeadlineFramer, BudgetPrediction

    framer = DeadlineFramer()
    pred = BudgetPrediction.from_control_string(
        "<PHASE_CODING><TOKEN_0.75X><TIME_HIGH><THINK_LOW><REPAIR_1>"
    )
    instruction = framer.frame(pred)
    print(instruction)
"""
from .budget_prediction import BudgetPrediction
from .framer import DeadlineFramer, DeadlinePolicy
from .pipeline_state import PipelineState

__all__ = ["DeadlineFramer", "DeadlinePolicy", "BudgetPrediction", "PipelineState"]
__version__ = "1.0.0"
