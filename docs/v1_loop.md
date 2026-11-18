# v1: agent loop with a validator

`quizgen/v1_loop.py`. **Who owns control flow: the model.**

The model gets one tool, `submit_quiz`. Each submission is checked in code, and any errors are sent
back as the tool result. The model decides what to fix and when to resubmit, until the quiz passes
or `MAX_TURNS = 5` runs out.

```
          source text (slides/lecture.md)
                       │
                       ▼
   ┌──────────────────────────────────────┐
   │ LLM turn (tools = [submit_quiz])     │◄──────────────┐
   └──────────────────┬───────────────────┘               │
                      │                                   │
          ┌───────────┴────────────┐                      │
          ▼                        ▼                      │
   no tool call             submit_quiz(quiz)             │
   → append NUDGE                  │                      │
     "call submit_quiz" ───────────┼──────────────────────┤
                                   ▼                      │
                   ┌──────────────────────────────┐       │
                   │ check (code)                 │       │
                   │  1. schema (Quiz)            │       │
                   │  2. exactly 5 questions      │       │
                   │  3. is_grounded(quote) each  │       │
                   └──────────────┬───────────────┘       │
                        ┌─────────┴─────────┐             │
                        ▼                   ▼             │
                    no errors           errors            │
                        │          → tool result:         │
                        │            "Fix these errors"  ─┘
                        ▼                  (up to MAX_TURNS = 5)
       last quiz  +  unresolved errors  +  trace record in runs/
```

## Steps

1. **Prompt:** asks for the quiz, with instructions to submit it through `submit_quiz` and fix any
   reported errors.
2. **Turn:** `llm.chat(messages, tools=[SUBMIT_TOOL])`.
3. **No tool call:** append the model's text plus a `NUDGE` message, then loop.
4. **Tool call:** `check(arguments, source)` runs the schema, the question count and `is_grounded`
   on every quote.
5. **Errors:** append them as a `tool` message, then loop. **No errors:** stop.
6. **Save + trace:** the record includes `turns` and `unresolved` (the errors left when the loop
   ended).

## What changed from v0

- **Grounding** is now checked by code (`is_grounded`) instead of being trusted.
- **Bad output** goes back to the model as feedback instead of crashing the run.

## Remaining weaknesses

- **Control flow:** the model still decides whether it calls the tool, what it fixes and when it
  stops. Small models loop, stall or regress.
- **One big artifact:** the whole quiz is regenerated on every turn, so fixing one question can
  break another.
- **Unchecked content:** nothing checks answer correctness, difficulty mix or answer-position bias.

These gaps are the reason for v2.
