"""Transport and domain boundaries for shared contracts v1."""
from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
SourceText = Annotated[str, StringConstraints(min_length=1)]
Identifier = Annotated[str, StringConstraints(min_length=1, max_length=200)]
Query = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
Quantity = Annotated[int, Field(strict=True, ge=1, le=10000)]
Count = Annotated[int, Field(strict=True, ge=0)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True, revalidate_instances="always")


class ProcedureSelection(Model):
    document_id: Identifier
    version: Identifier
    section_id: Identifier


class Selection(Model):
    assembly_id: Identifier | None = None
    part_id: Identifier | None = None
    procedure: ProcedureSelection | None = None

    @model_validator(mode="after")
    def one_inventory_selection(self):
        if self.assembly_id and self.part_id:
            raise ValueError("Select an assembly or a part, not both")
        return self


class HistoryMessage(Model):
    role: Literal["user", "assistant"]
    content: Annotated[str, StringConstraints(min_length=1, max_length=2000)]


class ChatRequest(Model):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
    history: list[HistoryMessage] = Field(default_factory=list, max_length=8)
    selection: Selection | None = None


class Choice(Model):
    id: Identifier
    label: Text


class Clarification(Model):
    kind: Literal["assembly", "part", "quantity", "procedure"]
    question: Text
    choices: list[Choice] = Field(default_factory=list, max_length=20)


class Error(Model):
    code: str
    message: str
    retryable: bool


class Citation(Model):
    citation_id: Identifier
    document_id: Identifier
    version: Identifier
    section_id: Identifier
    title: Text
    quoted_text: SourceText
    source_uri: str


class SourceSection(ProcedureSelection):
    title: Text
    text: SourceText
    source_uri: str
    is_current: bool


class SourceStep(Model):
    step_id: Identifier
    text: SourceText


class SourceWarning(Model):
    warning_id: Identifier
    text: SourceText
    applies_to_step_ids: list[Identifier] = Field(default_factory=list)


class SourcePrerequisite(Model):
    id: Identifier
    text: SourceText


class Passage(SourceSection):
    chunk_id: Identifier
    score: float = Field(allow_inf_nan=False)
    score_method: Text
    steps: list[SourceStep] = Field(default_factory=list)
    warnings: list[SourceWarning] = Field(default_factory=list)
    prerequisites: list[SourcePrerequisite] = Field(default_factory=list)

    @model_validator(mode="after")
    def source_integrity(self):
        ids = [step.step_id for step in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate source step IDs")
        for item in [*self.steps, *self.warnings, *self.prerequisites]:
            if item.text not in self.text:
                raise ValueError("Required source text must be an exact excerpt")
        if any(set(w.applies_to_step_ids) - set(ids) for w in self.warnings):
            raise ValueError("Warning references unknown source step")
        return self


class SearchResult(Model):
    status: Literal["ok", "no_evidence", "conflict", "unavailable"]
    passages: list[Passage] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    corpus_revision: str | None = None
    retrieval_mode: str

    @model_validator(mode="after")
    def evidence_state(self):
        if self.status == "ok" and (not self.passages or self.conflicts):
            raise ValueError("Successful retrieval requires nonconflicting passages")
        return self


class ProcedureStep(SourceStep):
    ordinal: Annotated[int, Field(ge=1)]
    citation_ids: list[Identifier]
    explanation: str | None = None


class WarningBlock(SourceWarning):
    citation_ids: list[Identifier]


class Prerequisite(SourcePrerequisite):
    citation_ids: list[Identifier]


class SourceIdentity(ProcedureSelection):
    is_current: bool


class ProcedureResult(Model):
    state: Literal["ok", "no_evidence", "conflict", "unavailable"]
    sources: list[SourceIdentity] = Field(default_factory=list)
    steps: list[ProcedureStep] = Field(default_factory=list)
    warnings: list[WarningBlock] = Field(default_factory=list)
    prerequisites: list[Prerequisite] = Field(default_factory=list)
    explanation: str | None = None
    fallback_used: bool = False


class Snapshot(Model):
    snapshot_id: Identifier
    captured_at: AwareDatetime


InventoryState = Literal["ok", "ambiguous", "not_found", "incomplete", "unavailable"]


class StockMatch(Model):
    part_id: Identifier
    label: Text
    available: Count | None
    unit: Text


class StockResult(Model):
    kind: Literal["stock"] = "stock"
    state: InventoryState
    snapshot: Snapshot | None
    matches: list[StockMatch]

    @model_validator(mode="after")
    def consistency(self):
        if self.state != "unavailable" and self.snapshot is None:
            raise ValueError("Inventory reads require a snapshot")
        if self.state == "ok" and (len(self.matches) != 1 or self.matches[0].available is None):
            raise ValueError("Stock success requires one known quantity")
        if self.state == "ambiguous" and (len(self.matches) < 2 or any(m.available is not None for m in self.matches)):
            raise ValueError("Ambiguity requires identities only")
        if self.state == "not_found" and self.matches:
            raise ValueError("Missing stock cannot have matches")
        return self


class Component(Model):
    part_id: Identifier
    per_assembly: Annotated[int, Field(strict=True, ge=1)]
    required: Count
    available: Count | None
    shortage: Count | None


class BuildResult(Model):
    kind: Literal["build"] = "build"
    state: InventoryState
    snapshot: Snapshot | None
    assembly_id: Identifier
    requested_units: Quantity
    ready: bool | None
    components: list[Component]

    @model_validator(mode="after")
    def consistency(self):
        if self.state != "unavailable" and self.snapshot is None:
            raise ValueError("Inventory reads require a snapshot")
        if len({c.part_id for c in self.components}) != len(self.components):
            raise ValueError("Duplicate BOM components")
        for c in self.components:
            if c.required != c.per_assembly * self.requested_units:
                raise ValueError("Invalid component requirement")
            expected = None if c.available is None else max(c.required - c.available, 0)
            if c.shortage != expected:
                raise ValueError("Invalid component shortage")
        missing = not self.components or any(c.available is None for c in self.components)
        shortage = any(c.shortage is not None and c.shortage > 0 for c in self.components)
        if self.state in {"ok", "incomplete"}:
            expected_ready = False if shortage else (None if missing or self.state == "incomplete" else True)
            if self.ready != expected_ready or (missing and self.state == "ok"):
                raise ValueError("Invalid readiness state")
        elif self.ready is not None:
            raise ValueError("Unresolved build cannot have readiness")
        return self


InventoryResult = Annotated[StockResult | BuildResult, Field(discriminator="kind")]


class ChatResponse(Model):
    answer: str
    answer_citation_ids: list[Identifier] = Field(default_factory=list)
    status: Literal["answered", "needs_clarification", "insufficient_evidence", "temporarily_unavailable"]
    citations: list[Citation] = Field(default_factory=list)
    procedure_result: ProcedureResult | None = None
    inventory_result: InventoryResult | None = None
    clarification: Clarification | None = None
    error: Error | None = None
    trace_id: UUID = Field(default_factory=uuid4)
    data_mode: Literal["synthetic"] = "synthetic"

    @model_validator(mode="after")
    def references(self):
        if (self.status == "needs_clarification") != (self.clarification is not None):
            raise ValueError("Clarification must agree with status")
        ids = {c.citation_id for c in self.citations}
        if len(ids) != len(self.citations) or set(self.answer_citation_ids) - ids:
            raise ValueError("Invalid citation IDs")
        if self.procedure_result:
            p = self.procedure_result
            if any(set(x.citation_ids) - ids for x in [*p.steps, *p.warnings, *p.prerequisites]):
                raise ValueError("Unknown procedure citation")
        return self


class ValidationErrorResponse(Model):
    error: Error
    trace_id: UUID = Field(default_factory=uuid4)
    data_mode: Literal["synthetic"] = "synthetic"


class Assembly(Model):
    assembly_id: Identifier
    label: Text


class AssembliesResponse(Model):
    items: list[Assembly] = Field(max_length=20)


class HealthResponse(Model):
    status: Literal["ok"] = "ok"


class ReadyResponse(Model):
    status: Literal["ready", "not_ready"]
    database: Literal["ready", "unavailable"]
    corpus: Literal["ready", "missing", "unavailable"]
    provider: Literal["configured", "missing"]


class SearchArguments(Model):
    query: Query
    limit: Annotated[int, Field(strict=True, ge=1, le=5)] = 5


class StockArguments(Model):
    part_query: Query


class BuildArguments(Model):
    assembly_id: Identifier
    quantity: Quantity


TOOL_ARGUMENTS = {"search_procedures": SearchArguments, "lookup_stock": StockArguments,
                  "check_build_readiness": BuildArguments}
