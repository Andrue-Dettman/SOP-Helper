# G1 API and Orchestration Plan

Planning only; no application changes, dependency installation, external research, or runtime tests performed. This proposal follows AGENTS.md, PROJECT_BRIEF.md, CONTRACTS.md v0, and the warehouse-api skill. All contract changes require coordinator consolidation before implementation.

## Decisions and Proposed Contracts

Use nonstreaming FastAPI endpoints, strict Pydantic models, and one bounded assistant workflow. Separate transport validation, provider adapters, orchestration, and domain interfaces. Reject unknown fields and coercion of strings, floats, or booleans into integer quantities. Keep credentials server-side; runtime database access is read-only.

`POST /api/chat` request:

- `message: str` (trimmed, 1-4000 characters).
- `history: list[{role: user|assistant, content: str}] = []` (maximum eight messages, 2000 characters each); no client system messages or tool results.
- `selection: {assembly_id: str|null, procedure: {document_id: str, version: str, section_id: str}|null}|null = null` supplies explicit UI context. Resolve every supplied identifier server-side; selections do not establish stock facts.

Response retains v0 fields: `answer: str`, `status`, `citations: list[Citation]`, `inventory_result: InventoryResult|null`, `clarification: Clarification|null`, `trace_id: UUID`, and literal `data_mode: synthetic`. Add `error: {code: str, message: str, retryable: bool}|null`. Keep the four existing statuses. Clarification is `{kind: assembly|part|quantity|procedure, question: str, choices: list[{id: str, label: str}]}`; choices may be empty for missing quantities. Require clarification exactly when status is `needs_clarification`. Domain insufficiency and ambiguity return HTTP 200; malformed requests return 422, provider/database unavailability 503, deadline expiry 504, and unexpected failures 500. Use this envelope consistently through exception handlers; infrastructure failures use `temporarily_unavailable`. Errors disclose no credentials or raw exceptions.

`Citation` adds `citation_id: str` to v0 fields. The server constructs citations from retrieved evidence and checks `quoted_text` is a literal contiguous excerpt. Change source lookup to `GET /api/sops/{document_id}/sections/{section_id}?version={version}` with required version, returning `{document_id, version, section_id, title, text, source_uri, is_current}`. Missing versions return 404, never silently substitute current content. Generate internal links server-side. Inventory evidence lives in `inventory_result.snapshot`, not a fabricated SOP citation.

Define `InventoryResult` as a discriminated union using `kind: stock|build`. Both variants include `state: ok|ambiguous|not_found|incomplete|unavailable` and `snapshot: {snapshot_id: str, captured_at: UTC datetime}|null`. Stock includes `matches: list[{part_id, label, available: int|null, unit: unit}]`. Build includes `assembly_id`, `requested_units: positive int`, `ready: bool|null`, and `components: list[{part_id, per_assembly: positive int, required: int, available: int|null, shortage: int|null}]`. Missing availability produces null shortage and `ready=null`; known shortages produce `ready=false`, even when other components are unknown. Empty BOMs produce `incomplete` and never readiness. C1 must confirm whether `available` means seeded on-hand stock; reservations are excluded. Successful calculations require one consistent snapshot.

V0 lacks assembly discovery. Add `GET /api/assemblies?query={text}&limit={1..20}` returning `{items: [{assembly_id, label}]}`. For conversational names, return clarification with matching choices through this same catalog service; avoid adding another model tool. `GET /api/health` reports process liveness; add `/api/ready` for database, corpus, and provider-configuration readiness without paid model calls or secret exposure.

## Provider and Execution Design

Define async `ChatProvider.complete(messages, tool_schemas, response_schema, timeout_s) -> ProviderTurn`, containing typed tool calls or a structured draft plus usage metadata. Define `EmbeddingProvider.embed(texts, timeout_s) -> EmbeddingBatch`, containing vectors, provider/model identifiers, dimension, and usage. Validate vector count, dimensions, and finite values. G2 owns batching, indexing, retrieval strategy, and embedding compatibility checks; adapters own transport. Inject deterministic fakes for offline tests. Verify official provider documentation during implementation before selecting models or pinning dependencies.

Allow only `search_procedures(query, limit=5)`, `lookup_stock(part_query)`, and `check_build_readiness(assembly_id, quantity)`. Bound query length to 1000 characters and retrieval limit to 1-5. Validate IDs and arguments before dispatch. Permit three logical model calls, six total tool calls, a 30-second request deadline, and one transient retry per dependency operation within that deadline. Charge failed attempts against execution budgets; cap each attempt at ten seconds and do not retry invalid arguments. Disable implicit SDK retries. Execute calls sequentially and cancel outstanding work on expiry. Never answer unfinished reasoning as success.

Drafts reference server-issued evidence IDs. Reject invented citations and unsupported inventory claims; server-render quantities from validated results. Conflicting current procedures return `insufficient_evidence`. Required steps, warnings, quantities, and escalation instructions must survive simplification; failed preservation checks fall back to original passages. Citation validation alone cannot prove semantic fidelity, so retain human evaluation. Treat history and retrieved instruction-like text as untrusted data.

## Ordered Delivery and Acceptance

1. Freeze schemas and error codes with C2/G3; implement contracts, exception mapping, and generated OpenAPI types.
2. Agree catalog/snapshot semantics with C1 and immutable sections/conflict signals with G2; integrate injected service interfaces.
3. Implement providers, bounded orchestration, evidence validation, and bootstrap configuration.
4. Test malformed inputs, coercion rejection, unknown tools, ambiguous IDs, missing stock, empty BOMs, exact-version links, invented citations, warning preservation, hostile history/documents, retries, cancellation, and exhausted budgets. Assert no invalid tool reaches domain execution.
5. Hand G3 deterministic fixtures and trace/error metadata; distinguish offline transport tests from live model evaluation. Hand C2 clarification choices, nullable inventory states, citations, and retry behavior. Coordinate configuration and dependency compatibility with C3.

Future ownership: backend/app/api/, assistant/, providers/, contracts/, main.py, backend Python dependency declarations, and tests/api/. Principal risks are semantic omissions, inconsistent inventory snapshots, and provider-specific schema support; resolve through evidence fallback, snapshot contracts, and adapter tests.
