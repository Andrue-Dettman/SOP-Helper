"""Atomic in-process corpus catalog for component development.

This is an explicit reference store, not production persistence. The coordinator
must supply the database bootstrap and migration predecessor before SQL storage.
"""

from dataclasses import dataclass
import json
import math
from pathlib import Path
from threading import RLock
from typing import Protocol, Sequence

from .models import Chunk, Document, SourceValidationError, stable_id
from .parser import CHUNKER_VERSION, chunk_document, parse_document, strict_json


@dataclass(frozen=True)
class Generation:
    generation_id: str
    provider: str
    model: str
    dimension: int

    def __post_init__(self):
        if any(not isinstance(value, str) or not value.strip()
               for value in (self.generation_id, self.provider, self.model)):
            raise SourceValidationError('Embedding metadata must be nonempty strings')
        if type(self.dimension) is not int or not 1 <= self.dimension <= 16_000:
            raise SourceValidationError('Invalid embedding dimension')


@dataclass(frozen=True)
class EmbeddingBatch:
    generation: Generation
    vectors: Sequence[Sequence[float]]


class Embedder(Protocol):
    def embed(self, texts: Sequence[str]) -> EmbeddingBatch: ...


def validate_vectors(batch: EmbeddingBatch, generation: Generation, count: int) -> tuple[tuple[float, ...], ...]:
    if batch.generation != generation:
        raise SourceValidationError('Embedding generation mismatch')
    if len(batch.vectors) != count:
        raise SourceValidationError('Embedding count mismatch')
    result = []
    for vector in batch.vectors:
        if len(vector) != generation.dimension:
            raise SourceValidationError('Embedding dimension mismatch')
        if any(type(value) not in (int, float) for value in vector):
            raise SourceValidationError('Embedding values must be finite numbers')
        try:
            converted = tuple(float(value) for value in vector)
        except (OverflowError, ValueError) as exc:
            raise SourceValidationError('Embedding values must be finite numbers') from exc
        if not all(math.isfinite(value) for value in converted):
            raise SourceValidationError('Embedding values must be finite numbers')
        norm = math.hypot(*converted)
        if not math.isfinite(norm) or norm == 0:
            raise SourceValidationError('Embedding norm must be finite and nonzero')
        result.append(converted)
    return tuple(result)


@dataclass(frozen=True)
class Snapshot:
    revision: str
    documents: tuple[Document, ...]
    current: frozenset[tuple[str, str]]
    chunks: tuple[Chunk, ...]
    generation: Generation | None
    vectors: tuple[tuple[float, ...], ...]
    chunker_version: str = CHUNKER_VERSION


class PublicationConflict(RuntimeError):
    pass


class MemoryCatalog:
    """Opt-in test/development adapter; never installed as an application default."""

    def __init__(self):
        self._lock = RLock()
        self._active: Snapshot | None = None
        self._archive: dict[tuple[str, str], Document] = {}

    def snapshot(self) -> Snapshot | None:
        with self._lock:
            return self._active

    def source(self, key: tuple[str, str]) -> tuple[Document, bool]:
        with self._lock:
            document = self._archive[key]
            return document, bool(self._active and key in self._active.current)

    def validate_immutability(self, documents: tuple[Document, ...]):
        with self._lock:
            for document in documents:
                previous = self._archive.get(document.key)
                if previous and previous.checksum != document.checksum:
                    raise SourceValidationError('Existing document/version content is immutable')

    def publish(self, snapshot: Snapshot, expected_revision: str | None) -> Snapshot:
        with self._lock:
            self.validate_immutability(snapshot.documents)
            if self._active and self._active.revision == snapshot.revision:
                return self._active
            actual = self._active.revision if self._active else None
            if actual != expected_revision:
                raise PublicationConflict('Corpus changed while indexing; retry from current revision')
            self._archive.update((document.key, document) for document in snapshot.documents)
            self._active = snapshot
            return snapshot


def _validate_supersession(documents: tuple[Document, ...]):
    by_key = {document.key: document for document in documents}
    visiting, complete = set(), set()

    def visit(key):
        if key in visiting:
            raise SourceValidationError('Supersession cycle')
        if key in complete:
            return
        if key not in by_key:
            raise SourceValidationError('Missing superseded version in corpus manifest')
        visiting.add(key)
        for version in by_key[key].supersedes:
            visit((key[0], version))
        visiting.remove(key)
        complete.add(key)

    for key in by_key:
        visit(key)


def ingest(root: Path, catalog: MemoryCatalog, *, generation: Generation | None = None,
           embedder: Embedder | None = None) -> Snapshot:
    if (generation is None) != (embedder is None):
        raise SourceValidationError('Embedding generation and adapter must be supplied together')
    root = root.resolve(strict=True)
    manifest = strict_json((root / 'manifest.json').read_text(encoding='utf-8'))
    if (not isinstance(manifest, dict) or set(manifest) != {'schema_version', 'documents'}
            or type(manifest['schema_version']) is not int or manifest['schema_version'] != 1):
        raise SourceValidationError('Unsupported corpus manifest')
    entries = manifest['documents']
    if not isinstance(entries, list) or not 1 <= len(entries) <= 40:
        raise SourceValidationError('Manifest must contain 1–40 document versions')
    documents, current, paths = [], set(), set()
    for entry in entries:
        if (not isinstance(entry, dict) or set(entry) != {'path', 'current'}
                or not isinstance(entry['path'], str) or type(entry['current']) is not bool):
            raise SourceValidationError('Invalid manifest entry')
        candidate = (root / entry['path']).resolve(strict=True)
        if not candidate.is_relative_to(root) or candidate.suffix != '.md' or candidate in paths:
            raise SourceValidationError('Source paths must be unique Markdown files inside the corpus')
        paths.add(candidate)
        document = parse_document(candidate.read_bytes())
        documents.append(document)
        if entry['current']:
            current.add(document.key)
    documents = tuple(sorted(documents, key=lambda item: item.key))
    if len({document.key for document in documents}) != len(documents):
        raise SourceValidationError('Duplicate document/version')
    if not current:
        raise SourceValidationError('Corpus must contain a current procedure')
    _validate_supersession(documents)
    catalog.validate_immutability(documents)
    chunks = tuple(chunk for document in documents for chunk in chunk_document(document))
    config = None if generation is None else (generation.generation_id, generation.provider,
                                              generation.model, generation.dimension)
    revision = stable_id(json.dumps([(d.key, d.checksum) for d in documents]),
                         json.dumps(sorted(current)), CHUNKER_VERSION, json.dumps(config))
    previous = catalog.snapshot()
    if previous and previous.revision == revision:
        return previous
    vectors = ()
    if generation is not None:
        vectors = validate_vectors(embedder.embed([chunk.title + '\n' + chunk.text for chunk in chunks]),
                                   generation, len(chunks))
    staged = Snapshot(revision, documents, frozenset(current), chunks, generation, vectors)
    return catalog.publish(staged, previous.revision if previous else None)
