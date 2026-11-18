import pytest
from pydantic import ValidationError

from quizgen.schema import Concept, Question

VALID = {
    "concept": "agent loop",
    "stem": "Who owns the control flow in an agent loop?",
    "options": ["The model", "The program", "The user", "Nobody"],
    "answer_index": 0,
    "source_quote": "the model decides what happens next",
    "difficulty": "easy",
}


def test_valid_question_parses() -> None:
    assert Question.model_validate(VALID).answer_index == 0


@pytest.mark.parametrize(
    "override",
    [
        {"options": ["a", "b", "c"]},
        {"options": ["a", "b", "c", "d", "e"]},
        {"answer_index": 4},
        {"answer_index": -1},
        {"difficulty": "trivial"},
        {"source_quote": "only four words here"},
        {"source_quote": " ".join(["word"] * 41)},
    ],
)
def test_invalid_question_is_rejected(override: dict) -> None:
    with pytest.raises(ValidationError):
        Question.model_validate(VALID | override)


def test_concept_quote_follows_the_same_length_rule() -> None:
    with pytest.raises(ValidationError):
        Concept(concept="agent", source_quote="too short")
