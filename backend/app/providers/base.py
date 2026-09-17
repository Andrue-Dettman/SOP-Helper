from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import Field

from app.contracts.models import Clarification, Identifier, Model


class ToolCall(Model):
    call_id: str
    name: str
    arguments: str


class Explanation(Model):
    step_id: Identifier
    text: str = Field(max_length=2000)


class Draft(Model):
    # No model-authored inventory prose or source metadata crosses this boundary.
    answer_citation_ids: list[str]
    explanations: list[Explanation]
    clarification: Clarification | None
    required_tools: list[Literal["search_procedures", "lookup_stock", "check_build_readiness"]]


class ProviderTurn(Model):
    tool_calls: list[ToolCall] = Field(default_factory=list, max_length=6)
    draft: Draft | None = None
    continuation: list[dict[str, Any]] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)


class EmbeddingBatch(Model):
    vectors: list[list[float]]
    provider: str
    model: str
    dimension: int = Field(ge=1)
    usage: dict[str, Any] = Field(default_factory=dict)


class ChatProvider(Protocol):
    configured: bool
    execution_mode: str

    async def complete(self, messages: list[dict], tool_schemas: list[dict], timeout_s: float) -> ProviderTurn: ...


class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str], timeout_s: float) -> EmbeddingBatch: ...
