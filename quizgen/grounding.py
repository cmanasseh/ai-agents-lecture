"""Deterministic grounding check: a tool in v1, a gate in v2, an eval in Part 2."""


def is_grounded(quote: str, source: str) -> bool:
    """True if `quote` appears verbatim in `source`, ignoring whitespace differences."""
    return " ".join(quote.split()) in " ".join(source.split())
