"""The contract: what a quiz looks like, whatever version produced it."""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field

MIN_QUOTE_WORDS = 5
MAX_QUOTE_WORDS = 40


def _quote_is_short(quote: str) -> str:
    """A quote must pin down one fact, not copy a whole paragraph."""
    n = len(quote.split())
    if not MIN_QUOTE_WORDS <= n <= MAX_QUOTE_WORDS:
        msg = f"source_quote has {n} words; use {MIN_QUOTE_WORDS}-{MAX_QUOTE_WORDS}"
        raise ValueError(msg)
    return quote


Quote = Annotated[str, AfterValidator(_quote_is_short)]
Difficulty = Literal["easy", "medium", "hard"]


class Question(BaseModel):
    """One multiple-choice question, grounded in a verbatim quote from the source."""

    concept: str
    stem: str
    options: list[str] = Field(min_length=4, max_length=4)
    answer_index: int = Field(ge=0, le=3)
    source_quote: Quote
    difficulty: Difficulty


class Quiz(BaseModel):
    """A list of questions."""

    questions: list[Question]


class Concept(BaseModel):
    """A concept worth a question, and the verbatim quote that states it."""

    concept: str
    source_quote: Quote


class Concepts(BaseModel):
    """What the concept extractor returns."""

    concepts: list[Concept]
