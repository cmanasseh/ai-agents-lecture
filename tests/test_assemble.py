import random
from collections import Counter

from quizgen.assemble import assemble
from quizgen.schema import Question


def question(i: int, difficulty: str) -> Question:
    return Question(
        concept=f"c{i}",
        stem=f"Question {i}?",
        options=[f"right {i}", f"wrong {i}a", f"wrong {i}b", f"wrong {i}c"],
        answer_index=0,
        source_quote="a quote of at least five words",
        difficulty=difficulty,
    )


QUESTIONS = [question(i, d) for i, d in enumerate(["hard", "easy", "medium", "easy", "hard"])]


def test_answer_positions_are_balanced() -> None:
    quiz = assemble(QUESTIONS, random.Random(0))
    counts = Counter(q.answer_index for q in quiz.questions)
    assert max(counts.values()) - min(counts.get(i, 0) for i in range(4)) <= 1


def test_correct_option_is_kept() -> None:
    quiz = assemble(QUESTIONS, random.Random(0))
    for q in quiz.questions:
        assert q.options[q.answer_index] == f"right {q.concept[1:]}"
        assert sorted(q.options) == sorted(QUESTIONS[int(q.concept[1:])].options)


def test_questions_are_ordered_by_difficulty() -> None:
    quiz = assemble(QUESTIONS, random.Random(0))
    assert [q.difficulty for q in quiz.questions] == ["easy", "easy", "medium", "hard", "hard"]


def test_same_seed_gives_same_quiz() -> None:
    assert assemble(QUESTIONS, random.Random(1)) == assemble(QUESTIONS, random.Random(1))
