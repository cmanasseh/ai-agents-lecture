from quizgen.grounding import is_grounded

SOURCE = """An agent is a model using tools in a loop.

| Use when the steps are | unknown | known |

The feedback loop is around the whole
agent. A check compares the output with the specification."""


def test_exact_quote_is_grounded() -> None:
    assert is_grounded("An agent is a model using tools in a loop.", SOURCE)


def test_quote_across_line_wrap_is_grounded() -> None:
    assert is_grounded("The feedback loop is around the whole agent.", SOURCE)


def test_paraphrase_is_not_grounded() -> None:
    assert not is_grounded("An agent is an LLM calling tools repeatedly.", SOURCE)


def test_flattened_table_row_is_not_grounded() -> None:
    assert not is_grounded("Use when the steps are: unknown | known", SOURCE)


def test_case_matters() -> None:
    assert not is_grounded("an agent is a model using tools in a loop.", SOURCE)
