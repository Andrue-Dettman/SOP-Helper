import pytest
from pydantic import ValidationError

from app.assistant.evidence import procedure_evidence
from app.contracts.models import BuildResult, ChatResponse, Component, Passage, SourceStep


def test_incomplete_build_retains_known_shortage(services):
    result = BuildResult(state="incomplete", snapshot=services.snapshot, assembly_id="A1", requested_units=2,
                         ready=False, components=[
                             Component(part_id="P1", per_assembly=2, required=4, available=1, shortage=3),
                             Component(part_id="P2", per_assembly=1, required=2, available=None, shortage=None)])
    assert result.ready is False and result.components[1].shortage is None


@pytest.mark.parametrize("components,ready,state", [
    ([], True, "ok"), ([], False, "incomplete"),
    ([dict(part_id="P1", per_assembly=2, required=4, available=None, shortage=0)], None, "incomplete"),
    ([dict(part_id="P1", per_assembly=2, required=99, available=100, shortage=0)], True, "ok"),
    ([dict(part_id="P1", per_assembly=2, required=4, available=0, shortage=4)], True, "ok"),
    ([dict(part_id="P1", per_assembly=2, required=4, available=5, shortage=0)] * 2, True, "ok"),
])
def test_invalid_inventory_result_cannot_cross_boundary(services, components, ready, state):
    with pytest.raises(ValidationError):
        BuildResult(state=state, snapshot=services.snapshot, assembly_id="A1", requested_units=2,
                    ready=ready, components=components)


def test_empty_bom_is_unknown(services):
    result = BuildResult(state="incomplete", snapshot=services.snapshot, assembly_id="A1", requested_units=2, ready=None, components=[])
    assert result.ready is None


def test_broken_response_references_rejected():
    with pytest.raises(ValidationError):
        ChatResponse(answer="unsupported", status="answered", answer_citation_ids=["invented"])


def test_required_source_text_must_be_exact_excerpt(services):
    data = services.passage.model_dump()
    data["steps"] = [{"step_id": "s", "text": "Invented action"}]
    with pytest.raises(ValidationError):
        Passage(**data)


def test_multiple_chunks_from_same_section_keep_all_required_steps(services):
    second = services.passage.model_copy(update={"chunk_id": "chunk-2", "text": "Record the delivery.",
        "steps": [SourceStep(step_id="record", text="Record the delivery.")], "warnings": []})
    services.search.passages.append(second)
    procedure, citations = procedure_evidence(services.search)
    assert len(procedure.sources) == 1 and len(procedure.steps) == 2 and len(citations) == 2
    assert procedure.steps[1].text == "Record the delivery."
