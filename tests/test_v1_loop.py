from quizgen.llm import Reply, ToolCall, tool_spec
from quizgen.schema import Quiz
from quizgen.v1_loop import N_QUESTIONS, check, run

SOURCE = "An agent is a model using tools in a loop. The harness is everything else."


def question(quote: str) -> dict:
    return {
        "concept": "agent",
        "stem": "What is an agent?",
        "options": ["A model using tools in a loop", "A database", "A compiler", "A GPU"],
        "answer_index": 0,
        "source_quote": quote,
        "difficulty": "easy",
    }


GOOD = {"questions": [question("An agent is a model using tools in a loop.")] * N_QUESTIONS}
UNGROUNDED = {"questions": [question("An agent is an LLM calling tools.")] * N_QUESTIONS}


def submit(arguments: dict) -> Reply:
    return Reply("", 10, 5, [ToolCall("submit_quiz", arguments)])


class ScriptedLLM:
    """Returns canned replies in order and records the messages of each call."""

    def __init__(self, replies: list[Reply]) -> None:
        self.replies = replies
        self.calls: list[list[dict]] = []

    def chat(self, messages: list[dict], schema: dict | None = None, tools=None) -> Reply:
        self.calls.append(list(messages))
        return self.replies[len(self.calls) - 1]


def test_check_accepts_grounded_quiz() -> None:
    quiz, errors = check(GOOD, SOURCE)
    assert errors == []
    assert isinstance(quiz, Quiz)


def test_check_reports_ungrounded_quote() -> None:
    _, errors = check(UNGROUNDED, SOURCE)
    assert len(errors) == N_QUESTIONS
    assert "not found verbatim" in errors[0]


def test_check_reports_schema_errors() -> None:
    quiz, errors = check({"questions": [question("too short")]}, SOURCE)
    assert quiz is None
    assert "source_quote" in errors[0]


def test_check_reports_wrong_question_count() -> None:
    _, errors = check({"questions": GOOD["questions"][:2]}, SOURCE)
    assert errors == [f"expected {N_QUESTIONS} questions, got 2"]


def test_loop_feeds_errors_back_until_valid() -> None:
    llm = ScriptedLLM([submit(UNGROUNDED), submit(GOOD)])
    result = run(SOURCE, llm)
    assert result.turns == 2
    assert result.errors == []
    assert result.output_tokens == 10
    feedback = llm.calls[1][-1]
    assert feedback["role"] == "tool"
    assert "not found verbatim" in feedback["content"]


def test_loop_stops_at_max_turns_with_unresolved_errors() -> None:
    llm = ScriptedLLM([submit(UNGROUNDED)] * 3)
    result = run(SOURCE, llm, max_turns=3)
    assert result.turns == 3
    assert result.errors


def test_loop_nudges_when_model_answers_in_text() -> None:
    llm = ScriptedLLM([Reply("Here is a quiz...", 10, 5), submit(GOOD)])
    result = run(SOURCE, llm)
    assert result.turns == 2
    assert "submit_quiz" in llm.calls[1][-1]["content"]


def test_tool_spec_inlines_refs() -> None:
    spec = tool_spec("submit_quiz", "Submit.", Quiz.model_json_schema())
    assert "$ref" not in str(spec)
    assert "$defs" not in str(spec)
