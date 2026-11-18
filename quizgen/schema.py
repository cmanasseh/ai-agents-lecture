"""The contract: what a quiz looks like, whatever version produced it."""

from typing import Literal

from pydantic import BaseModel, Field


class Question(BaseModel):
    """One multiple-choice question, grounded in a verbatim quote from the source."""

    concept: str
    stem: str
    options: list[str] = Field(min_length=4, max_length=4)
    answer_index: int = Field(ge=0, le=3)
    source_quote: str
    difficulty: Literal["easy", "medium", "hard"]


class Quiz(BaseModel):
    """A list of questions."""

    questions: list[Question]
