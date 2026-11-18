"""Entry point for the quiz generator."""

import sys
from pathlib import Path


def main() -> None:
    """Read the slides and report their size."""
    slides = Path(sys.argv[1]).read_text()
    print(f"Read {len(slides)} characters of slides.")


if __name__ == "__main__":
    main()
