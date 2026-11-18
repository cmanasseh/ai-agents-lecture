"""v2: an agent graph. The program owns the control flow.

extract concepts -> fan-out question writers -> critic -> revise -> assemble.
Nodes are functions; edges are the code in `run`; fan-out is asyncio.gather.
"""

import asyncio
import hashlib
import json
import random
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from quizgen.assemble import assemble
from quizgen.grounding import is_grounded
from quizgen.llm import LLM, CountingLLM, OllamaLLM, model_name
from quizgen.schema import Concept, Concepts, Difficulty, Question, Quiz
from quizgen.trace import RUNS_DIR, write_trace

VERSION = "v2"
N_QUESTIONS = 5
N_CONCEPTS_ASKED = 8
MAX_REVISIONS = 2
DIFFICULTIES: tuple[Difficulty, ...] = ("easy", "medium", "hard")
OUT_DIR = Path("data/quizes/v2")

EXTRACT_PROMPT = f"""List {N_CONCEPTS_ASKED} distinct concepts a student should learn from the text
below. For each, copy one short sentence from the text, word for word, that states it.

TEXT:
"""
WRITE_PROMPT = """Write one {difficulty} multiple-choice question about "{concept}".
It must be answerable from this quote alone: "{quote}"
Give 4 options: exactly one is correct; the others are plausible but wrong given the quote."""
CRITIC_PROMPT = """Review this quiz question against its quote.
Quote: "{quote}"
Question: {stem}
Options: {options}
Marked answer: {answer}
Is the marked answer correct according to the quote, and is every other option wrong?
Reply ok=true, or ok=false with the problem in one sentence."""


class Draft(BaseModel):
    """What a question writer returns; code adds the concept, quote and difficulty."""

    stem: str
    options: list[str] = Field(min_length=4, max_length=4)
    answer_index: int = Field(ge=0, le=3)


class Verdict(BaseModel):
    """What the critic returns."""

    ok: bool
    problem: str


@dataclass(frozen=True)
class NodeResult:
    """One question node's output: the question, unresolved problems, revisions used."""

    question: Question | None
    problems: list[str]
    revisions: int


@dataclass(frozen=True)
class GraphResult:
    """The assembled quiz and what each node did."""

    quiz: Quiz
    concepts: list[Concept]
    nodes: list[NodeResult]


def ask(llm: LLM, prompt: str, model: type[BaseModel]) -> str:
    """One structured call: the reply is JSON matching `model`."""
    return llm.chat([{"role": "user", "content": prompt}], model.model_json_schema()).text


def extract_concepts(source: str, llm: LLM) -> list[Concept]:
    """Ask for concepts; keep only those whose quote is valid and grounded (code gate)."""
    raw = json.loads(ask(llm, EXTRACT_PROMPT + source, Concepts)).get("concepts", [])
    kept: dict[str, Concept] = {}
    for item in raw:
        try:
            concept = Concept.model_validate(item)
        except ValidationError:
            continue  # expected: the gate drops invalid concepts
        if is_grounded(concept.source_quote, source):
            kept.setdefault(" ".join(concept.source_quote.split()), concept)
    return list(kept.values())[:N_QUESTIONS]


def critique(concept: Concept, draft: Draft, llm: LLM) -> list[str]:
    """Code checks first; only if they pass, ask the LLM critic."""
    if len(set(draft.options)) < len(draft.options):
        return ["the 4 options must all be different"]
    prompt = CRITIC_PROMPT.format(
        quote=concept.source_quote,
        stem=draft.stem,
        options=draft.options,
        answer=draft.options[draft.answer_index],
    )
    verdict = Verdict.model_validate_json(ask(llm, prompt, Verdict))
    return [] if verdict.ok else [verdict.problem or "the critic rejected the question"]


def question_node(concept: Concept, difficulty: Difficulty, llm: LLM) -> NodeResult:
    """Write -> critique -> revise, at most MAX_REVISIONS times. The program owns the loop."""
    prompt = WRITE_PROMPT.format(
        difficulty=difficulty, concept=concept.concept, quote=concept.source_quote
    )
    draft, problems = None, []
    for revision in range(MAX_REVISIONS + 1):
        feedback = (
            f"\nA reviewer rejected your last version: {problems}. Fix it." if problems else ""
        )
        try:
            draft = Draft.model_validate_json(ask(llm, prompt + feedback, Draft))
        except ValidationError as e:
            problems = [err["msg"] for err in e.errors()]
            continue
        problems = critique(concept, draft, llm)
        if not problems:
            return NodeResult(build(concept, difficulty, draft), [], revision)
    return NodeResult(build(concept, difficulty, draft) if draft else None, problems, MAX_REVISIONS)


def build(concept: Concept, difficulty: Difficulty, draft: Draft) -> Question:
    """Code, not the model, sets the concept, the quote and the difficulty."""
    return Question(
        concept=concept.concept,
        stem=draft.stem,
        options=draft.options,
        answer_index=draft.answer_index,
        source_quote=concept.source_quote,
        difficulty=difficulty,
    )


async def run(source: str, llm: LLM, rng: random.Random | None = None) -> GraphResult:
    """The graph: extract, fan out one node per concept, keep the accepted, assemble."""
    concepts = extract_concepts(source, llm)
    nodes = await asyncio.gather(
        *(
            asyncio.to_thread(question_node, c, DIFFICULTIES[i % len(DIFFICULTIES)], llm)
            for i, c in enumerate(concepts)
        )
    )
    accepted = [n.question for n in nodes if n.question and not n.problems]
    return GraphResult(assemble(accepted, rng or random.Random()), concepts, list(nodes))


def main() -> None:
    """Generate one quiz from the file in argv[1]; save it and trace the run."""
    source = Path(sys.argv[1]).read_text()
    model = model_name()
    llm = CountingLLM(OllamaLLM(model))
    start = time.perf_counter()
    result = asyncio.run(run(source, llm))
    latency = time.perf_counter() - start

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"quiz_{stamp}.json"
    out_path.write_text(result.quiz.model_dump_json(indent=2))

    unresolved = [
        {"concept": c.concept, "problems": n.problems}
        for c, n in zip(result.concepts, result.nodes, strict=True)
        if n.problems
    ]
    write_trace(
        RUNS_DIR,
        {
            "version": VERSION,
            "model": model,
            "input_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "input_tokens": llm.input_tokens,
            "output_tokens": llm.output_tokens,
            "latency_s": round(latency, 2),
            "concepts_found": len(result.concepts),
            "revisions": [n.revisions for n in result.nodes],
            "unresolved": unresolved,
            "timestamp": stamp,
            "quiz": result.quiz.model_dump(),
        },
    )
    n = len(result.quiz.questions)
    print(f"{n} questions, {len(unresolved)} unresolved, {latency:.1f}s -> {out_path}")


if __name__ == "__main__":
    main()
