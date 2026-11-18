# v0 vs v1 vs v2: who owns the control flow?

Each version of the quiz generator answers the same question differently: *who decides what
happens next?* This page compares the three versions on the same input with the same model.
For how each version works, see [v0_single.md](v0_single.md), [v1_loop.md](v1_loop.md) and
[v2_graph.md](v2_graph.md).

| Version | Design | Who owns control flow |
|---|---|---|
| v0 | One structured-output call | Nobody |
| v1 | Loop: the model submits through a tool, and a validator sends errors back | The model |
| v2 | Graph: extract concepts, write questions in parallel, critique, revise, assemble | The program |

## Setup

- **Input:** `slides/lecture.md`, the same file for every run.
- **Model:** `qwen3:8b` through Ollama, with thinking off, on a laptop.
- **Runs:** 5 per version, each producing a 5-question quiz, so 25 questions per version.
- **Data:** quizzes are in `data/quizes/<version>/` and traces in `runs/<version>.jsonl`. Git tags
  `v0`, `v1` and `v2` mark the code that produced them.
- **Grounding:** `quizgen/grounding.py:is_grounded` checks every quote after the run. It is an
  exact, case-sensitive match after collapsing runs of spaces and line breaks.

## Results

| | v0 | v1 | v2 |
|---|---|---|---|
| Quotes found verbatim (of 25) | 23 | 21 | **25** |
| Quotes found verbatim, per quiz | 5, 5, 4, 4, 5 | 2, 5, 4, 5, 5 | **5, 5, 5, 5, 5** |
| Quote length (words) | 5–127 | 5–27 | 5–21 |
| Correct answer at index 0 / 1 / 2 / 3 | 3 / 20 / 0 / 2 | 13 / 9 / 2 / 1 | **10 / 5 / 5 / 5** |
| Most answers sharing one position, per quiz | 3–5 | 2–5 | **2** |
| Difficulty (easy / medium / hard) | 3 / 15 / 7 | 7 / 10 / 8 | 10 / 10 / 5 |
| LLM calls per run | 1 | 2–5 (turns) | 11 (1 extract + 5 writers + 5 critics) |
| Input tokens per run | 3,303 | 7,590–18,215 (average 13,374) | 4,450–4,541 (average 4,495) |
| Output tokens per run | 467–1,326 (average 718) | 815–2,619 (average 1,704) | 816–882 (average 840) |
| Time per run | 15–37 s (average 23) | 33–84 s (average 60) | 25–37 s (average 30) |
| Unresolved at the end | not tracked | 4 quotes in 2 runs | 0 |
| Code (lines) | 63 | 136 | 201 + 25 (`assemble.py`) |

A position spread of 10 / 5 / 5 / 5 is the best possible over 25 questions with 5 per quiz: each
quiz uses positions 0–3 once and repeats one of them.

### What failed

- **v0, grounding:** 23 of 25 quotes are verbatim, but only 15 match exactly. The other 8 copy
  speaker notes that wrap across lines in the file. The two real failures are a table row
  flattened into prose ("Use when the steps are: unknown | known") and a paraphrase.
- **v0, quote length:** several quotes copy an entire speaker note, up to 127 words. These ran
  before the 5–40-word rule was added. Today v0 crashes on output like this, because it has no
  retry.
- **v0, answer position:** 20 of 25 correct answers are at index 1. Two quizzes put every answer
  there.
- **v1, grounding:** 2 of 5 runs hit `MAX_TURNS = 5` with errors left. The leftover quotes stitch
  a slide's `> ` blockquote onto speaker-note text, or join two sentences and drop the middle
  ("A loop is flexible. A graph is predictable.").
- **v1, cost:** every turn resends the full slides, about 3.7k input tokens, so cost grows with
  each extra turn.
- **v1, answer position:** still biased. One quiz has all 5 answers at index 0.
- **v2:** no failures in these runs. Every question passed the critic on its first draft.

## Pros and cons

### v0: one call

**Pros**
- Simplest possible design: one prompt, one call, one parse, 63 lines.
- Cheapest and fastest per run.
- A good baseline: it shows what the model does with no structure around it.

**Cons**
- Nothing checks the content. Grounding, answer position and difficulty are whatever the model
  produces.
- Has no recovery. Invalid output crashes the run.
- Pushes problems into the prompt, the weakest place to fix them.

### v1: agent loop

**Pros**
- Verifies grounding in code. Errors become feedback instead of crashes.
- Short quotes come out of the schema rule, not the prompt: quotes drop from up to 127 words to
  at most 27.
- Flexible: the same loop works for any check you can write as code.
- Traces record turns and unresolved errors, which Part 2 can analyse.

**Cons**
- The model decides what to fix and when to stop. Small models stall: 2 of 5 runs ran out of
  turns with ungrounded quotes left.
- The whole quiz is regenerated each turn, so fixing one question can break another.
- Most expensive and slowest: about 4× v0's input tokens and about 2.6× its time on average,
  with high variance (33–84 s).
- Answer position and difficulty are still left to the model.

### v2: agent graph

**Pros**
- Grounded by construction. Code gates each concept's quote with `is_grounded` and sets
  `source_quote` itself. 25 of 25 are verbatim.
- Code owns the properties prompts can't guarantee: `assemble` balances answer positions and
  difficulty is assigned in turn.
- Retries happen per question with a fixed limit, so one bad question can't sink the quiz, and
  failures are dropped and logged.
- Cheap and predictable: writers see only their concept and quote, not the slides. That gives
  about a third of v1's input tokens and a narrow time range (25–37 s).
- The fan-out (`asyncio.gather`) makes the parallel structure visible in the code.

**Cons**
- The most code: 226 lines across `v2_graph.py` and `assemble.py`, against a stage budget of
  about 300 for the whole app.
- More moving parts: 11 LLM calls per run, three prompts and two internal models (`Draft`,
  `Verdict`).
- The LLM critic approved all 25 first drafts. The revise path is covered by tests but never ran
  with the real model, so the critic's value is unproven.
- Questions are narrow and easy to guess. Writers see only one quote, and stems often repeat it
  ("According to the statement 'An agent is a model using tools in a loop,' what best describes
  an agent?").
- The quiz can have fewer than 5 questions if the concept gate or the critic rejects too much.
  This didn't happen in these runs.

## Takeaways

1. **Checks in code beat instructions.** The prompt asked for verbatim quotes in every version.
   v1 got closer because code checked them. v2 got there fully because code chose the quotes.
2. **Answer position is a code problem.** No prompt in v0 or v1 fixed it. v2 fixes it with 25
   lines of plain code, in `assemble.py`.
3. **Control flow decides cost and variance.** v1's cost depends on how many turns the model
   needs. v2's cost is fixed by the graph, so its time range is tight.
4. **A loop is flexible; a graph is predictable.** v1 can handle failures it wasn't designed
   for. v2 can only fix the failures it has nodes for, but it fixes them every time.

## Caveats

- **Small sample:** 5 runs per version on one model and one input. These are trends, not
  significant differences.
- **Grounding only checks quotes:** `is_grounded` proves a quote exists, not that the question
  is answerable from it, correct, or hard to guess. Those are evaluation questions for Part 2.
- **v0 predates the length rule.** The other two versions ran under it, so v0's quote lengths
  aren't directly comparable.
- **Model sensitivity:** results may change with `QUIZGEN_MODEL`. Comparing models is a Part 2
  exercise built on the same traces.
