---
name: warehouse-retrieval
description: Build section-preserving ingestion, retrieval, and source grounding over the project's fictional warehouse SOP corpus.
---

Author a small fictional Markdown SOP corpus with document/version/section IDs, effective dates, step order, glossary terms, and explicit stop/escalation instructions. Label it as demonstration material. Avoid pretending it is an employer's procedure or certified operational guidance.

Chunk around headings and steps, keeping warnings attached to the affected steps. Store enough source metadata to recover the exact cited original. Re-ingestion is idempotent. Superseded versions are excluded by default; conflicts are surfaced.

Use PostgreSQL lexical retrieval as a baseline and pgvector embeddings for comparison. Keep provider/model/dimension and chunker versions with index metadata; a model change may require re-indexing. Start with exact vector search for the small corpus. Do not add a reranker or approximate index without a measured need.

Test provenance, stable IDs, missing evidence, version selection, multi-step coverage, and instruction-like text inside documents. Coordinate the embedding interface with G1 and migrations with C1/coordinator. Propose reference cases without accessing G3's held-out set during tuning.
