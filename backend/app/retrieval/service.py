"""Evidence assembly without model calls, URLs from models, or generated SQL."""

from dataclasses import dataclass, replace
import math
from typing import Protocol, Sequence

from ..ingestion.catalog import Embedder, MemoryCatalog, Snapshot, validate_vectors
from ..ingestion.models import Chunk, Document, SourceValidationError, source_uri, stable_id
from ..ingestion.parser import chunk_document
from .ranking import Hit, RetrievalUnavailable, exact_cosine


@dataclass(frozen=True)
class Selection:
    """G1 supplies this from validated request context, outside model arguments."""
    document_id: str
    version: str
    section_id: str


class LexicalRanker(Protocol):
    score_method: str
    def rank(self, query: str, chunks: Sequence[Chunk]) -> tuple[Hit, ...]: ...


def _citation(document: Document, section_id: str, text: str) -> dict:
    section = next(section for section in document.sections if section.section_id == section_id)
    if not text or text not in section.text:
        raise SourceValidationError('Citation must be an exact nonempty source excerpt')
    return {'citation_id': stable_id(document.document_id, document.version, section_id, text),
            'document_id': document.document_id, 'version': document.version,
            'section_id': section_id, 'title': section.title, 'quoted_text': text,
            'source_uri': source_uri(document.document_id, document.version, section_id)}


def passage(snapshot: Snapshot, chunk: Chunk, score: float, score_method: str) -> dict:
    document = next(doc for doc in snapshot.documents if doc.key == (chunk.document_id, chunk.version))
    citations = [_citation(document, chunk.section_id, chunk.text)]
    blocks = []
    for block in document.blocks:
        citation = _citation(document, block.section_id, block.text)
        citations.append(citation)
        blocks.append({'id': block.block_id, 'kind': block.kind, 'text': block.text,
                       'section_id': block.section_id, 'order': block.order,
                       'applies_to': list(block.applies_to), 'citation_ids': [citation['citation_id']]})
    return {'document_id': document.document_id, 'version': document.version,
            'section_id': chunk.section_id, 'chunk_id': chunk.chunk_id, 'title': chunk.title,
            'text': chunk.text, 'source_uri': source_uri(document.document_id, document.version, chunk.section_id),
            'score': score, 'score_method': score_method, 'is_current': document.key in snapshot.current,
            'required_steps': [block for block in blocks if block['kind'] == 'step'],
            'warnings': [block for block in blocks if block['kind'] == 'warning'],
            'prerequisites': [block for block in blocks if block['kind'] == 'prerequisite'],
            'citations': list({citation['citation_id']: citation for citation in citations}.values())}


class ProcedureService:
    """Explicit adapters only; no fixture fallback or application-wide default store."""

    def __init__(self, catalog: MemoryCatalog, *, mode: str, lexical: LexicalRanker | None = None,
                 embedder: Embedder | None = None, minimum_similarity: float | None = None,
                 vector_ranker=None):
        if mode not in ('lexical', 'embedding'):
            raise ValueError('Choose lexical or embedding mode explicitly')
        if mode == 'lexical' and lexical is None:
            raise ValueError('Lexical mode requires a ranker')
        if mode == 'embedding' and (embedder is None or type(minimum_similarity) not in (int, float)
                                   or not math.isfinite(minimum_similarity)
                                   or not -1 <= minimum_similarity <= 1):
            raise ValueError('Embedding mode needs an adapter and explicit acceptance threshold')
        self.catalog, self.mode, self.lexical = catalog, mode, lexical
        self.embedder, self.minimum_similarity = embedder, minimum_similarity
        self.vector_ranker = vector_ranker

    def get_section(self, document_id: str, section_id: str, *, version: str) -> dict:
        """Unknown identity raises KeyError for G1 to map to HTTP 404."""
        document, current = self.catalog.source((document_id, version))
        section = next((section for section in document.sections if section.section_id == section_id), None)
        if section is None:
            raise KeyError((document_id, version, section_id))
        return {'document_id': document_id, 'version': version, 'section_id': section_id,
                'title': section.title, 'text': section.text, 'is_current': current,
                'source_uri': source_uri(document_id, version, section_id)}

    def search_procedures(self, query: str, limit: int = 5, *, selection: Selection | None = None) -> dict:
        if not isinstance(query, str) or not query.strip() or len(query) > 1000:
            raise ValueError('Query must contain 1–1000 characters and non-whitespace text')
        if type(limit) is not int or not 1 <= limit <= 5:
            raise ValueError('Limit must be an integer from 1 to 5')
        # One immutable snapshot throughout ranking, expansion, and conflict checks.
        snapshot = self.catalog.snapshot()
        base = {'status': 'unavailable', 'passages': [], 'conflicts': [],
                'corpus_revision': snapshot.revision if snapshot else None, 'retrieval_mode': self.mode}
        if snapshot is None:
            return base
        eligible = tuple(chunk for chunk in snapshot.chunks
                         if (chunk.document_id, chunk.version) in snapshot.current)
        method = ''
        if selection is not None:
            if not any(doc.key == (selection.document_id, selection.version) for doc in snapshot.documents):
                try:
                    historical, _ = self.catalog.source((selection.document_id, selection.version))
                except KeyError:
                    return {**base, 'status': 'no_evidence'}
                # Archived text is immutable. Eligibility remains pinned to the request's current set.
                snapshot = replace(snapshot, documents=(*snapshot.documents, historical),
                                   chunks=(*snapshot.chunks, *chunk_document(historical)))
            eligible = tuple(chunk for chunk in snapshot.chunks
                             if (chunk.document_id, chunk.version, chunk.section_id) ==
                             (selection.document_id, selection.version, selection.section_id))
            hits = tuple(Hit(chunk.chunk_id, 1.0) for chunk in eligible)
            method = 'explicit-selection'
        else:
            try:
                if self.mode == 'lexical':
                    hits = self.lexical.rank(query, eligible)
                    method = self.lexical.score_method
                else:
                    if snapshot.generation is None:
                        return base
                    query_vector = validate_vectors(self.embedder.embed([query]), snapshot.generation, 1)[0]
                    by_id = dict(zip((chunk.chunk_id for chunk in snapshot.chunks), snapshot.vectors, strict=True))
                    rank = self.vector_ranker.rank if self.vector_ranker else exact_cosine
                    hits = rank(query_vector, [by_id[chunk.chunk_id] for chunk in eligible],
                                eligible, self.minimum_similarity)
                    method = self.vector_ranker.score_method if self.vector_ranker else 'exact-cosine'
            except (RetrievalUnavailable, SourceValidationError, TimeoutError, ConnectionError):
                return base
        chunks = {chunk.chunk_id: chunk for chunk in eligible}
        if any(hit.chunk_id not in chunks or type(hit.score) not in (int, float)
               or not math.isfinite(hit.score) for hit in hits):
            return base
        hits = tuple(sorted({hit.chunk_id: hit for hit in hits}.values(), key=lambda hit: (-hit.score, hit.chunk_id)))
        if not hits:
            return {**base, 'status': 'no_evidence'}
        by_key = {document.key: document for document in snapshot.documents}
        current_scopes = {}
        for key in snapshot.current:
            document = by_key[key]
            current_scopes.setdefault((document.procedure_key, document.scope), []).append(key)
        conflicts = {}
        for hit in hits:
            chunk = chunks[hit.chunk_id]
            document = by_key[chunk.document_id, chunk.version]
            scope = (document.procedure_key, document.scope)
            if document.key in snapshot.current and len(current_scopes[scope]) > 1:
                conflicts[scope] = {'procedure_key': scope[0], 'scope': scope[1],
                                    'sources': [{'document_id': key[0], 'version': key[1]}
                                                for key in sorted(current_scopes[scope])]}
        if conflicts:
            return {**base, 'status': 'conflict', 'conflicts': [conflicts[key] for key in sorted(conflicts)]}
        return {**base, 'status': 'ok',
                'passages': [passage(snapshot, chunks[hit.chunk_id], hit.score, method) for hit in hits[:limit]]}
