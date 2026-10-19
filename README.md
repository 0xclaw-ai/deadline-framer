# 🦀 0xClaw Deadline Framer ⏱️

DeadlineFramer converts BudgetRouter control tokens into phase-specific natural-language guidance for hackathon agents.

```text
<PHASE_CODING><TOKEN_0.75X><TIME_HIGH><THINK_LOW><REPAIR_1>
```

## Install

```powershell
git clone https://github.com/0xclaw-ai/deadline-framer.git
python -m pip install -e ./deadline-framer
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

## Use with 0xClaw

Install this package in the same Python environment as
[0xClaw](https://github.com/0xclaw-ai/0xClaw). For model-driven controls, also
install [BudgetRouter](https://github.com/0xclaw-ai/budget-router) and set
`OXCLAW_PHASE_CONTROLS=budget-router,deadline-framer` in the 0xClaw `.env`.
Configure the model paths using the BudgetRouter README.

To use DeadlineFramer independently, supply a phase control template:

```dotenv
OXCLAW_PHASE_CONTROLS=deadline-framer
OXCLAW_DEADLINE_CONTROL_TEMPLATE=<PHASE_{phase}><TOKEN_0.75X><TIME_HIGH><THINK_LOW><REPAIR_1>
```

The plugin substitutes the current phase and uses the existing framing logic.
For combined operation, its bridge reads prior predicted budgets and completion
usage from the local 0xClaw logs. The bridge preserves the existing conversion of
BudgetRouter's `THINK_OFF` label to DeadlineFramer's `THINK_LOW` label.
The core parser, pressure policy, and templates are unchanged.

The interactive CLI invokes the component on normal phases, `/resume`, and
`/redo`. Local frame logs are stored in `workspace/hackathon/deadline_framer.jsonl`
and ignored by Git. The Python API above works in any agent and does not depend
on 0xClaw or BudgetRouter.

## Related resources

- [Paper / preprint](https://spiral.imperial.ac.uk/entities/publication/7a460786-fba9-4b42-b9a0-d128429f67e4)
- [BudgetRouter training](https://github.com/0xclaw-ai/budget-router-trainer)
- [Model adapter](https://huggingface.co/0xclaw-ai/budgetrouter-qwen3.5-2b-lora)

## License

MIT. See [LICENSE](LICENSE).
