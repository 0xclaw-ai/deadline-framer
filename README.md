# 0xClaw DeadlineFramer

DeadlineFramer converts BudgetRouter control tokens into phase-specific natural-language guidance for hackathon agents.

```text
<PHASE_CODING><TOKEN_0.75X><TIME_HIGH><THINK_LOW><REPAIR_1>
```

## Install

```powershell
pip install -e .
```

## Usage

```python
from deadline_framer import BudgetPrediction, DeadlineFramer, PipelineState

prediction = BudgetPrediction.from_control_string(
    "<PHASE_CODING><TOKEN_0.75X><TIME_HIGH><THINK_LOW><REPAIR_1>"
)

state = PipelineState()
state.record_phase("research", predicted=12000, consumed=14000)

framer = DeadlineFramer()
instruction = framer.frame(prediction, pipeline_state=state)
print(instruction)
```

## Files

- `deadline_framer/budget_prediction.py`: parser and dataclass for BudgetRouter control strings.
- `deadline_framer/framer.py`: DeadlineFramer policy and prompt injection logic.
- `deadline_framer/pipeline_state.py`: path-aware budget overrun state.
- `deadline_framer/pressure.py`: pressure-tier computation.
- `deadline_framer/templates.py`: phase-specific natural-language templates.

This package contains only the DeadlineFramer core and does not require model weights or API keys.
