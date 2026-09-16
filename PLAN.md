# Warehouse Procedure & Inventory Assistant: implementation plan

## Outcome

Build a standalone portfolio application that answers questions about fictional warehouse procedures and seeded inventory. It should demonstrate retrieval-augmented generation, embeddings, LLM function calling, deterministic database calculations, and reproducible evaluation. It does not connect to Northern Valley Industries or claim business savings, production adoption, or validated accessibility outcomes.

This plan uses three OpenAI/Codex workers and three Claude Code workers, each with its own Git branch, worktree, assignment, and project skill. The coordinator owns integration. These are development agents; the application itself has one bounded assistant workflow.

## What the user can do

1. Ask "How do I receive a delivery?" and get short ordered steps with links to the relevant sample SOP passages.
2. Select a procedure step and ask what it means. The explanation preserves mandatory actions, quantities, warnings, and escalation instructions, and keeps the original text available.
3. Ask "Can we assemble 20 units of Kit A?" and see availability and shortages calculated from the seeded database.
4. Ask a combined question about a shortage and the applicable procedure. The answer distinguishes computed inventory facts from cited procedural guidance.

The first screen is the working tool. It shows fictional-data provenance, an input, recent exchanges, source passages, and inventory results. It is not a marketing page.

## Scope and architecture

Use React/TypeScript/Vite for the frontend, FastAPI/Pydantic for the API, PostgreSQL/pgvector for storage and search, and SQLAlchemy/Alembic for database access/migrations. Use pytest for backend checks and Playwright for browser workflows. Docker Compose supports a repeatable local environment. Pin compatible versions when implementation begins.

The browser calls FastAPI. FastAPI validates the request and invokes a bounded assistant workflow with three tools: `search_procedures`, `lookup_stock`, and `check_build_readiness`. Retrieval returns versioned source sections. Inventory tools run parameterized queries and deterministic calculations. A provider adapter supplies generation and embeddings; credentials remain on the server. The API validates the final response before the frontend displays it.

Start with approximately 10 Markdown SOPs, 30 parts, and 6 single-level assemblies. All records are invented. A single warehouse and integer unit quantities keep inventory behavior understandable. Use stable document/section IDs and versions. Markdown is the first ingestion format; PDFs are a later addition.

Out of scope: employer integrations, employee records, purchasing, inventory writes, nested BOMs, arbitrary SQL generation, model training, fine-tuning, multi-agent product orchestration, voice, custom account management, and Kubernetes. Public hosting is a separate delivery decision; local runnability is required.

## Six workers

| ID | Provider | Responsibility | Project skill | Branch |
| --- | --- | --- | --- | --- |
| G1 | OpenAI/Codex | API, shared schemas, provider adapter, bounded assistant | `warehouse-api` | `agent/g1-api` |
| G2 | OpenAI/Codex | Sample SOP corpus, ingestion, retrieval, citations | `warehouse-retrieval` | `agent/g2-retrieval` |
| G3 | OpenAI/Codex | Independent evaluation cases, scoring, result evidence | `warehouse-evaluation` | `agent/g3-evaluation` |
| C1 | Claude Code | Seeded PostgreSQL inventory, BOM logic, domain tests | `warehouse-inventory` | `agent/c1-inventory` |
| C2 | Claude Code | Frontend, source viewer, clarification, readable UI | `warehouse-interface` | `agent/c2-frontend` |
| C3 | Claude Code | Local packaging, CI, integration checks, demo documentation | `warehouse-delivery` | `agent/c3-delivery` |

The main checkout is `C:\Users\andru\Documents\Codex\2026-09-16\wha\outputs\warehouse-assistant`.

The six worktrees are under `C:\Users\andru\Documents\Codex\2026-09-16\wha\work\warehouse-agents`, in folders `g1-api`, `g2-retrieval`, `g3-evaluation`, `c1-inventory`, `c2-frontend`, and `c3-delivery`.

Each worker loads `AGENTS.md`, [the product brief](docs/PROJECT_BRIEF.md), [the contracts](docs/CONTRACTS.md), its [assignment](agents/prompts/), and its one `.agents/skills/<skill>/SKILL.md`. Claude reads the same skill Markdown explicitly. No global skill installation is needed. OpenAI workers inherit the current model; Claude workers use the configured Claude Code default. Do not substitute one provider for the other silently.

## Ownership

| Worker | Application write scope |
| --- | --- |
| G1 | `backend/app/api/`, `assistant/`, `providers/`, `contracts/`, `main.py`, backend dependency files, `tests/api/` |
| G2 | `backend/app/retrieval/`, `ingestion/`, `data/sops/`, `tests/retrieval/`, assigned retrieval migrations |
| G3 | `evals/`, `tests/evaluation/`, `docs/evaluation.md` |
| C1 | `backend/app/inventory/`, `data/inventory/`, `tests/inventory/`, assigned inventory migrations |
| C2 | `frontend/`, including its package files, API mocks, and UI tests |
| C3 | `infra/`, `scripts/`, `.github/`, `tests/integration/`, `.env.example`, README and operations/demo docs |

Backend subdirectories abbreviated in the table are beneath `backend/app/`. The coordinator approves shared contracts and migration ordering. G1 owns backend dependency changes; C2 owns frontend dependencies. A worker requests cross-scope changes instead of editing another worker's files. C3 reviews integration without rewriting other workers' implementations.

## Build sequence and handoffs

### Phase 0: freeze contracts and establish a runnable skeleton

G1 proposes final Pydantic/OpenAPI types, tool interfaces, and response fixtures. The coordinator reconciles the six planning reports and freezes a contract revision. C2 checks that the response represents every UI state; C1 verifies inventory semantics; G2 verifies source provenance; G3 verifies scoreability. G1 adds the FastAPI skeleton and test provider adapter. C3 establishes the minimal PostgreSQL/pgvector Compose service and migration convention. C2 establishes the frontend shell.

Exit: health endpoint works; shared fixtures validate; the UI can render fixture responses; each branch starts from the same committed interface baseline. Fixtures are explicitly offline test data, not live AI output.

### Phase 1: parallel implementation against the contracts

- G1 implements the provider interface, strict tool schemas, execution bounds, and explicit dependency/error states against fakes.
- G2 authors the SOP corpus, metadata validation, idempotent ingestion, section lookup, and lexical retrieval baseline; then adds embedding retrieval.
- C1 implements constrained tables, deterministic seeds, lookup/ambiguity handling, and build-readiness calculations.
- C2 builds the conversation view, ordered procedural answers, original-source panel, inventory table, clarification choices, and loading/error states using contract fixtures.
- G3 authors reference cases, freezes split/group assignments, and builds deterministic graders and a human-review rubric. Retrieval developers use only development cases while tuning.
- C3 adds isolated local environments, CI for offline checks, and the integration-test harness.

Exit: each worker's component checks pass, owned files are committed, and the handoff states what was actually verified and what remains mocked.

### Phase 2: integrate a complete working flow

Merge inventory and retrieval services into the shared backend, then connect G1's tool loop to them. Connect the real frontend API client. Verify one cited SOP answer, one explanation, one correct inventory result, and one combined answer. Reuse a selected canonical part/assembly ID when resolving ambiguity. Ensure missing evidence does not turn a valid stock result into an invented procedural answer.

Exit: all primary workflows operate against the local seeded database and corpus; no hidden fixture substitution. If provider credentials are unavailable, report that limitation and retain explicit offline mode. Live LLM acceptance remains incomplete until a real run is performed.

### Phase 3: evaluate and revise

Run the lexical baseline and embedding retrieval on the same development cases. Compare retrieval coverage before deciding whether hybrid search or reranking is necessary. Inspect unsupported answers, incorrect citations, missing warnings, and ambiguous entities. Measure inventory values independently of the LLM's wording. Fix failures and rerun affected tests.

Freeze prompts/retrieval configuration before the held-out run. G3 publishes measured results with denominators, configuration, dataset versions, failures, and limitations. If held-out failures inform another tuning cycle, disclose that reuse and reserve new untouched cases for subsequent validation.

Exit: final evaluation is reproducible; deterministic calculations are correct; serious warning/citation failures are fixed; all remaining limitations are documented. Quality thresholds are release targets, not claims of achieved performance.

### Phase 4: finish the portfolio demo

C2 checks keyboard navigation, source-panel focus, screen-reader announcements, text resizing, contrast, mobile layout, and desktop/mobile screenshots. C3 verifies fresh local startup, seed/reset isolation, secret handling, and end-to-end scenarios; writes a short demo script and system diagram. G1/G2/C1 address issues in their own modules. The coordinator runs the combined checks and reviews the final README/resume claims.

Exit: a fresh checkout can run the app, load fictional data, complete the three workflows, and reproduce the documented checks. The README links to real evaluation evidence. Production integration is labeled future work.

## Worktree and merge protocol

Worktrees isolate files, not running services. Allocate environments before starting databases:

| Worker | API port | Frontend port | PostgreSQL port | Compose project |
| --- | --- | --- | --- | --- |
| Coordinator | 8100 | 5200 | 5500 | `warehouse-main` |
| G1 | 8101 | 5201 | 5501 | `warehouse-g1` |
| G2 | 8102 | 5202 | 5502 | `warehouse-g2` |
| G3 | 8103 | 5203 | 5503 | `warehouse-g3` |
| C1 | 8104 | 5204 | 5504 | `warehouse-c1` |
| C2 | 8105 | 5205 | 5505 | `warehouse-c2` |
| C3 | 8106 | 5206 | 5506 | `warehouse-c3` |

These are proposed ports, not reservations. Check availability and choose alternatives when occupied. Use Compose-scoped volumes without globally fixed names. Only launch services a worker needs; the frontend can use API fixtures before integration. Every reset validates its demo database identity and requires an explicit reset command; startup is not destructive.

Merge small tested commits in this order: G1 interface foundation; C3 local-service foundation; C1 inventory; G2 retrieval; G1 real orchestration; C2 frontend; G3 evaluation; C3 final integration/docs. Some scaffold commits can land earlier when they do not change contracts. Workers update from the coordinator's merged baseline at each phase boundary. No worker merges a sibling branch independently or overwrites another worker's changes.

Cross-provider review pairs: G1 and C2 check HTTP schemas, generated types, and clarification/source presentation; G2 and C1 check migrations, data boundaries, and reproducible seeds; G3 and C3 check evaluation tiers, CI, and release evidence. C1 also independently recomputes G3's inventory expectations. The coordinator resolves disagreements and checks integration. Reviewers report findings; owners implement fixes.

## Required correctness checks

- Source links identify the exact document version and section. Unknown citation IDs cannot become valid links.
- Procedure simplification preserves mandatory steps, quantities, conditions, and stop/escalation instructions. Shorter wording alone is not success.
- Build requests require a selected assembly and positive bounded integer quantity. Arithmetic runs in Python/SQL, not model prose.
- Test sufficient stock, exact stock, shortages, missing rows, zero stock, invalid quantity, empty BOM, duplicate components, and ambiguous aliases. Unknown stock and zero stock remain distinct.
- A build check reads a consistent dataset snapshot and returns its identity/time. Stock answers show they refer to the fictional dataset.
- Retrieved documents cannot authorize tool changes. The model cannot write inventory, generate arbitrary SQL, or invoke unlisted tools.
- Provider timeout, database unavailability, and insufficient evidence have explicit states. Retry/call limits prevent an unbounded tool loop.
- Browser tests exercise the actual frontend/backend for integration acceptance, not just mocked UI fixtures.

## Evaluation design

Adopt G3's proposed 84-case allocation: 18 procedure retrieval/answers, 12 passage explanations, 18 inventory/build checks, 12 missing/ambiguous/invalid input cases, 9 unsupported/conflicting evidence cases, 6 dependency failures/limits, and 9 instruction-injection/tool-misuse cases. Use 56 development and 28 held-out cases grouped to prevent sibling/paraphrase leakage. See the independent [evaluation report](docs/agent-reports/G3-evaluation.md) for category-level split counts and representative cases.

Report retrieval recall at the selected k, citation validity and source support, exact inventory correctness, correct clarification/insufficient-evidence behavior, mandatory-step retention, and observed latency/cost when measured. Report answerable-question success as well as refusal behavior. An assistant that refuses everything must fail.

Inventory/schema/source-identity checks can be automated. Source support and plain-language fidelity use a written human rubric: review every live response, with a second reviewer checking all failures and at least 20% of remaining answers. An optional LLM judge is not the sole authority. Keep live model runs separate from mocked component/integration tests. Store failures as first-class results. No revenue, worker productivity, or accessibility KPIs are required.

Initial release targets: 100% deterministic inventory/schema/source-resolution checks; zero lost mandatory warnings or unauthorized tool calls; held-out retrieval recall@5 of at least 90%; supported claims at least 95%; answerable completion and correct uncertainty/clarification each at least 90%. These are targets to test, not measured results or population-level reliability guarantees. Publish small category denominators and failures rather than only a single aggregate score.

## Implementation kickoff

The current assignment is planning only. When implementation begins, the coordinator explicitly changes the phase in AGENTS.md/CLAUDE.md and dispatches an implementation task to each role. Do not use the current planning prompts as instructions to build code without changing that phase.

For each worker, the kickoff message should name its absolute worktree, branch, role prompt, skill file, approved contract revision, owned files, milestone, and required acceptance checks. Require a handoff containing changed paths, commit IDs, tests run, mocked/live distinction, unresolved issues, and requested shared-file changes. Retain existing model defaults unless a particular model is requested.

The three Claude workers can be started from their worktrees using Claude Code; the three OpenAI workers use Codex subagents or separate coding sessions pointed to their assigned worktrees. Load the local role skill explicitly. Use normal permission controls. A missing provider, exhausted account, or authentication failure must be reported instead of relabeling a different model as the requested provider.

## Resolved review decisions

All six workers completed a planning report. The coordinator adopted their recommendations with these explicit resolutions:

- Use CONTRACTS.md v1 as the source of truth; reports that reference v0 are historical proposals.
- Unknown readiness is nullable, not a blanket false. A known shortage is false even if another component is unknown; retain an incomplete-data flag. Empty BOMs are incomplete, never ready.
- Use a maximum requested build quantity of 10000 throughout the demo. Resolve names through the catalog service without adding a fourth model tool.
- Conflicting current procedures mean insufficient evidence. The user can clarify scope, but should not be asked to decide which incompatible procedure is authoritative.
- Source requests require an exact version. Citation links and step associations use server-issued IDs. Selection travels in the typed request context, not only conversational history.
- Generate frontend types from G1's frozen schema. Put fixture substitution in the test/development API boundary; never silently substitute a fixture for a failed live request.
- Announce new answers without stealing focus while a user is typing. Moving into a source panel is an explicit user action, with a predictable return path. Browser checks described by C2 are planned, not already performed.
- Keep Compose configuration in `infra/compose.yaml`. C3 owns it. Sequence Alembic predecessors as well as assigning distinct filenames.
- Offline CI can pass without provider keys. Live checks are explicitly skipped when not configured; attempted failing checks remain failed. A skipped or unavailable live run cannot satisfy the completed-demo release gate or support LLM-quality claims.

The run record is [agents/RUN_STATUS.md](agents/RUN_STATUS.md). All work so far is planning/setup, not application implementation or executed product tests.

## Reference material

- [OpenAI worktree documentation](https://learn.chatgpt.com/docs/environments/git-worktrees) explains file/branch isolation.
- [OpenAI skills documentation](https://learn.chatgpt.com/docs/build-skills) describes project-local `.agents/skills` discovery.
- [Microsoft RAG sample](https://github.com/Azure-Samples/azure-search-openai-demo) is a reference for document retrieval and source presentation, not a project to copy wholesale.
- [AWS agent evaluation example](https://github.com/aws-samples/sample-evaluating-agents-on-aws-with-strands-and-agentcore) provides a comparison for tool and answer evaluation.

See [the roster](agents/ROSTER.md), [shared contracts](docs/CONTRACTS.md), and individual reports under `docs/agent-reports/` for the handoffs and decisions behind this plan.
