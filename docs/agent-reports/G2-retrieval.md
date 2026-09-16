# G2 Retrieval Implementation Plan

Planning only. This report applies `.agents/skills/warehouse-retrieval/SKILL.md`; no application behavior is implemented. All procedures and operational details below are fictional demonstration material.

## Decisions and Corpus

Start with eight Markdown SOPs: receiving deliveries, damaged deliveries, labeling stock, putting stock away, counting stock, picking assembly parts, reporting shortages, and packing completed assemblies. Include glossary sections within these documents. Markdown is canonical; defer PDF ingestion. Provide one superseded receiving version and a separate conflict fixture excluded from normal demo seeding.

Each document declares `document_id`, `version`, `title`, `effective_date`, `status`, `procedure_key`, `scope`, `supersedes`, and `data_mode=synthetic`. Version identifiers are opaque, never lexically sorted to choose the current version. Each section has an explicit stable `section_id`; ordered steps and warnings have stable IDs. Record a source checksum, corpus revision, and chunker version during ingestion. An existing document/version cannot acquire different content: edits require a new version.

Concrete fixture: `receiving-delivery`, version `2`, effective `2026-09-01`, section `inspect-and-count`, scope `demo-warehouse`, procedure key `delivery-receipt`. Its original passage contains:

1. `receive-01`: Match the delivery reference to the sample delivery note.
2. `receive-02`: Inspect the packages before opening them.
3. `receive-03`: Count each item in whole units and compare with the delivery note.
4. `receive-04`: Record accepted quantities and report differences to the demo supervisor.

Warning `receive-stop-01`, attached to step two: "If a package is leaking or visibly damaged, stop. Do not open or move it. Contact the demo supervisor." Glossary entry `delivery-note` defines the accompanying item list. Version one remains available through exact lookup but is excluded from default search. A conflict fixture declares another current version for the same procedure and scope; ingestion must expose this ambiguity, never silently choose a winner.

## Chunking and Ingestion

Parse Markdown with a maintained parser selected with G1. Use sections as retrieval units, preserving heading ancestry, original Markdown, ordered steps, glossary terms, and warning relationships. Split unusually long sections only between complete steps. Replicate applicable section-wide warnings and prerequisites in each child chunk; never truncate a step or safety block to meet an embedding limit. Reject oversized indivisible blocks with an actionable ingest error. Derive chunk IDs from document/version/section, step range, and chunker version.

Validate IDs, metadata, warning references, version relationships, and source size before indexing. Stage source rows and embeddings, then publish a complete corpus revision transactionally. Repeating ingestion with identical checksums is a no-op; failed runs leave the previous revision searchable. Serialize publication to prevent competing seeds. Runtime source access uses database records and server-generated URLs, never model-supplied filesystem paths.

Request coordinator-allocated migrations for document versions, sections, chunks, embedding generations, and the active corpus revision. Enforce unique immutable source keys, foreign keys, and embedding-generation membership. Store original sections separately from normalized search text. Keep conflicting current declarations so search can report them. Detect conflicts from the current-document registry before ranking, since top-k results alone can hide a competing version.

## Retrieval and Contract Changes

Implement PostgreSQL full-text retrieval first, followed by pgvector exact vector search as a separately selectable comparison. Use English lexical configuration, parameterized queries, deterministic tie-breaking, and bounded limits. Exact ID lookup bypasses semantic ranking. Embedding comparisons must share one provider/model/dimension generation; model changes require a completed reindex before activation.

Propose these shared-contract changes through G1/coordinator:

- Require `version` on `GET /api/sops/{document_id}/sections/{section_id}` as a query parameter. Return original Markdown and immutable source identity; missing versions return 404, never the latest replacement.
- Extend search arguments with optional canonical document/section context for selected-procedure explanations and an internal retrieval mode. Historical context requires an explicit version and remains visibly historical.
- Return `{status, passages, conflicts, corpus_revision, retrieval_mode}` with statuses `ok`, `no_evidence`, `conflict`, and `unavailable`. Map conflict to chat `needs_clarification`, absent evidence to `insufficient_evidence`, and operational failure to `temporarily_unavailable`.
- Add `chunk_id`, `step_ids`, structured `required_steps`, `warnings`, `prerequisites`, and score method to passages. Scores are ranking values, not probabilities. Expand matched steps to their complete procedural context before answering.
- Agree an embedding batch interface returning ordered vectors plus provider, model, dimension, and generation metadata. Validate vector count, dimensions, and finite values; specify timeouts and typed failures. G1 owns provider adapters and dependencies.

Mandatory steps and warnings travel as structured evidence. G1 should render required procedural content deterministically, retaining original quantities, order, and stop/escalation wording, with model explanations as supplemental text. Validate citation identity and quoted substrings against immutable source sections. Similarity alone cannot establish answerability.

## Ordered Delivery, Checks, and Risks

1. Freeze contracts with G1, source rendering with C2, and migration ordering with C1/coordinator.
2. Author fixtures; implement validation, transactional ingestion, and exact source lookup.
3. Deliver lexical search, then embedding search and explicit provider-failure behavior.
4. Supply G3 development scenarios and configuration metadata; integrate through C3's isolated demo database workflow.

Future edits stay within `backend/app/retrieval/`, `backend/app/ingestion/`, `data/sops/`, `tests/retrieval/`, and allocated migrations. Proposed tests cover idempotence, rollback, immutable citations, superseded exclusion, conflicts outside top-k, warning attachment, multi-step coverage, malformed embeddings, absent evidence, and instruction-like malicious source text. G3 independently owns held-out labels; tuning uses development cases only.

Compare retrieval recall, citation accuracy, procedural coverage, latency, and cost. Consider hybrid search only for demonstrated complementary lexical/embedding misses; reranking requires relevant candidates already present but misordered. Recheck frozen choices independently before claiming improvement. Main risks are incomplete context, ambiguous versions, and model omission. No tests, installations, or external research were performed during this planning pass.
