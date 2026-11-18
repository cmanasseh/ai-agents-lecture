"""The contract: what a quiz looks like, whatever version produced it."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

MIN_QUOTE_WORDS = 5
MAX_QUOTE_WORDS = 40


class Question(BaseModel):
    """One multiple-choice question, grounded in a verbatim quote from the source."""

    concept: str
    stem: str
    options: list[str] = Field(min_length=4, max_length=4)
    answer_index: int = Field(ge=0, le=3)
    source_quote: str
    difficulty: Literal["easy", "medium", "hard"]

    @field_validator("source_quote")
    @classmethod
    def quote_is_short(cls, quote: str) -> str:
        """A quote must pin down one fact, not copy a whole paragraph."""
        n = len(quote.split())
        if not MIN_QUOTE_WORDS <= n <= MAX_QUOTE_WORDS:
            msg = f"source_quote has {n} words; use {MIN_QUOTE_WORDS}-{MAX_QUOTE_WORDS}"
            raise ValueError(msg)
        return quote


class Quiz(BaseModel):
    """A list of questions."""

    questions: list[Question]
