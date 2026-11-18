"""Deterministic assembly: fix answer-position bias and order by difficulty with plain code."""

import random

from quizgen.schema import Question, Quiz

N_OPTIONS = 4
DIFFICULTY_ORDER = {"easy": 0, "medium": 1, "hard": 2}


def _place_answer(question: Question, position: int, rng: random.Random) -> Question:
    """Shuffle the wrong options and put the correct one at `position`."""
    correct = question.options[question.answer_index]
    wrong = [o for i, o in enumerate(question.options) if i != question.answer_index]
    rng.shuffle(wrong)
    wrong.insert(position, correct)
    return question.model_copy(update={"options": wrong, "answer_index": position})


def assemble(questions: list[Question], rng: random.Random) -> Quiz:
    """Spread correct answers evenly over positions, then order questions easy to hard."""
    positions = [i % N_OPTIONS for i in range(len(questions))]
    rng.shuffle(positions)
    placed = [_place_answer(q, p, rng) for q, p in zip(questions, positions, strict=True)]
    return Quiz(questions=sorted(placed, key=lambda q: DIFFICULTY_ORDER[q.difficulty]))
