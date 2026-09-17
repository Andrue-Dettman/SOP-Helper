from contextlib import contextmanager
import json

import pytest

from backend.app.ingestion.catalog import ingest
from backend.app.retrieval.ranking import Hit, PostgresLexicalRanker, PostgresVectorRanker, RetrievalUnavailable
from backend.app.retrieval.service import ProcedureService, Selection


class ScriptedRanker:
    """Transport/component fixture; deliberately makes no lexical quality claim."""
    score_method = 'offline-scripted-ranking'

    def rank(self, query, chunks):
        return tuple(Hit(chunk.chunk_id, 1.0) for chunk in chunks
                     if chunk.document_id == 'receiving-delivery' and chunk.section_id == 'inspect-and-count')


def add_conflict(corpus):
    path = corpus / 'manifest.json'
    manifest = json.loads(path.read_text())
    # A competing current document for the same procedure/scope, with no supersession.
    source = (corpus / 'receiving-delivery/v1.md').read_bytes()
    (corpus / 'conflict.md').write_bytes(source.replace(b'"document_id": "receiving-delivery"',
                                                       b'"document_id": "receiving-conflict"'))
    manifest['documents'].append({'path': 'conflict.md', 'current': True})
    path.write_text(json.dumps(manifest))


def test_warning_and_prerequisite_citations_resolve_to_exact_source(catalog):
    service = ProcedureService(catalog, mode='lexical', lexical=ScriptedRanker())
    result = service.search_procedures('receive a delivery', limit=1)
    assert result['status'] == 'ok'
    item = result['passages'][0]
    assert item['version'] == '2'
    assert [step['id'] for step in item['required_steps']] == ['receive-01', 'receive-02', 'receive-03', 'receive-04']
    assert item['warnings'][0]['text'] == 'If a package is leaking or visibly damaged, stop. Do not open or move it. Contact the demo supervisor.'
    assert item['warnings'][0]['applies_to'] == ['receive-02']
    citation_ids = {citation['citation_id'] for citation in item['citations']}
    for block in item['required_steps'] + item['warnings'] + item['prerequisites']:
        assert set(block['citation_ids']) <= citation_ids
    for citation in item['citations']:
        section = service.get_section(citation['document_id'], citation['section_id'], version=citation['version'])
        assert citation['quoted_text'] in section['text']
        assert citation['source_uri'] == section['source_uri']
    assert service.search_procedures('another phrasing', limit=1)['passages'][0]['citations'] == item['citations']


@pytest.mark.parametrize(('query', 'limit'), [('', 5), ('  ', 5), ('x' * 1001, 5), (123, 5),
                                            ('x', 0), ('x', 6), ('x', True), ('x', 1.0), ('x', '1')])
def test_bounds_rejected_before_dependency_call(catalog, query, limit):
    service = ProcedureService(catalog, mode='lexical', lexical=object())
    with pytest.raises(ValueError):
        service.search_procedures(query, limit)


def test_conflict_not_hidden_by_limit_or_missing_competitor_hit(corpus, catalog):
    add_conflict(corpus)
    ingest(corpus, catalog)
    service = ProcedureService(catalog, mode='lexical', lexical=ScriptedRanker())
    result = service.search_procedures('receive', limit=1)
    assert result['status'] == 'conflict'
    assert result['passages'] == []
    assert len(result['conflicts'][0]['sources']) == 2
    selected = service.search_procedures('explain', selection=Selection('receiving-delivery', '2', 'inspect-and-count'))
    assert selected['status'] == 'conflict'
    historical = service.search_procedures('explain', selection=Selection('receiving-delivery', '1', 'inspect-and-count'))
    assert historical['status'] == 'ok'


def test_request_pins_revision_during_concurrent_publication(corpus, catalog):
    original_revision = catalog.snapshot().revision

    class PublishingRanker(ScriptedRanker):
        def rank(self, query, chunks):
            add_conflict(corpus)
            ingest(corpus, catalog)
            return super().rank(query, chunks)

    result = ProcedureService(catalog, mode='lexical', lexical=PublishingRanker()).search_procedures('receive')
    assert result['status'] == 'ok'
    assert result['corpus_revision'] == original_revision
    assert catalog.snapshot().revision != original_revision


def test_unavailable_is_distinct_from_no_evidence(catalog):
    class Empty(ScriptedRanker):
        def rank(self, query, chunks):
            return ()

    class Broken(ScriptedRanker):
        def rank(self, query, chunks):
            raise RetrievalUnavailable('injected adapter failure')

    assert ProcedureService(catalog, mode='lexical', lexical=Empty()).search_procedures('unrelated')['status'] == 'no_evidence'
    failed = ProcedureService(catalog, mode='lexical', lexical=Broken()).search_procedures('receive')
    assert failed['status'] == 'unavailable'
    assert failed['passages'] == []
    assert 'injected adapter failure' not in repr(failed)


def test_unknown_selection_does_not_substitute_current_text(catalog):
    service = ProcedureService(catalog, mode='lexical', lexical=ScriptedRanker())
    result = service.search_procedures('receive', selection=Selection('receiving-delivery', 'missing', 'inspect-and-count'))
    assert result['status'] == 'no_evidence'
    assert result['passages'] == []


class FakeCursor:
    def __init__(self, rows=()):
        self.rows = rows
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        self.calls.append((sql, params))

    def fetchall(self):
        return self.rows


@contextmanager
def fake_connection(cursor):
    class Connection:
        def cursor(self):
            return cursor
    yield Connection()


def test_postgres_lexical_query_uses_bound_parameters(catalog):
    chunks = catalog.snapshot().chunks[:1]
    cursor = FakeCursor([(chunks[0].chunk_id, 0.5)])
    ranker = PostgresLexicalRanker(lambda: fake_connection(cursor))
    query = "delivery'); DROP TABLE source; --"
    assert ranker.rank(query, chunks) == (Hit(chunks[0].chunk_id, 0.5),)
    sql, parameters = cursor.calls[0]
    assert query not in sql
    assert parameters[2] == query
    assert parameters[1][0].endswith(chunks[0].text)


def test_postgres_vector_query_binds_vectors_and_threshold(catalog):
    chunks = catalog.snapshot().chunks[:1]
    cursor = FakeCursor([(chunks[0].chunk_id, 1.0)])
    ranker = PostgresVectorRanker(lambda: fake_connection(cursor))
    assert ranker.rank((1.0, 0.0), [(1.0, 0.0)], chunks, 0.9)[0].score == 1.0
    sql, params = cursor.calls[0]
    assert '<=>' in sql
    assert params[1] == ['[1.0, 0.0]']
    assert params[2:] == ('[1.0, 0.0]', 0.9)


def test_database_failure_is_normalized(catalog):
    def broken():
        raise ConnectionError('injected secret-like error detail')
    with pytest.raises(RetrievalUnavailable, match='dependency unavailable'):
        PostgresLexicalRanker(broken).rank('receive', catalog.snapshot().chunks)
