import asyncio
import json
from collections import Counter

from quizgen.llm import Reply
from quizgen.schema import Concept
from quizgen.v2_graph import (
    MAX_REVISIONS,
    N_QUESTIONS,
    Draft,
    critique,
    extract_concepts,
    question_node,
    run,
)

SENTENCES = [f"Sentence number {i} explains one idea." for i in range(8)]
SOURCE = " ".join(SENTENCES)
CONCEPT = Concept(concept="idea 0", source_quote=SENTENCES[0])
DRAFT = {"stem": "What is idea 0?", "options": ["A", "B", "C", "D"], "answer_index": 0}
OK = {"ok": True, "problem": ""}
BAD = {"ok": False, "problem": "two options are correct"}


class FakeLLM:
    """Answers by schema title; verdicts come from a script, then default to OK."""

    def __init__(self, concepts: list[dict] | None = None, verdicts: list[dict] | None = None):
        self.concepts = concepts or [
            {"concept": f"idea {i}", "source_quote": s} for i, s in enumerate(SENTENCES)
        ]
        self.verdicts = list(verdicts or [])
        self.calls: list[tuple[str, str]] = []

    def chat(self, messages: list[dict], schema: dict | None = None, tools=None) -> Reply:
        title = schema["title"]
        self.calls.append((title, messages[-1]["content"]))
        if title == "Verdict":
            answer = self.verdicts.pop(0) if self.verdicts else OK
        else:
            answer = {"Concepts": {"concepts": self.concepts}, "Draft": DRAFT}[title]
        return Reply(json.dumps(answer), 10, 5)


def test_extract_gate_drops_ungrounded_and_short_quotes() -> None:
    concepts = [
        {"concept": "made up", "source_quote": "This sentence is not in the source."},
        {"concept": "short", "source_quote": "Sentence number"},
        *[{"concept": f"idea {i}", "source_quote": s} for i, s in enumerate(SENTENCES)],
    ]
    found = extract_concepts(SOURCE, FakeLLM(concepts=concepts))
    assert [c.concept for c in found] == [f"idea {i}" for i in range(N_QUESTIONS)]


def test_critic_rejection_is_sent_back_and_revised() -> None:
    llm = FakeLLM(verdicts=[BAD])
    result = question_node(CONCEPT, "easy", llm)
    assert result.revisions == 1
    assert result.problems == []
    drafts = [content for title, content in llm.calls if title == "Draft"]
    assert "two options are correct" in drafts[1]
    assert result.question.source_quote == CONCEPT.source_quote


def test_never_accepted_question_is_unresolved() -> None:
    llm = FakeLLM(verdicts=[BAD] * (MAX_REVISIONS + 1))
    result = question_node(CONCEPT, "easy", llm)
    assert result.revisions == MAX_REVISIONS
    assert result.problems == ["two options are correct"]


def test_duplicate_options_are_rejected_without_calling_the_llm() -> None:
    llm = FakeLLM()
    problems = critique(CONCEPT, Draft(**DRAFT | {"options": ["A", "A", "C", "D"]}), llm)
    assert problems
    assert llm.calls == []


def test_run_grounds_every_question_and_balances_answers() -> None:
    result = asyncio.run(run(SOURCE, FakeLLM()))
    questions = result.quiz.questions
    assert len(questions) == N_QUESTIONS
    assert {q.source_quote for q in questions} <= set(SENTENCES)
    counts = Counter(q.answer_index for q in questions)
    assert max(counts.values()) - min(counts.get(i, 0) for i in range(4)) <= 1
