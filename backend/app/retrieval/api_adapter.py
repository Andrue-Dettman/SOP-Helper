"""G1's async service boundary, with exact-section contract validation.

The memory adapter is explicitly for offline integration, never a database fallback.
"""

from dataclasses import replace

from app.contracts.models import Passage, SearchResult, SourceSection
from app.contracts.services import DependencyFailure

from ..ingestion.models import SourceValidationError, source_uri, stable_id
from .service import ProcedureService, Selection


def contract_result(result: dict, snapshot) -> SearchResult:
    if result['status'] != 'ok':
        return SearchResult(status=result['status'], retrieval_mode=result['retrieval_mode'],
                            corpus_revision=result['corpus_revision'],
                            conflicts=[f"{item['procedure_key']} / {item['scope']}: " + ', '.join(
                                f"{source['document_id']}@{source['version']}" for source in item['sources'])
                                       for item in result['conflicts']])
    passages, seen = [], set()
    documents = {document.key: document for document in snapshot.documents}
    for hit in result['passages']:
        key = hit['document_id'], hit['version']
        if key in seen:
            continue
        seen.add(key)
        document = documents[key]
        all_steps = {block.block_id for block in document.blocks if block.kind == 'step'}
        # Expand a ranked hit into real, separately addressable sections. G1's
        # Passage validator forbids claiming a cross-section excerpt belongs here.
        for section in document.sections:
            blocks = [block for block in document.blocks if block.section_id == section.section_id]
            step_ids = {block.block_id for block in blocks if block.kind == 'step'}
            warnings = []
            for block in blocks:
                if block.kind != 'warning':
                    continue
                targets = all_steps if block.applies_to == ('*',) else set(block.applies_to)
                if not targets <= step_ids:
                    raise SourceValidationError('G1 contract cannot represent a warning targeting another section')
                warnings.append({'warning_id': block.block_id, 'text': block.text,
                                 'applies_to_step_ids': [step.block_id for step in document.blocks
                                                        if step.kind == 'step' and step.block_id in targets]})
            passages.append(Passage(
                document_id=document.document_id, version=document.version, section_id=section.section_id,
                title=section.title, text=section.text,
                source_uri=source_uri(document.document_id, document.version, section.section_id),
                is_current=key in snapshot.current,
                chunk_id=stable_id(document.document_id, document.version, section.section_id, snapshot.chunker_version),
                score=hit['score'], score_method=hit['score_method'],
                steps=[{'step_id': block.block_id, 'text': block.text} for block in blocks if block.kind == 'step'],
                warnings=warnings,
                prerequisites=[{'id': block.block_id, 'text': block.text} for block in blocks
                               if block.kind == 'prerequisite']))
    return SearchResult(status='ok', passages=passages, corpus_revision=snapshot.revision,
                        retrieval_mode=result['retrieval_mode'])


class MemoryRetrievalServices:
    """Explicit offline bridge used by G1/G2 contract tests."""

    def __init__(self, service: ProcedureService):
        self.service = service

    async def search_procedures(self, query, limit=5, *, selection=None):
        context = Selection(selection.document_id, selection.version, selection.section_id) if selection else None
        snapshot = self.service.catalog.snapshot()
        result = self.service.search_procedures(query, limit, selection=context)
        if result['status'] == 'unavailable':
            raise DependencyFailure('retrieval_unavailable', retryable=True)
        for hit in result['passages']:
            key = hit['document_id'], hit['version']
            if not any(document.key == key for document in snapshot.documents):
                document, _ = self.service.catalog.source(key)
                snapshot = replace(snapshot, documents=(*snapshot.documents, document))
        return contract_result(result, snapshot)

    async def section(self, document_id, version, section_id):
        try:
            return SourceSection.model_validate(self.service.get_section(document_id, section_id, version=version))
        except KeyError:
            return None

    async def readiness(self):
        # Offline memory storage cannot claim database readiness.
        return False, self.service.catalog.snapshot() is not None
