"""Natural-language instruction templates for DeadlineFramer.

Structure:
    PHASE_TEMPLATES[phase][tier]  →  base instruction string
    THINK_MODIFIERS[think_tag]    →  reasoning-depth modifier
    REPAIR_MODIFIERS[repair_int]  →  iteration-budget modifier

Template design principles:
    1. Phase-specific: each phase has distinct scope concepts
       (breadth of research ≠ feature count in coding)
    2. Tier-specific behavioral triggers that LLMs reliably respond to:
       - Explicit count limits ("3–5 sources", "one primary feature")
       - Permission to skip ("skip all non-essentials")
       - Commitment framing ("commit now", "decide immediately")
       - Quality–speed trade-off ("working over perfect")
    3. Progressive intensity: tier 0→4 has monotonically increasing urgency,
       not just shorter strings — each tier removes a qualitatively different
       layer of work.

Tier mapping to experimental conditions:
    tier 0  ≈  C0  (no pressure, no brevity)
    tier 1  ≈  C2  (4 h, low-moderate)
    tier 2  ≈  C3  (2 h, moderate)
    tier 3  ≈  C4  (1 h, high)
    tier 4  ≈  C5  (30 min, extreme)
"""
from __future__ import annotations

# fmt: off
PHASE_TEMPLATES: dict[str, list[str]] = {

    # ------------------------------------------------------------------ #
    "research": [
        # tier 0 — no pressure
        "You are in the research phase."
        " Survey the topic extensively — explore multiple angles, consult"
        " diverse sources, and build comprehensive background context before"
        " synthesizing your findings.",

        # tier 1 — low-moderate
        "You are in the research phase."
        " Survey key sources and directly relevant information."
        " Aim for breadth across major subtopics and summarize the most"
        " important findings before proceeding.",

        # tier 2 — moderate
        "You are in the research phase."
        " Identify the 3–5 most relevant sources or knowledge areas."
        " Extract key facts and constraints that will directly inform your"
        " solution — skip peripheral topics.",

        # tier 3 — high pressure
        "You are in the research phase."
        " Use 1–2 sources only."
        " Extract the single most critical fact or constraint you need."
        " Do not explore tangents.",

        # tier 4 — extreme
        "You are in the research phase."
        " Do one targeted lookup."
        " Gather only the minimum information required to start building."
        " Proceed immediately.",
    ],

    # ------------------------------------------------------------------ #
    "idea": [
        # tier 0
        "You are in the idea generation phase."
        " Brainstorm broadly — generate diverse solution concepts across"
        " different approaches, technology stacks, and design philosophies"
        " before evaluating any of them.",

        # tier 1
        "You are in the idea generation phase."
        " Generate 4–6 distinct solution concepts."
        " Consider different approaches or technology choices, then"
        " identify the most promising direction with brief reasoning.",

        # tier 2
        "You are in the idea generation phase."
        " Generate 2–3 focused solution concepts."
        " Note the key trade-off for each, then commit to one direction.",

        # tier 3
        "You are in the idea generation phase."
        " Propose one primary solution approach."
        " Keep the scope narrow and immediately achievable."
        " Commit to it without further exploration.",

        # tier 4
        "You are in the idea generation phase."
        " Choose the most straightforward feasible solution."
        " State it in one sentence and proceed immediately.",
    ],

    # ------------------------------------------------------------------ #
    "selection": [
        # tier 0
        "You are in the selection phase."
        " Evaluate all candidate ideas systematically — assess feasibility,"
        " novelty, scope risk, and technical complexity before making your"
        " final decision.",

        # tier 1
        "You are in the selection phase."
        " Compare the top 2–3 ideas against the key criteria"
        " (feasibility, scope, value)."
        " Select the best option and provide a brief justification.",

        # tier 2
        "You are in the selection phase."
        " Pick the idea that best balances feasibility and impact."
        " State your choice and the single most important reason.",

        # tier 3
        "You are in the selection phase."
        " Select the most immediately buildable option."
        " One sentence decision — do not over-analyze.",

        # tier 4
        "You are in the selection phase."
        " Pick the simplest feasible option."
        " Decide now and move on.",
    ],

    # ------------------------------------------------------------------ #
    "planning": [
        # tier 0
        "You are in the planning phase."
        " Create a detailed implementation plan: subtasks, inter-task"
        " dependencies, complexity estimates, and key technical decisions"
        " for each major component.",

        # tier 1
        "You are in the planning phase."
        " Outline the key implementation phases and major tasks."
        " Identify the main dependencies and flag any potential blockers.",

        # tier 2
        "You are in the planning phase."
        " Write a brief implementation plan:"
        " 3–5 bullet points covering the main components and build order."
        " Skip detailed sub-task breakdowns.",

        # tier 3
        "You are in the planning phase."
        " State your approach in 2–3 sentences."
        " List the top 3 things to build, in priority order."
        " Start coding immediately after.",

        # tier 4
        "You are in the planning phase."
        " Skip detailed planning."
        " State what you will build in one sentence, then start coding.",
    ],

    # ------------------------------------------------------------------ #
    # coding has the highest token prior (1.15×) — tier 2 should still
    # encourage a working solution, not just a skeleton.
    "coding": [
        # tier 0
        "You are in the coding phase."
        " Implement thoroughly — include proper error handling, edge cases,"
        " clear naming, modular structure, and inline comments where helpful.",

        # tier 1
        "You are in the coding phase."
        " Implement all core features with basic error handling."
        " Code should be clean and fully functional.",

        # tier 2
        "You are in the coding phase."
        " Deliver a working MVP."
        " Prioritize functionality over polish — a working solution over a"
        " perfect one.",

        # tier 3
        "You are in the coding phase."
        " Implement the single most critical feature only."
        " Skip everything else."
        " Get something that runs.",

        # tier 4
        "You are in the coding phase."
        " Write the absolute minimum that executes."
        " One core function or script."
        " No error handling, no extras, no comments.",
    ],

    # ------------------------------------------------------------------ #
    # testing has the highest TIME prior (1.20×) — reflect this in tiers
    "testing": [
        # tier 0
        "You are in the testing phase."
        " Test comprehensively — cover happy paths, edge cases, error"
        " conditions, and boundary values."
        " Document all test results with expected vs. actual outputs.",

        # tier 1
        "You are in the testing phase."
        " Write tests for the main happy paths and the most likely failure"
        " modes."
        " Verify core functionality works end-to-end.",

        # tier 2
        "You are in the testing phase."
        " Run basic smoke tests."
        " Verify the primary use case completes without errors.",

        # tier 3
        "You are in the testing phase."
        " Run one integration test to confirm the core feature works."
        " That is sufficient.",

        # tier 4
        "You are in the testing phase."
        " Manually verify the code runs without crashing."
        " Skip all automated testing.",
    ],

    # ------------------------------------------------------------------ #
    # documentation has the lowest token prior (0.75×) — even tier 0
    # should not demand excessive docs
    "documentation": [
        # tier 0
        "You are in the documentation phase."
        " Write the complete submission package: README.md with setup"
        " instructions, SUBMISSION.md for the hackathon portal, PITCH.md"
        " with the spoken pitch, and copy the README to project/README.md.",

        # tier 1
        "You are in the documentation phase."
        " Write the required submission docs: README.md, SUBMISSION.md,"
        " PITCH.md, and project/README.md. Keep each concise but complete.",

        # tier 2
        "You are in the documentation phase."
        " Produce the mandatory documentation set: README.md,"
        " SUBMISSION.md, PITCH.md, plus project/README.md. Do not stop"
        " until all four files exist.",

        # tier 3
        "You are in the documentation phase."
        " Write a 3–5 sentence README: what it is, how to run it,"
        " SUBMISSION.md, PITCH.md, and project/README.md. Keep it short."
        " All four required files must still be written.",

        # tier 4
        "You are in the documentation phase."
        " Write only the required files: README.md, SUBMISSION.md,"
        " PITCH.md, and project/README.md. Use brief content.",
    ],
}
# fmt: on

# THINK modifiers — appended after the base phase instruction.
# Controls how much the agent should reason before acting.
THINK_MODIFIERS: dict[str, str] = {
    "THINK_HIGH": (
        "Think step by step before acting."
        " Reason through your approach carefully before writing any output."
    ),
    "THINK_MEDIUM": "Plan your next steps briefly, then execute.",
    "THINK_LOW": (
        "Execute directly."
        " Skip extended reasoning — act immediately."
    ),
}

# REPAIR modifiers — appended after THINK modifier.
# Controls how many revision cycles the agent is permitted.
REPAIR_MODIFIERS: dict[int, str] = {
    0: "Commit to your first implementation — no revision cycles.",
    1: "One revision pass allowed after your initial implementation.",
    2: "Up to two rounds of revision are available if needed.",
    3: "Standard iteration budget — revise as needed to reach a working solution.",
}
