import json
from pathlib import Path

from quizgen.llm import Reply
from quizgen.trace import write_trace
from quizgen.v0_single import generate

QUESTION = {
    "concept": "agent loop",
    "stem": "Who owns the control flow in an agent loop?",
    "options": ["The model", "The program", "The user", "Nobody"],
    "answer_index": 0,
    "source_quote": "the model decides what happens next",
    "difficulty": "easy",
}


class FakeLLM:
    """Records the call and returns a canned quiz."""

    def __init__(self) -> None:
        self.messages: list[dict] = []

    def chat(self, messages: list[dict], schema: dict) -> Reply:
        self.messages = messages
        return Reply(text=json.dumps({"questions": [QUESTION]}), input_tokens=10, output_tokens=5)


def test_generate_sends_source_and_parses_quiz() -> None:
    llm = FakeLLM()
    quiz, reply = generate("SLIDES TEXT", llm)
    assert "SLIDES TEXT" in llm.messages[-1]["content"]
    assert quiz.questions[0].concept == "agent loop"
    assert reply.output_tokens == 5


def test_write_trace_appends_jsonl(tmp_path: Path) -> None:
    write_trace(tmp_path, {"version": "v0"})
    write_trace(tmp_path, {"version": "v0"})
    lines = (tmp_path / "v0.jsonl").read_text().splitlines()
    assert [json.loads(line)["version"] for line in lines] == ["v0", "v0"]
