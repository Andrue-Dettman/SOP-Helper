from dataclasses import replace

import pytest

from backend.app.ingestion.catalog import (EmbeddingBatch, Generation, MemoryCatalog,
                                           PublicationConflict, ingest, validate_vectors)
from backend.app.ingestion.models import SourceValidationError
from backend.app.retrieval.service import ProcedureService

GENERATION = Generation('fixture-generation-1', 'offline-fixture', 'fixture-vectors', 2)


class FixtureEmbedder:
    """Handwritten offline vectors, not evidence of embedding-provider quality."""

    def __init__(self, generation=GENERATION):
        self.generation = generation
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        return EmbeddingBatch(self.generation, [(1.0, 0.0) if 'delivery' in text.lower() else (0.0, 1.0)
                                                for text in texts])


@pytest.mark.parametrize('vectors', [[], [[1.0]], [[True, 1.0]], [[float('nan'), 1.0]],
                                    [[float('inf'), 1.0]], [[0.0, 0.0]], [[10**1000, 1.0]]])
def test_malformed_embedding_batches_are_rejected(vectors):
    with pytest.raises(SourceValidationError):
        validate_vectors(EmbeddingBatch(GENERATION, vectors), GENERATION, 1)


def test_query_generation_mismatch_is_unavailable(corpus):
    catalog = MemoryCatalog()
    ingest(corpus, catalog, generation=GENERATION, embedder=FixtureEmbedder())
    other = replace(GENERATION, generation_id='fixture-generation-2')
    service = ProcedureService(catalog, mode='embedding', embedder=FixtureEmbedder(other), minimum_similarity=0.9)
    assert service.search_procedures('delivery')['status'] == 'unavailable'


def test_embedding_reindex_and_failed_batch_are_atomic(corpus):
    catalog, embedder = MemoryCatalog(), FixtureEmbedder()
    first = ingest(corpus, catalog, generation=GENERATION, embedder=embedder)
    assert ingest(corpus, catalog, generation=GENERATION, embedder=embedder) is first
    assert embedder.calls == 1
    other = replace(GENERATION, model='another-fixture-model', generation_id='fixture-generation-2')
    with pytest.raises(SourceValidationError, match='generation mismatch'):
        ingest(corpus, catalog, generation=other, embedder=embedder)
    assert catalog.snapshot() is first
    second = ingest(corpus, catalog, generation=other, embedder=FixtureEmbedder(other))
    assert first.revision != second.revision
    assert catalog.snapshot().generation == other


def test_failed_provider_leaves_previous_corpus_active(corpus):
    catalog = MemoryCatalog()
    first = ingest(corpus, catalog)

    class Broken:
        def embed(self, texts):
            raise TimeoutError('injected test failure')

    with pytest.raises(TimeoutError):
        ingest(corpus, catalog, generation=GENERATION, embedder=Broken())
    assert catalog.snapshot() is first


def test_stale_publication_cannot_replace_a_newer_revision(corpus):
    catalog = MemoryCatalog()
    first = ingest(corpus, catalog)
    second = ingest(corpus, catalog, generation=GENERATION, embedder=FixtureEmbedder())
    with pytest.raises(PublicationConflict):
        catalog.publish(first, expected_revision=None)
    assert catalog.snapshot() is second


def test_exact_embedding_search_expands_all_steps_and_warnings(corpus):
    catalog, embedder = MemoryCatalog(), FixtureEmbedder()
    ingest(corpus, catalog, generation=GENERATION, embedder=embedder)
    service = ProcedureService(catalog, mode='embedding', embedder=embedder, minimum_similarity=0.99)
    result = service.search_procedures('delivery', limit=1)
    assert result['status'] == 'ok'
    item = result['passages'][0]
    assert item['score_method'] == 'exact-cosine'
    assert len(item['required_steps']) == 4
    assert len(item['warnings']) == 1
    assert len(item['prerequisites']) == 1
    assert item['is_current'] is True


def test_vector_neighbors_below_threshold_are_not_evidence(corpus):
    catalog = MemoryCatalog()
    ingest(corpus, catalog, generation=GENERATION, embedder=FixtureEmbedder())

    class Unrelated:
        def embed(self, texts):
            return EmbeddingBatch(GENERATION, [(-1.0, -1.0)])

    service = ProcedureService(catalog, mode='embedding', embedder=Unrelated(), minimum_similarity=0.9)
    assert service.search_procedures('unrelated')['status'] == 'no_evidence'
