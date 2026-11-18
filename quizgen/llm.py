"""The only module that talks to Ollama. Swap models with the QUIZGEN_MODEL env var."""

import os
import threading
from dataclasses import dataclass, field
from typing import Any, Protocol

import ollama

DEFAULT_MODEL = "qwen3:8b"


@dataclass(frozen=True)
class ToolCall:
    """The model asked to call tool `name` with `arguments`."""

    name: str
    arguments: dict


@dataclass(frozen=True)
class Reply:
    """What a model call returns: text, token counts, and any tool calls."""

    text: str
    input_tokens: int
    output_tokens: int
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLM(Protocol):
    """Anything that can answer a chat, optionally constrained to a schema or given tools."""

    def chat(
        self, messages: list[dict], schema: dict | None = None, tools: list[dict] | None = None
    ) -> Reply: ...


def model_name() -> str:
    """The model selected for this run."""
    return os.environ.get("QUIZGEN_MODEL", DEFAULT_MODEL)


def _inline_refs(node: Any, defs: dict) -> Any:
    """Replace every {"$ref": ...} with its definition; small models miss $refs."""
    if isinstance(node, list):
        return [_inline_refs(item, defs) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return _inline_refs(defs[node["$ref"].split("/")[-1]], defs)
    return {key: _inline_refs(value, defs) for key, value in node.items() if key != "$defs"}


def tool_spec(name: str, description: str, schema: dict) -> dict:
    """A tool definition whose parameters follow `schema`, with $refs inlined."""
    parameters = _inline_refs(schema, schema.get("$defs", {}))
    return {
        "type": "function",
        "function": {"name": name, "description": description, "parameters": parameters},
    }


class CountingLLM:
    """Wraps an LLM and sums tokens across calls, including calls from parallel threads."""

    def __init__(self, llm: LLM) -> None:
        self.llm = llm
        self.input_tokens = 0
        self.output_tokens = 0
        self._lock = threading.Lock()

    def chat(
        self, messages: list[dict], schema: dict | None = None, tools: list[dict] | None = None
    ) -> Reply:
        """Forward the call and count its tokens."""
        reply = self.llm.chat(messages, schema, tools)
        with self._lock:
            self.input_tokens += reply.input_tokens
            self.output_tokens += reply.output_tokens
        return reply


class OllamaLLM:
    """LLM backed by a local Ollama server."""

    def __init__(self, model: str) -> None:
        self.model = model

    def chat(
        self, messages: list[dict], schema: dict | None = None, tools: list[dict] | None = None
    ) -> Reply:
        """Send the messages; with `schema`, the reply text is JSON matching it."""
        response = ollama.chat(
            model=self.model, messages=messages, format=schema, tools=tools, think=False
        )
        calls = [
            ToolCall(call.function.name, dict(call.function.arguments))
            for call in response.message.tool_calls or []
        ]
        return Reply(
            text=response.message.content or "",
            input_tokens=response.prompt_eval_count or 0,
            output_tokens=response.eval_count or 0,
            tool_calls=calls,
        )
