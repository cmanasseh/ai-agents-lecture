"""The only module that talks to Ollama. Swap models with the QUIZGEN_MODEL env var."""

import os
from dataclasses import dataclass
from typing import Protocol

import ollama

DEFAULT_MODEL = "qwen3:8b"


@dataclass(frozen=True)
class Reply:
    """What a model call returns: the text and its token counts."""

    text: str
    input_tokens: int
    output_tokens: int


class LLM(Protocol):
    """Anything that can answer a chat with JSON matching a schema."""

    def chat(self, messages: list[dict], schema: dict) -> Reply: ...


def model_name() -> str:
    """The model selected for this run."""
    return os.environ.get("QUIZGEN_MODEL", DEFAULT_MODEL)


class OllamaLLM:
    """LLM backed by a local Ollama server, with output constrained to a JSON schema."""

    def __init__(self, model: str) -> None:
        self.model = model

    def chat(self, messages: list[dict], schema: dict) -> Reply:
        """Send the messages; the reply text is JSON matching `schema`."""
        response = ollama.chat(model=self.model, messages=messages, format=schema, think=False)
        return Reply(
            text=response.message.content or "",
            input_tokens=response.prompt_eval_count or 0,
            output_tokens=response.eval_count or 0,
        )
