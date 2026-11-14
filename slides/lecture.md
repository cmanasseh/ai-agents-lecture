---
marp: true
paginate: true
---

# Coding with AI Agents

From prompts to loops to graphs

Eloi Pereira · Director of Data Science, Element Fleet Management

---

## Today

- **Part 1, AI agents:** concepts, then build an agent, live, with an agent
- **Part 2, validation and evaluation:** how good is what we built?
- **Part 3, deployment:** what does it take to run it for real?

Two layers: a coding agent writes our application, and the application is itself an agent. The same principles apply to both.

---

## How AI coding tools evolved

| Generation | Example tools | Unit of work |
|---|---|---|
| Autocomplete | Copilot (early) | A line |
| Chat | ChatGPT, Claude | A snippet |
| Agentic | Cursor, Claude Code, Codex CLI | A task |

Each step moved the human from writing code to specifying and reviewing it.

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

## The harness

The harness is all the code around the model:

- **Context assembly:** what goes into the prompt
- **Output parsing:** turning text into structured actions
- **Tool dispatch:** executing actions safely
- **Feedback:** formatting results and errors for the model
- **Stop conditions:** success, budget, failure
- **Tracing:** recording every step

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
| Flexibility | High | Lower |
| Cost and latency | Unpredictable | Bounded |
| Parallelism | Hard | Natural (fan-out) |
| Debugging | Read the transcript | Inspect each node |

---

## When to use which

- **Loop:** open-ended tasks where the steps are unknown in advance
- **Graph:** repeatable tasks where you know the steps
- In practice: graphs whose nodes contain small loops

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
