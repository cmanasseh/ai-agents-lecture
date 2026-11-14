---
marp: true
paginate: true
---

# Coding with AI Agents

Who owns the control flow?

Eloi Pereira · Director of Data Science, Element Fleet Management

---

## Today

- **Part 1, AI agents:** concepts, then build an agent, live, with an agent
- **Part 2, validation and evaluation:** how good is what we built?
- **Part 3, deployment:** what does it take to run it for real?

Two layers: a coding agent writes our application, and the application is itself an agent. The same principles apply to both.

---

## 2021 · Autocomplete

```python
def fahrenheit_to_celsius(f):
    return (f - 32) * 5 / 9    # ← suggested; press Tab
```

The model guesses the next line. You accept or reject it.

**You decide every line.**

---

## 2023 · Prompt engineering

```text
You are an expert Python developer.
Write a function that converts Fahrenheit to Celsius.
Think step by step. Return only code.
```

You craft the input. The model is a black box you talk to.

**You decide; the model answers once.**

---

## Mid 2025 · Context engineering

```text
┌─ context window ─────────────────┐
│ system prompt   CLAUDE.md        │
│ tools           read, edit, bash │
│ docs            relevant files   │
│ examples        few-shot         │
│ task            fix issue #42    │
└──────────────────────────────────┘
```

The model is only as good as what you put in its context: RAG, system prompts, tool descriptions, few-shot examples — curating the full context became the lever.

**You decide what the model sees.**

---

## 2026 · Agentic paradigms

**Loop engineering** (June 2026)
One agent cycles plan → act → observe → retry until done. **The model decides the next step.**

**Graph engineering** (July 2026)
Many steps, wired together: parallel stages, feedback routed to one node. **Code decides the steps; the model works inside them.**

Both come back in detail later, and we build one of each today.

---

## What is an agent?

> An agent is an LLM using tools in a loop.

- **Model:** decides the next action
- **Tools:** act on the environment (read files, run code, call APIs)
- **Loop:** feed results back until a stop condition is met

---

## The agent loop

```
context → model → action → environment → observation
   ↑                                          │
   └──────────────────────────────────────────┘
            until done or out of budget
```

The model never runs code itself. The surrounding program does.

---

## Every turn is a roll of the dice

If each step is right 95% of the time:

| Steps | 1 | 10 | 20 | 50 |
|---|---|---|---|---|
| Whole run right | 95% | 60% | 36% | 8% |

- Errors compound over the run
- A mistake stays in the context and steers every later turn

Temperature 0 doesn't fix this: the path itself is chosen by the model.

---

## The harness: taking control back

The harness is the deterministic code around the model. You decide:

- **Context:** what the model sees
- **Tools:** which actions are allowed, and how they run
- **Feedback:** how results and errors come back
- **Stop conditions:** what counts as done
- **Budget:** how many turns, tokens, seconds
- **Tracing:** a record of every step

The model proposes; the harness decides.

Do not confuse the agent harness with an eval harness, which runs tests.

---

## Workflow for coding with agents

**Spec → Plan → Implement → Verify**

- Ask for a plan before any code
- Write tests first and let the agent iterate against them
- Keep diffs small and review every one
- Commit often; git is your undo button

---

## Configuring the coding agent

| Mechanism | What it does |
|---|---|
| Context file (CLAUDE.md, AGENTS.md) | Always-loaded project knowledge and conventions |
| Skills | Instructions and scripts loaded only when relevant |
| MCP servers | Connect the agent to external tools and data |
| Subagents | Delegate a task to a separate, isolated context |
| Permissions | Allow or deny specific tools and commands |
| Hooks | Run deterministic scripts on agent events |

Context files and skills are requests. Permissions and hooks are enforcement.

---

## Verification beats instructions

An agent is only as good as its feedback signal.

- Linters and formatters: ruff
- Type checkers: pyright, mypy
- Tests: pytest
- Secret scanners: gitleaks, detect-secrets

Errors returned to the model become its next instruction.

A check turns a probabilistic output into a known one.

---

## Guardrails in layers

| Layer | When it runs | Mechanism |
|---|---|---|
| Agent time | After every edit | Agent hooks, permissions |
| Commit time | On `git commit` | pre-commit hooks |
| Merge time | On pull request | CI |

Run the same checks at every layer, fastest first. No layer trusts the one before it.

---

## Example: an agent hook

`.claude/settings.json`

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{ "type": "command",
        "command": "uv run ruff check --fix --quiet . >&2 || exit 2" }]
    }]
  }
}
```

Exit code 2 sends the lint errors back to the agent, which fixes them before moving on.

---

## Loops vs graphs

The key question: **who owns the control flow?**

| | Loop | Graph |
|---|---|---|
| Control flow | The model decides | You decide |
| Non-determinism | Compounds over the whole run | Contained in each node |
| Flexibility | High | Lower |
| Cost and latency | Unpredictable | Bounded |
| Parallelism | Hard | Natural (fan-out) |
| Debugging | Read the transcript | Inspect each node |

---

## Keep the loops small

```text
one long loop:  model ⟲ × 50 ───────────────────────────→ result?

graph:          [model ⟲ ≤ 3] → check → [model ⟲ ≤ 3] → check → result
```

- **Loop:** open-ended tasks where the steps are unknown in advance
- **Graph:** repeatable tasks where you know the steps
- **Subagents** are the same idea for coding agents: a bounded task, a fresh context, a result you can check

Start with the simplest thing that works. Add structure when you see failures.

---

## Today's app: a quiz generator

- **Input:** this lecture, as markdown
- **Output:** a multiple-choice quiz
- Every question must cite a verbatim quote from the lecture

The quote makes grounding checkable by code, not just by judgment.

---

## Build plan

| Version | Design | Fixes |
|---|---|---|
| v0 | Single structured call | Baseline |
| v1 | Loop with a validator | Ungrounded or malformed output |
| v2 | Graph: concepts → questions → critic → assembly | Ambiguity, cost, position bias |

Each version is motivated by a failure of the previous one.

v0 → v1 gives the model control; v1 → v2 takes it back, except inside each node.

---

## Local models, swappable

- Ollama runs open models on a laptop
- One environment variable switches the model
- Same harness, different models, different mistakes

Failure types to watch:

- **Harness:** malformed tool calls, no tool call, budget exhausted
- **Contract:** schema violations
- **Content:** ungrounded, ambiguous, or guessable questions

---

## Questions for the next parts

v1 and v2 both produce quizzes.

- **Evaluation:** which one is better, and how would you know?
- **Deployment:** what hardware does each model need, and where can it run?

Let's build.
