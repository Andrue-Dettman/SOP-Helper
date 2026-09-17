# G2 component handoff

Implemented in G2's assigned worktree after the user's implementation go-ahead. The user subsequently authorized committing the implementation for other workers. This is a tested component milestone, not a running integrated application. The earlier planning report is excluded from the implementation commit.

## Available components

- `backend/app/ingestion/parser.py`: strict fictional-source metadata, CommonMark section extraction, original source offsets, required-step and warning validation, stable section chunks.
- `backend/app/ingestion/catalog.py`: explicit in-process reference catalog with immutable version history, atomic publication, idempotence, stale-publication protection, supersession validation, and embedding-generation checks. It does not persist across process restarts.
- `backend/app/retrieval/service.py`: bounded search, server-supplied selection context, exact version lookup, request-pinned source revision, complete procedural context, exact excerpt citations, historical flags, and conflicts checked before result limiting.
- `backend/app/retrieval/ranking.py`: PostgreSQL English full-text and pgvector exact cosine adapters using bound parameters. Candidate sections are passed through `unnest`; this small-corpus implementation does not require unapproved database table names. An in-process exact cosine function is available for component tests and comparison.
- `data/sops/`: eight current fictional procedures and one historical version, with 27 sections.
- `tests/retrieval/`: offline component and mocked database-transport checks.

Public response schemas, HTTP routes, provider adapters, dependency manifests, database bootstrap, and migration files have not been modified. Internal dataclasses and dictionaries need G1's mapping to the frozen Pydantic contract; they are not a replacement for it. No model or external inventory calls occur here.

## Run the component checks

From the G2 worktree in PowerShell:

```powershell
python -m venv tests/retrieval/.venv
& tests/retrieval/.venv/Scripts/python.exe -m pip install markdown-it-py==4.2.0 pytest==9.1.1
& tests/retrieval/.venv/Scripts/python.exe -m pytest tests/retrieval --basetemp tests/retrieval/.venv/pytest-tmp -q
```

The existing local environment is under the ignored `tests/retrieval/.venv/`; no global Python packages were installed. The versions above were actually installed and exercised on Python 3.12. G1 should review and declare compatible shared dependency pins. The parser uses the documented [markdown-it-py token stream and source maps](https://markdown-it-py.readthedocs.io/en/latest/using.html).

First verification: **52 passed**. Checks cover malformed metadata and source structure, exact LF/CRLF text, step/warning relationships, historical lookup, archived selection, idempotence, failed-index rollback, stale publication, embedding validation and generation changes, query bounds, conflict detection outside top-k, request consistency, no-evidence versus dependency failure, and bound SQL parameters. Database adapters use fake connections in these checks. Fixture vectors and scripted rankings do not establish semantic retrieval quality or LLM robustness.

## Integration prerequisites and ownership

1. G1 supplies the shared session and provider interfaces. The embedding adapter must return ordered vectors with `Generation`-compatible metadata and normalize provider failures to `RetrievalUnavailable`, `TimeoutError`, or `ConnectionError`. Malformed vector batches become unavailable during search. Pass the remaining request deadline through the provider/connection adapters; these modules add no retry loop.
2. G1 maps `Selection` from validated request context. Only query and limit belong to the model tool schema. Unknown exact section/version raises `KeyError` for HTTP 404; invalid search arguments raise `ValueError` for request/tool validation. Map retrieval `conflict` to chat `insufficient_evidence` and `unavailable` to `temporarily_unavailable`. Resolve procedure-scope ambiguity at the orchestration boundary.
3. G1 maps `required_steps`, `warnings`, `prerequisites`, and their citation IDs into `procedure_result`. Preserve order, quantities, applicable warnings, and cross-section citations; implement explanation validation and original-source fallback in the assistant layer. The retrieval layer does not claim to validate generated prose.
4. G1/C3 provide a read-only PostgreSQL connection context with bounded statement/request deadlines, and verify pgvector is enabled in the isolated demo database. Supply `PostgresLexicalRanker` for lexical mode and `PostgresVectorRanker` for the database embedding comparison. The in-process vector reference has score method `exact-cosine`; database comparison reports `pgvector-exact-cosine`. Neither score is a confidence probability. Embedding mode requires an explicit acceptance threshold; none is advertised as calibrated.
5. C1/coordinator must supply the actual inventory revision and allocate G2's successor before persistent retrieval migrations can be implemented. No revision ID was invented and no schema was applied. A persistent catalog adapter remains outstanding; `MemoryCatalog` is opt-in and must not silently replace failed database storage.
6. G3 independently supplies development cases for relevance/threshold tuning and owns held-out evaluation. No held-out labels were read. No hybrid ranker, ANN index, or reranker was added.

Remaining verification: real PostgreSQL/pgvector execution and parity, persistence and migration lifecycle, API/type integration, provider failure/deadline integration, live embeddings, generated-answer preservation, and independent retrieval evaluation. Metadata detects declared conflicts; it cannot prove arbitrary semantic consistency across authored procedures. Corpus authors and G3 must review that limitation.

G1's async contract/provider files and C1's `c1_0001_inventory_schema` migration are now available in their worktrees. G2's next increment will map complete source sections to G1's strict `Passage` schema and add persistent database storage. Other workers can use the corpus and source parser immediately. A retrieval migration revision still needs coordinator allocation.

The worktree's `git status` now succeeds. New implementation files are confined to G2's scope. No repository metadata repair, branch change, service provisioning, or deployment was attempted. The earlier planning report remains a separate uncommitted planning artifact.
