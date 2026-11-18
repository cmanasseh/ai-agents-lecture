"""v1: an agent loop. The model submits via a tool; a validator feeds errors back.

The model owns the control flow: it decides what to fix and when to resubmit.
"""

import hashlib
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from quizgen.grounding import is_grounded
from quizgen.llm import LLM, OllamaLLM, model_name, tool_spec
from quizgen.schema import Quiz
from quizgen.trace import RUNS_DIR, write_trace

VERSION = "v1"
N_QUESTIONS = 5
MAX_TURNS = 5
OUT_DIR = Path("data/quizes/v1")

SUBMIT_TOOL = tool_spec(
    "submit_quiz",
    "Submit the quiz. Returns 'ok' or a list of errors to fix before resubmitting.",
    Quiz.model_json_schema(),
)

PROMPT = f"""Write a multiple-choice quiz with {N_QUESTIONS} questions about the text below.
Each question has exactly 4 options and one correct answer.
For each question, copy a short verbatim sentence from the text that supports the answer
into `source_quote`. Submit the quiz with the submit_quiz tool and fix any errors it reports.

TEXT:
"""
NUDGE = "Do not answer in text. Call submit_quiz with the quiz."


@dataclass(frozen=True)
class LoopResult:
    """The last submitted quiz, its unresolved errors, and what the loop cost."""

    quiz: Quiz | None
    errors: list[str]
    turns: int
    input_tokens: int
    output_tokens: int


def check(arguments: dict, source: str) -> tuple[Quiz | None, list[str]]:
    """Validate a submission: schema first, then question count and grounding."""
    try:
        quiz = Quiz.model_validate(arguments)
    except ValidationError as e:
        return None, [f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()]
    if len(quiz.questions) != N_QUESTIONS:
        return quiz, [f"expected {N_QUESTIONS} questions, got {len(quiz.questions)}"]
    errors = [
        f"questions.{i}.source_quote: not found verbatim in the text: {q.source_quote!r}"
        for i, q in enumerate(quiz.questions)
        if not is_grounded(q.source_quote, source)
    ]
    return quiz, errors


def run(source: str, llm: LLM, max_turns: int = MAX_TURNS) -> LoopResult:
    """Let the model submit, check, and resubmit until the quiz passes or turns run out."""
    messages = [{"role": "user", "content": PROMPT + source}]
    quiz, errors = None, ["no quiz submitted"]
    turns = tokens_in = tokens_out = 0
    while turns < max_turns:
        turns += 1
        reply = llm.chat(messages, tools=[SUBMIT_TOOL])
        tokens_in += reply.input_tokens
        tokens_out += reply.output_tokens
        if not reply.tool_calls:
            messages += [
                {"role": "assistant", "content": reply.text},
                {"role": "user", "content": NUDGE},
            ]
            continue
        call = reply.tool_calls[0]
        quiz, errors = check(call.arguments, source)
        if not errors:
            break
        messages += [
            {
                "role": "assistant",
                "content": reply.text,
                "tool_calls": [{"function": {"name": call.name, "arguments": call.arguments}}],
            },
            {
                "role": "tool",
                "tool_name": call.name,
                "content": "Fix these errors:\n" + "\n".join(errors),
            },
        ]
    return LoopResult(quiz, errors, turns, tokens_in, tokens_out)


def main() -> None:
    """Generate one quiz from the file in argv[1]; save it and trace the run."""
    source = Path(sys.argv[1]).read_text()
    model = model_name()
    start = time.perf_counter()
    result = run(source, OllamaLLM(model))
    latency = time.perf_counter() - start
    quiz = result.quiz.model_dump() if result.quiz else None

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"quiz_{stamp}.json"
    out_path.write_text(result.quiz.model_dump_json(indent=2) if result.quiz else "null")

    write_trace(
        RUNS_DIR,
        {
            "version": VERSION,
            "model": model,
            "input_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "latency_s": round(latency, 2),
            "turns": result.turns,
            "unresolved": result.errors,
            "timestamp": stamp,
            "quiz": quiz,
        },
    )
    print(f"{result.turns} turns, {len(result.errors)} unresolved, {latency:.1f}s -> {out_path}")


if __name__ == "__main__":
    main()
