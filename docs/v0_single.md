# v0: one structured-output call

`quizgen/v0_single.py`. **Who owns control flow: nobody.**

One prompt, one call, one parse. The model is asked for the whole quiz at once, and its reply is
constrained to the `Quiz` JSON schema.

```
      source text (slides/lecture.md)
                   │
                   ▼
   ┌────────────────────────────────┐
   │ generate                       │
   │   1 LLM call, format = Quiz    │  "5 questions, 4 options each,
   │   JSON schema                  │   copy a verbatim source_quote"
   └───────────────┬────────────────┘
                   ▼
        Quiz.model_validate_json        fails → crash, no retry
                   ▼
          Quiz  +  trace record in runs/
```

## Steps

1. **Prompt:** asks for `N_QUESTIONS = 5` questions, each with 4 options and a verbatim quote.
2. **Call:** `llm.chat(messages, Quiz.model_json_schema())`. The schema shapes the output.
3. **Parse:** `Quiz.model_validate_json`. Invalid output raises an error.
4. **Save + trace:** the quiz goes to `data/quizes/v0/`, and one record goes to `runs/` with model,
   input hash, tokens and latency.

## What it doesn't check

- **Grounding:** nothing checks that `source_quote` actually appears in the text.
- **Question count:** the schema doesn't fix the number of questions.
- **Answer position:** the model often puts the correct answer in the same slot.
- **Failure:** there's no retry or feedback, so the run either parses or fails.

These gaps are the reason for v1.
