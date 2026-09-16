# Shared contracts, v1

Coordinator decisions for implementation planning. Individual reports contain independent proposals; this document resolves differences and is authoritative for the first build. G1 will encode it in Pydantic/OpenAPI before other workers implement against it.

## Service boundaries

- `backend/app/api/`, `backend/app/assistant/`, `backend/app/providers/`, `backend/app/contracts/`: G1.
- `backend/app/retrieval/`, `backend/app/ingestion/`, `data/sops/`: G2.
- `backend/app/inventory/`, `data/inventory/`, inventory migrations: C1.
- `frontend/`: C2.
- `evals/`, `tests/evaluation/`: G3.
- `infra/`, `scripts/`, `.github/`, integration tests and delivery docs: C3.

G1 owns Python dependency declarations and the shared application bootstrap. C2 owns frontend dependencies. Inventory and retrieval migrations must use nonconflicting IDs and be sequenced by the coordinator. No worktree runs schema changes against another worktree's database.

G1 establishes the shared database session/bootstrap and Alembic environment. C1 owns the first inventory revision; G2's retrieval revision follows that exact revision. G2 can develop parsing/retrieval interfaces in parallel but rebases onto the merged inventory schema before final migration verification. C3 owns `infra/compose.yaml` and service Dockerfiles. Shared revision allocation stays in this document; duplicate migration heads are not accepted accidentally.

## HTTP boundary

- `POST /api/chat`: `{message, history?, selection?}`. Message length 1-4000 characters, at most eight prior user/assistant messages of 2000 characters each. No client-supplied system messages or tool results. History is untrusted context, never a source of fresh inventory facts.
- Optional `selection` contains a canonical `assembly_id` or `part_id`, and/or `procedure: {document_id, version, section_id}`. All IDs are resolved server-side; a selection never establishes permissions or current stock.
- Returns `{answer, answer_citation_ids, status, citations, procedure_result, inventory_result, clarification, error, trace_id, data_mode}`.
- `status`: `answered | needs_clarification | insufficient_evidence | temporarily_unavailable`.
- `data_mode`: `synthetic` always in this demo. Structured results, clarification, and error can be null. Never use data_mode to imply whether a model was actually called; execution mode is separate run metadata.
- `clarification`: `{kind: assembly|part|quantity|procedure, question, choices: [{id, label}]}`. Choices can be empty for a missing quantity. Include it only for `needs_clarification`.
- `error`: `{code, message, retryable}` without raw exceptions or secrets. Validation is HTTP 422; unavailable dependencies are 503; request deadline expiry is 504. Domain ambiguity or absent evidence returns HTTP 200 with the appropriate status. Exception handlers use the same response envelope where possible; no success payload is fabricated for infrastructure failures.
- `GET /api/sops/{document_id}/sections/{section_id}?version={version}` requires version and returns the exact original section plus `is_current`. Missing versions return 404; never substitute the latest text.
- `GET /api/assemblies?query={text}&limit={1..20}` returns canonical assembly IDs and labels. Orchestration uses the same catalog service for name resolution; no fourth model tool is needed.
- `GET /api/health` is process liveness. `GET /api/ready` identifies database/corpus readiness and provider configuration, without making paid model calls or claiming a configured key is valid.
- Nonstreaming first. Validate requests/responses with Pydantic. OpenAPI generates frontend types after the interface is frozen.

For combined questions, retain independently validated successful sections in their structured result fields. If any required part is unavailable, use `temporarily_unavailable`; otherwise unresolved required input uses `needs_clarification`, missing/conflicting evidence uses `insufficient_evidence`, and fully supported completion uses `answered`. The UI shows which part is incomplete. Do not discard a known stock result or invent an SOP answer to make the whole response look successful.

## Retrieval boundary

`search_procedures(query, limit=5)` accepts bounded query text (maximum 1000 characters) and a limit from 1 through 5. Selected source context is supplied server-side from validated request context. Return `{status, passages, conflicts, corpus_revision, retrieval_mode}` where status is `ok | no_evidence | conflict | unavailable`.

Each passage has `document_id, version, section_id, chunk_id, title, text, source_uri, score, score_method`, plus structured required steps, prerequisites, and warning/step relationships. Scores are ranking values, not confidence probabilities. Expand matched steps to the complete needed procedure context before generation.

`Citation` contains `citation_id, document_id, version, section_id, title, quoted_text, source_uri`. Citation IDs and internal URLs are assigned by the server from retrieved passages. Quoted text must be an exact source excerpt. Only current documents are eligible by default; selected historical text stays visibly historical. Conflicting current procedures produce `insufficient_evidence` rather than asking the user to choose between incompatible instructions. Use clarification only for an ambiguity the user can resolve, such as procedure scope.

`answer_citation_ids` and each procedure step's `citation_ids` reference those stable IDs explicitly. The UI must not guess links from array positions, arbitrary Markdown URLs, or model-produced HTML. `trace_id` is available as an error-support detail, not ordinary answer content. Versioned source responses include `document_id, version, section_id, title, text, source_uri, is_current`.

`procedure_result` contains its evidence state, source/version identity, ordered steps with stable IDs, mandatory warning blocks, and optional plain-language explanations. Required actions, quantities, sequence, and warnings come from validated source structures; the model adds explanations. If the draft fails preservation checks, fall back to original source steps and disclose the fallback. A deterministic check is not proof of semantic fidelity; G3 reviews actual answers.

Source document/version content is immutable. Changed content needs a new version. Re-ingestion of the same checksums is a no-op. A failed indexing run cannot replace the active corpus. Start with exact vector search for this small corpus; do not require ANN indexes or a reranker.

G1's embedding adapter returns ordered vectors and provider/model/dimension metadata. G2 stores generation, corpus, and chunker versions; validates vector count, dimensions, and finite values; and only compares vectors from the same generation. An embedding model change requires a completed compatible re-index.

## Inventory tools

`lookup_stock(part_query)` returns `ok | ambiguous | not_found | incomplete | unavailable` with matching canonical part IDs, nullable quantities, unit, and snapshot metadata. If a part was explicitly selected, resolve its canonical ID instead of repeating fuzzy matching.

`check_build_readiness(assembly_id, quantity)` accepts a selected canonical assembly ID and a positive integer quantity bounded at 10000 for the demo. Reject booleans, coercion from strings/floats, zero, and negative values. Returns a deterministic result containing requested units, readiness, per-component requirements/available/shortage, and data snapshot metadata. Clarify assembly identity before calling this function when a name is ambiguous.

For each known component: `required = per_assembly * quantity`; `shortage = max(required - available, 0)`. Available means seeded on-hand stock; reservations and unit conversions are excluded. Unknown availability/shortage is null, never zero. `ready=true` requires complete sufficient data; `ready=false` means at least one known shortage; otherwise incomplete data yields `ready=null`. An incomplete result with a known shortage retains `state=incomplete` and `ready=false` so missing components remain visible. Empty or invalid BOMs can never be ready. Reject duplicate component lines with a database uniqueness constraint.

`inventory_result` is a `kind: stock|build` discriminated union. Common fields are `state` and `snapshot: {snapshot_id, captured_at}`. Build fields include `assembly_id, requested_units, ready, components`; each component has `part_id, per_assembly, required, available, shortage`. Stock fields include canonical matches. All queries for one answer use a consistent snapshot. The initial seeded demo is immutable during runtime.

Normalize name/alias queries by trimming whitespace and case-folding. Exact canonical IDs take precedence. Ambiguous matches return candidate IDs/labels without choosing a stock quantity. Parts and assemblies have separate alias tables; BOM foreign keys reference parts only. Use a read-only repeatable-read transaction for multi-query calculations, and atomically publish seed data with its snapshot metadata. Runtime privileges cover every required inventory/retrieval table; seed/migration roles are separate.

Use typed arguments, parameterized SQL/ORM queries, and read-only runtime database credentials. Seeding/migrations use separate development credentials. There is no free-form SQL tool, component deduction, purchasing, or employer connection.

## Assistant boundary

One bounded tool-calling loop, strict three-tool allowlist, and validation before dispatch. Initial limits: three logical model calls, six tool calls, 30 seconds total, at most ten seconds per dependency attempt, and one transient retry per operation within the overall deadline. Failed attempts consume execution budgets. Disable implicit SDK retries and never retry malformed arguments. Tune limits only with measured evidence and corresponding tests.

Retrieval content is data, not instructions. Numerical displays derive from structured tool results. Chat history does not authorize tools. Model output references evidence IDs instead of inventing URLs or source metadata. Keep bounded internal traces linked to trace_id: calls, validated results, source identities, errors, dataset versions, and timing; never API keys.

## Evaluation boundary

Case fields: `id, group_id, split, category, input, answerable, expected_status, expected_http_status, expected_source_ids, expected_inventory, expected_clarification, mandatory_facts, mandatory_warnings, forbidden_actions, fixture_id, applicable_tiers, notes`. Source expectations include exact versions/sections; inventory expectations include snapshot identity. Failure cases support error injection into adapters, not real external disruption.

Keep paraphrases and sibling cases in the same split. Reference expected inventory values are independently specified, not generated by calling the function under test. Separate deterministic component checks, offline transport mocks, and live model runs. Store configuration, corpus/seed versions, commit, and failure records with each run; only live runs support claims about LLM behavior.
