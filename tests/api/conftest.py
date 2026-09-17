"""Offline fixtures only: these are not live model or real inventory evidence."""
import copy
import json
from datetime import datetime, timezone

import pytest

from app.contracts.models import Assembly, BuildResult, Component, Passage, SearchResult, Snapshot, SourceSection, SourceStep, SourceWarning, StockMatch, StockResult
from app.providers.base import Draft, ProviderTurn, ToolCall


def call(name, **args):
    return ToolCall(call_id="call-" + name, name=name, arguments=json.dumps(args))


def final_draft(messages):
    citations = []
    for message in messages:
        if message.get("type") == "function_call_output":
            result = json.loads(message["output"])
            citations.extend(c["citation_id"] for c in result.get("citations", []))
    return ProviderTurn(draft=Draft(answer_citation_ids=citations, explanations=[], clarification=None, required_tools=[]))


class FakeProvider:
    configured = True
    execution_mode = "offline_fixture"

    def __init__(self, turns=()):
        self.turns = list(turns)
        self.calls = 0
        self.messages = []

    async def complete(self, messages, tool_schemas, timeout_s):
        self.calls += 1
        self.messages.append(copy.deepcopy(messages))
        turn = self.turns.pop(0) if self.turns else final_draft
        if isinstance(turn, Exception):
            raise turn
        return turn(messages) if callable(turn) else turn


class FakeServices:
    def __init__(self):
        self.calls = []
        self.snapshot = Snapshot(snapshot_id="fictional-001", captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.passage = Passage(document_id="receiving", version="1", section_id="inspect", title="Inspect delivery",
                               text="Check 2 labels. Stop if labels are missing.", source_uri="https://untrusted.invalid/",
                               is_current=True, chunk_id="chunk-1", score=1.0, score_method="keyword",
                               steps=[SourceStep(step_id="check", text="Check 2 labels.")],
                               warnings=[SourceWarning(warning_id="stop", text="Stop if labels are missing.", applies_to_step_ids=["check"])])
        self.search = SearchResult(status="ok", passages=[self.passage], corpus_revision="corpus-1", retrieval_mode="keyword")
        self.stock = StockResult(state="ok", snapshot=self.snapshot,
                                 matches=[StockMatch(part_id="P1", label="Fictional bolt", available=5, unit="each")])
        self.catalog = [Assembly(assembly_id="A1", label="Fictional kit")]

    async def search_procedures(self, query, limit, *, selection=None):
        self.calls.append(("search", query, limit, selection))
        return self.search

    async def section(self, document_id, version, section_id):
        self.calls.append(("section", document_id, version, section_id))
        if (document_id, version, section_id) != (self.passage.document_id, self.passage.version, self.passage.section_id):
            return None
        return SourceSection(**{k: getattr(self.passage, k) for k in SourceSection.model_fields})

    async def assemblies(self, query, limit):
        self.calls.append(("catalog", query, limit))
        return self.catalog[:limit]

    async def lookup_stock(self, part_query):
        self.calls.append(("stock", part_query))
        return self.stock

    async def check_build_readiness(self, assembly_id, quantity):
        self.calls.append(("build", assembly_id, quantity))
        required = 2 * quantity
        return BuildResult(state="ok", snapshot=self.snapshot, assembly_id=assembly_id,
                           requested_units=quantity, ready=required <= 5,
                           components=[Component(part_id="P1", per_assembly=2, required=required,
                                                 available=5, shortage=max(required - 5, 0))])

    async def readiness(self):
        return True, True


@pytest.fixture
def services():
    return FakeServices()
