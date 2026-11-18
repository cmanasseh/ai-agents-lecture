# v2: agent graph

`quizgen/v2_graph.py`. **Who owns control flow: the program.**

The work is split into small nodes with fixed edges. The model only fills in content at each node.
Code decides the order, the fan-out, the retry limit and what gets thrown away.

```
                      source text (slides/lecture.md)
                                 │
                                 ▼
                   ┌──────────────────────────┐
                   │ extract_concepts         │  1 LLM call → up to 8 concepts
                   │   code gate: schema +    │  drop invalid / ungrounded / duplicate
                   │   is_grounded(quote)     │  keep first 5
                   └────────────┬─────────────┘
              asyncio.gather — one node per concept, run in threads
          ┌──────────────┬──────┴───────┬──────────────┐
          ▼              ▼              ▼              ▼
   question_node   question_node  question_node   ...      difficulty = easy, medium, hard, easy, …
   ┌─────────────────────────────────────────┐
   │ write (LLM → Draft)                     │
   │   ├─ schema invalid → feedback, retry   │
   │   ▼                                     │
   │ critique                                │  up to 3 attempts (MAX_REVISIONS = 2)
   │   ├─ code: are all 4 options distinct?  │
   │   └─ LLM critic: is the answer right?   │
   │   ├─ ok → build Question, stop          │
   │   └─ problems → feedback, retry         │
   └─────────────────────────────────────────┘
          └──────────────┬──────────────┘
                         ▼
              keep only nodes with no problems
                         ▼
               assemble (no LLM): balance answer positions, sort easy → hard
                         ▼
                 Quiz  +  trace record in runs/
```

## Nodes

1. **`extract_concepts`:** one call that returns concepts, each with a quote. A code gate keeps
   only valid, grounded, non-duplicate concepts, up to 5.
2. **Fan-out:** one `question_node` per concept, run in parallel with
   `asyncio.gather(asyncio.to_thread(...))`. Difficulty rotates easy, medium, hard by position.
3. **`question_node`:** a write → critique → revise loop that code bounds at 3 attempts.
   - The model writes only a `Draft` (`stem`, `options`, `answer_index`).
   - `critique` runs the cheap code check first (are the options distinct?), then the LLM critic.
   - `build` adds `concept`, `source_quote` and `difficulty` from code, so every question is grounded
     by construction.
4. **Accept:** nodes that still have problems after 3 attempts are dropped and logged.
5. **`assemble`:** plain code with no LLM. It spreads correct answers evenly over positions 0–3 and
   sorts questions from easy to hard.
6. **Save + trace:** the record includes `concepts_found`, `revisions` per node and `unresolved`
   (each failed concept with its problems).

## v1 vs v2

| | v1 loop | v2 graph |
|---|---|---|
| Who decides when to stop | The model (by calling submit) | A `for` loop with a fixed limit |
| Grounding | A check after each submission | A filter on concepts; quotes are set by code |
| Difficulty and answer position | The model's choice | Code (`DIFFICULTIES`, `assemble`) |
| Unit of retry | The whole quiz | One question |
| Bad output | Sent back as an error message | Retried for a fixed number of tries, then excluded and logged |

## Trade-off

- **More calls, but smaller ones:** extraction, plus a writer and a critic per question, adds up
  to 11 calls with no retries (v1 made 2–5). Only extraction sees the slides; writers and critics
  see one concept and its quote. Over 5 runs with `qwen3:8b`, v2 averaged 4.5k input tokens and
  30 s per run, against v1's 13.4k and 60 s. See [comparison.md](comparison.md).
- **Fewer questions:** the quiz can have fewer than 5 questions when concepts or nodes fail.
  The trace records how many. This didn't happen in the 5 measured runs.
- **Narrow questions:** writers see only one quote, so stems often repeat it and the answer is
  easy to guess.
- **Unproven critic:** the critic approved all 25 first drafts in the measured runs, so the revise
  path hasn't run against a real model.
