"""Independent PostgreSQL lexical and exact-vector ranking primitives."""

from dataclasses import dataclass
import json
import math
from typing import Callable, Sequence

from ..ingestion.models import Chunk


class RetrievalUnavailable(RuntimeError):
    """Dependency failure, never an empty successful search."""


@dataclass(frozen=True)
class Hit:
    chunk_id: str
    score: float


class PostgresLexicalRanker:
    """Read-only full-text baseline over bounded, supplied section candidates.

    G1 supplies a connection/context manager configured with the request's remaining
    deadline and read-only role. No schema is created and no write statement is issued,
    and no SQL originates from a model. For this tiny corpus VALUES/unnest avoids
    coupling this component milestone to unallocated table names or migrations.
    """

    score_method = 'postgres-ts-rank-cd-english'
    _SQL = """
        WITH source AS (
            SELECT chunk_id, to_tsvector('english', body) AS document
            FROM unnest(%s::text[], %s::text[]) AS input(chunk_id, body)
        ), query AS (SELECT plainto_tsquery('english', %s) AS terms)
        SELECT chunk_id, ts_rank_cd(document, terms) AS score
        FROM source CROSS JOIN query WHERE document @@ terms
        ORDER BY score DESC, chunk_id ASC
    """

    def __init__(self, connection: Callable):
        self._connection = connection

    def rank(self, query: str, chunks: Sequence[Chunk]) -> tuple[Hit, ...]:
        if not chunks:
            return ()
        try:
            with self._connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(self._SQL, ([chunk.chunk_id for chunk in chunks],
                                              [chunk.title + '\n' + chunk.text for chunk in chunks], query))
                    return tuple(Hit(chunk_id, float(score)) for chunk_id, score in cursor.fetchall())
        except Exception as exc:
            raise RetrievalUnavailable('Lexical retrieval dependency unavailable') from exc


class PostgresVectorRanker:
    """Exact pgvector comparison over parameterized candidates; no ANN index."""

    score_method = 'pgvector-exact-cosine'
    _SQL = """
        WITH source AS (
            SELECT chunk_id, embedding::vector AS embedding
            FROM unnest(%s::text[], %s::text[]) AS input(chunk_id, embedding)
        ), scored AS (
            SELECT chunk_id, 1 - (embedding <=> %s::vector) AS score FROM source
        )
        SELECT chunk_id, score FROM scored WHERE score >= %s
        ORDER BY score DESC, chunk_id ASC
    """

    def __init__(self, connection: Callable):
        self._connection = connection

    def rank(self, query, vectors, chunks, minimum_similarity):
        # Validate the same numerical preconditions as the reference implementation.
        exact_cosine(query, vectors, chunks, minimum_similarity)
        if not chunks:
            return ()
        try:
            with self._connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(self._SQL, ([chunk.chunk_id for chunk in chunks],
                                              [json.dumps(list(vector), allow_nan=False) for vector in vectors],
                                              json.dumps(list(query), allow_nan=False), minimum_similarity))
                    return tuple(Hit(chunk_id, float(score)) for chunk_id, score in cursor.fetchall())
        except Exception as exc:
            raise RetrievalUnavailable('Vector retrieval dependency unavailable') from exc


def exact_cosine(query: Sequence[float], vectors: Sequence[Sequence[float]],
                 chunks: Sequence[Chunk], minimum_similarity: float) -> tuple[Hit, ...]:
    if not math.isfinite(minimum_similarity) or not -1 <= minimum_similarity <= 1:
        raise ValueError('A calibrated minimum similarity in [-1, 1] is required')
    if len(vectors) != len(chunks):
        raise ValueError('Vector/chunk count mismatch')
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in query):
        raise ValueError('Invalid query vector values')
    query_norm = math.hypot(*query)
    if query_norm == 0 or not math.isfinite(query_norm):
        raise ValueError('Invalid query vector norm')
    normalized = [value / query_norm for value in query]
    hits = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        if len(vector) != len(query):
            raise ValueError('Vector dimensions differ')
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in vector):
            raise ValueError('Invalid indexed vector values')
        norm = math.hypot(*vector)
        if norm == 0 or not math.isfinite(norm):
            raise ValueError('Invalid indexed vector norm')
        score = max(-1.0, min(1.0, math.fsum(a * (b / norm) for a, b in zip(normalized, vector))))
        if score >= minimum_similarity:
            hits.append(Hit(chunk.chunk_id, score))
    return tuple(sorted(hits, key=lambda hit: (-hit.score, hit.chunk_id)))
