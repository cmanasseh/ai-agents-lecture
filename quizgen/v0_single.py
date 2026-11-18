"""v0: one structured-output call. Nobody owns the control flow."""

import hashlib
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from quizgen.llm import LLM, OllamaLLM, Reply, model_name
from quizgen.schema import Quiz
from quizgen.trace import RUNS_DIR, write_trace

VERSION = "v0"
N_QUESTIONS = 5
OUT_DIR = Path("data/quizes/v0")

PROMPT = f"""Write a multiple-choice quiz with {N_QUESTIONS} questions about the text below.
Each question has exactly 4 options and one correct answer.
For each question, copy a verbatim sentence from the text that supports the answer
into `source_quote`.

TEXT:
"""


def generate(source: str, llm: LLM) -> tuple[Quiz, Reply]:
    """Ask the model for a whole quiz in one call and parse it."""
    messages = [{"role": "user", "content": PROMPT + source}]
    reply = llm.chat(messages, Quiz.model_json_schema())
    return Quiz.model_validate_json(reply.text), reply


def main() -> None:
    """Generate one quiz from the file in argv[1]; save it and trace the run."""
    source = Path(sys.argv[1]).read_text()
    model = model_name()
    start = time.perf_counter()
    quiz, reply = generate(source, OllamaLLM(model))
    latency = time.perf_counter() - start

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"quiz_{stamp}.json"
    out_path.write_text(quiz.model_dump_json(indent=2))

    write_trace(
        RUNS_DIR,
        {
            "version": VERSION,
            "model": model,
            "input_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "input_tokens": reply.input_tokens,
            "output_tokens": reply.output_tokens,
            "latency_s": round(latency, 2),
            "timestamp": stamp,
            "quiz": quiz.model_dump(),
        },
    )
    print(f"{len(quiz.questions)} questions in {latency:.1f}s -> {out_path}")


if __name__ == "__main__":
    main()
