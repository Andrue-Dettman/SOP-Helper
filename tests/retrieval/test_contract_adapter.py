import asyncio

import pytest

pytest.importorskip('app.contracts.models', reason='G1 shared contract baseline is required')

from app.assistant.evidence import procedure_evidence
from app.contracts.models import ProcedureSelection, SearchResult
from app.retrieval.api_adapter import MemoryRetrievalServices
from app.retrieval.service import ProcedureService


def test_g1_contract_and_evidence_keep_whole_procedure(catalog):
    adapter = MemoryRetrievalServices(ProcedureService(catalog, mode='lexical', lexical=object()))
    result = asyncio.run(adapter.search_procedures('What does this mean?', 1, selection=ProcedureSelection(
        document_id='receiving-delivery', version='2', section_id='terms')))
    assert isinstance(result, SearchResult)
    assert [passage.section_id for passage in result.passages] == ['preparation', 'inspect-and-count', 'terms']
    procedure, citations = procedure_evidence(result)
    assert len(procedure.steps) == 4
    assert len(procedure.warnings) == 1
    assert len(procedure.prerequisites) == 1
    assert procedure.warnings[0].applies_to_step_ids == [procedure.steps[1].step_id]
    for citation in citations:
        original = asyncio.run(adapter.section(citation.document_id, citation.version, citation.section_id))
        assert citation.quoted_text == original.text


def test_g1_historical_and_missing_source_contract(catalog):
    adapter = MemoryRetrievalServices(ProcedureService(catalog, mode='lexical', lexical=object()))
    historical = asyncio.run(adapter.section('receiving-delivery', '1', 'inspect-and-count'))
    assert historical.is_current is False
    assert asyncio.run(adapter.section('receiving-delivery', 'missing', 'inspect-and-count')) is None
    assert asyncio.run(adapter.readiness()) == (False, True)
