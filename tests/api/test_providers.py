import json

import httpx
import pytest

from app.contracts.services import DependencyFailure
from app.providers.openai import OpenAIChatProvider, OpenAIEmbeddingProvider, strict_schema, tool_schemas


async def test_responses_request_and_structured_draft():
    captured = []
    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [
            {"type": "output_text", "text": json.dumps({"answer_citation_ids": [], "explanations": [],
                                                         "clarification": None, "required_tools": []})}]}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAIChatProvider("fake-key", "configured-test-model", client=client)
        result = await provider.complete([{"role": "user", "content": "hi"}], tool_schemas(), 1)
    assert result.draft is not None
    assert captured[0]["store"] is False and captured[0]["parallel_tool_calls"] is False
    assert captured[0]["text"]["format"]["strict"] is True
    assert {t["name"] for t in captured[0]["tools"]} == {"lookup_stock", "search_procedures", "check_build_readiness"}


async def test_reasoning_and_call_ids_are_preserved():
    output = [{"type": "reasoning", "id": "reasoning-1", "summary": []},
              {"type": "function_call", "call_id": "call-1", "name": "lookup_stock", "arguments": '{"part_query":"P1"}'}]
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"status": "completed", "output": output}))) as client:
        result = await OpenAIChatProvider("fake", "model", client=client).complete([], tool_schemas(), 1)
    assert result.continuation == output and result.tool_calls[0].call_id == "call-1"


@pytest.mark.parametrize("status,retryable", [(401, False), (400, False), (429, True), (500, True)])
async def test_http_failures_sanitized_and_adapter_never_retries(status, retryable):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(status, text="fake-key do-not-disclose")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(DependencyFailure) as error:
            await OpenAIChatProvider("fake-key", "model", client=client).complete([], tool_schemas(), 1)
    assert len(requests) == 1 and error.value.retryable is retryable
    assert "fake-key" not in str(error.value)


@pytest.mark.parametrize("data", [
    {"status": "incomplete", "output": []},
    {"status": "completed", "output": []},
    {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": "not JSON"}]}]},
    {"status": "completed", "output": [{"type": "web_search_call"}]},
])
async def test_invalid_provider_data(data):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=data))) as client:
        with pytest.raises(DependencyFailure, match="invalid_provider_response"):
            await OpenAIChatProvider("fake", "model", client=client).complete([], tool_schemas(), 1)


async def test_embeddings_restore_input_order_and_return_generation_metadata():
    payloads = []
    def handler(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(200, json={"model": "embedding-test", "data": [
            {"index": 1, "embedding": [0.0, 1.0]}, {"index": 0, "embedding": [1.0, 0.0]}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OpenAIEmbeddingProvider("fake", "embedding-test", dimension=2, client=client).embed(["one", "two"], 1)
    assert result.vectors == [[1.0, 0.0], [0.0, 1.0]]
    assert (result.provider, result.model, result.dimension) == ("openai", "embedding-test", 2)
    assert payloads[0]["encoding_format"] == "float" and payloads[0]["dimensions"] == 2


@pytest.mark.parametrize("rows", [[], [{"index": 1, "embedding": [1.0]}],
    [{"index": 0, "embedding": []}], [{"index": 0, "embedding": [True]}],
    [{"index": 0, "embedding": ["1.0"]}],
    [{"index": 0, "embedding": [1.0]}, {"index": 0, "embedding": [1.0]}],
])
async def test_embedding_count_shape_and_value_validation(rows):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"model": "e", "data": rows}))) as client:
        with pytest.raises(DependencyFailure, match="invalid_embedding_response"):
            await OpenAIEmbeddingProvider("fake", "e", client=client).embed(["one"], 1)


async def test_embedding_nonfinite_rejected():
    content = b'{"model":"e","data":[{"index":0,"embedding":[NaN]}]}'
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=content))) as client:
        with pytest.raises(DependencyFailure, match="invalid_embedding_response"):
            await OpenAIEmbeddingProvider("fake", "e", client=client).embed(["one"], 1)


def test_strict_schema_requires_optional_fields_without_mutating_original():
    original = {"type": "object", "properties": {"x": {"type": "integer", "default": 5}}}
    result = strict_schema(original)
    assert result["required"] == ["x"] and result["additionalProperties"] is False
    assert "default" not in result["properties"]["x"]
    assert original["properties"]["x"]["default"] == 5
