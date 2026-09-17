# G3 evaluation implementation and handoff

The G3 evaluation package validates 84 independently authored case definitions and
scores captured outputs. It uses the Python standard library; no dependencies,
provider credentials, database, or services are needed for harness checks.

This is an evaluation harness, not an implemented warehouse application. This
worktree currently has no backend, production SOP corpus, or inventory seed to
execute against. No application component, mocked integration, or live model
evaluation has run. Harness unit tests use artificial positive and negative
controls; their success says nothing about application answer quality.

The user authorized moving beyond planning and subsequently authorized committing
the G3 work. Implementation changes remain within `evals/`, `tests/evaluation/`,
and this document; the earlier planning report is included in the G3 handoff.
The worktree Git pointer failed during planning but resolves at handoff. G3 did
not modify that pointer. The checkout base is
`dcceec4714c14b60ccb71d519d1df506164602f9` at the start of implementation.

## Run the available checks

Run these commands from the assigned G3 worktree:

```powershell
Set-Location 'C:\Users\andru\Documents\Codex\2026-09-16\wha\work\warehouse-agents\g3-evaluation'
python -m evals validate
python -m unittest discover -s tests/evaluation -v
```

Validation checks allocation, case fields, duplicate IDs, split leakage within
groups, source identities, scenario references, quantity types, and oracle
snapshot bindings. It prints the manifest and fixture SHA-256 hashes.
Tests are also discoverable by pytest once G1 supplies that dependency.

Verification actually performed on Python 3.12.10: manifest validation passed
with 84 cases, 21 groups, and the 56/28 split; all 37 harness unit tests passed.
`git diff --check` passed for tracked changes. New implementation files were
checked separately for trailing whitespace. These are harness checks only;
application evaluation remains unrun.

## Suite and fixture status

| Category | Development | Held-out candidates | Total |
| --- | ---: | ---: | ---: |
| Procedure retrieval and answers | 12 | 6 | 18 |
| Explanations | 8 | 4 | 12 |
| Stock and build arithmetic | 12 | 6 | 18 |
| Missing/ambiguous/invalid inputs and data | 8 | 4 | 12 |
| Unsupported or conflicting evidence, version selection | 6 | 3 | 9 |
| Dependency failures and limits | 4 | 2 | 6 |
| Injection and tool misuse | 6 | 3 | 9 |
| Total | 56 | 28 | 84 |

There are 21 groups. Retrieval/explanation paraphrases and receiving injection,
conflict, and historical cases share development groups. Strict invalid-quantity
variants stay in development. The held-out quantity-clarification cases share the
held-out boundary-inventory group. Held-out history and partial-failure cases use
independent assembly IDs, stock tables, quantities, and snapshots.

`evals/cases.json` contains literal oracle tables, not calls to inventory code.
For example, 20 KIT-A units require 60 brackets and 40 pads; availability 59/40
means shortages 1/0. KIT-C cases distinguish a missing pad stock row from zero,
and preserve a known bracket shortage alongside missing pad data. Stock captures
also exercise an explicit zero and a known part with an absent stock row.

`evals/fixtures.json` is a **provisional evaluation fixture specification**, not
the application seed. Its ten current sample sections, historical section,
conflicting section, scenario inventory tables, and adapter fault descriptions
are synthetic. G2/C1 must bind these definitions to their test fixtures through
the coordinator before product evaluation. The injection payload is supplied to
the test adapter as retrieved data, never as a system instruction. A fault case
must use adapter injection, not disruption of a running external service.

The `held_out` label expresses intended allocation only. Questions and answers
are currently visible together in this worktree and have not been independently
sealed or reviewed. The coordinator must restrict tuning access, obtain an
independent arithmetic/label review, freeze hashes, and replace any groups used
for tuning before making held-out generalization claims. Group validation does
not detect every conceptual sibling; independent review is necessary.

## Capture boundary for the other workers

No tool, HTTP client, or model runner is hidden inside the scorer. G1/C3 should
capture actual execution into JSONL, one object per selected case. Use a separate
capture for each tier/configuration/repetition. Never replace failed live calls
with mock responses. `input.kind=chat` contains a request object; `kind=tool`
contains a tool name and typed arguments. Internal invalid-quantity cases are
component-only and expect `response.validation_error=true`; no HTTP status is
invented for an internal tool rejection.

Minimal completed capture structure (values below describe the capture schema;
they are not a successful product example):

```json
{
  "case_id": "inventory-shortage-01",
  "outcome": "completed",
  "http_status": 200,
  "response": {},
  "trace": {
    "model_attempts": 1,
    "tool_attempts": [
      {"name": "check_build_readiness", "arguments_valid": true, "dispatched": true}
    ],
    "elapsed_ms": 1200,
    "dependency_attempts": [
      {"operation_id": "generation-1", "duration_ms": 500, "retry_reason": null}
    ]
  }
}
```

`response` is the actual contracts-v1 envelope. Component adapters normalize
service outputs into its applicable fields, such as `inventory_result` or
`status`. Preserve raw service results in an additional observation field for
audit. The scorer compares inventory structures strictly, including types,
snapshot timestamp, components, and stock matches; component/match order does
not matter. Its provisional stock projection is
`{kind, state, snapshot, matches: [{part_id, quantity, unit}]}`. G1/C1 must approve
or map this projection when the stock schema freezes. Do not fabricate model
output to fill a component envelope.

When retrieval applies, add:

```json
{
  "retrieval": {
    "ranked_source_ids": [
      {"document_id": "receiving", "version": "2", "section_id": "delivery"}
    ],
    "expanded_source_ids": [
      {"document_id": "receiving", "version": "2", "section_id": "delivery"}
    ]
  }
}
```

The ranked list preserves chunk rank, including repeated section identities.
Recall uses unique matching sections within the first five chunks; a sixth hit
cannot be promoted by deduplication. Expanded identities describe context actually
supplied downstream, not all corpus sections. Missing retrieval capture remains
pending when expected sources exist. No-evidence cases use false-evidence rate;
their recall denominator would otherwise be undefined.

Trace counts include failed attempts. Repeat attempts share an `operation_id`;
only a second transient attempt is allowed. Record rejected tool requests with
`dispatched=false`. Instrument dispatch independently of model text. The scorer
checks the allowlist, validated arguments, three model/six tool attempts,
30-second deadline, and ten seconds per dependency attempt. It cannot establish
the authenticity of a supplied trace or replace G1's execution-control tests.

Live captures additionally require `provider_calls` between one and three,
matching trace model attempts. Mocked transport failures while calling a real
model must be disclosed in configuration. A failure before any model call is
component/mocked dependency evidence, not a live-model observation.

For capture failures use `outcome=error` with an `error` explanation. For an
unrun case use no record, or `outcome=skipped` with `reason`. These yield failed,
missing, or pending outcomes and remain in completion denominators.

## Human review and scoring

Create blank review forms bound to each captured output's SHA-256:

```powershell
python -m evals review-template --observations evals/runs/run-001-observations.jsonl --output evals/runs/run-001-reviews.jsonl
```

These files must first be populated from real captures; the command does not run
the application. A reviewer reads the answer and original evidence, records their
identity, counts all factual claims and supported claims, and counts claims
requiring citations and claims with supporting citations. Empty denominators
produce a null rate, never 100%. For answerable model cases, zero claims cannot
pass. Citation identity/excerpt checks alone cannot establish semantic support.

Review each mandatory fact and warning as a boolean, including sequence,
quantities, prerequisites, and escalation conditions. Review every forbidden
action's absence. Also judge numerical prose and clarification usefulness where
applicable. Null values leave checks pending. Plain-language scores are 0 for
misleading/unusable, 1 for understandable with minor issues, and 2 for clear,
concise guidance with necessary jargon explained. Inspect fallback disclosure
and whether historical context is clearly marked. A second reviewer should check
every failure and at least 20% of other answers; preserve disagreements and
adjudication in review notes. This sampling is a release process requirement,
not automatically certified by the current grader.

An altered capture invalidates its earlier human review. Missing human review or
execution trace prevents a mocked/live case from passing. No LLM judge is used.

## Reports and provenance

Create metadata with all these fields:

```json
{
  "run_id": "run-001",
  "captured_at": "2026-09-16T00:00:00Z",
  "tier": "component",
  "commit": null,
  "working_tree_sha256": null,
  "case_manifest_sha256": "copy the actual validate output",
  "fixtures_sha256": "copy the actual validate output",
  "corpus_revision": "eval-corpus-v1",
  "seed_revision": "eval-stock-v1",
  "generation_mode": "none",
  "embedding_mode": "none",
  "provider": null,
  "model": null,
  "retrieval_mode": "keyword",
  "prompt_sha256": null,
  "configuration": {}
}
```

Use real run time and configuration. If Git remains broken, keep `commit=null`
and disclose the provenance gap; do not invent a revision. Include actual dirty
file hashes, chunker/index generation and embedding provider/model/dimensions,
prompt hash, retrieval limits, dependency fault configuration, and relevant
settings in `configuration`. Do not store keys, tokens, or authorization headers.
`data_mode=synthetic` is independent of generation/embedding execution modes.

```powershell
python -m evals score --observations evals/runs/run-001-observations.jsonl --reviews evals/runs/run-001-reviews.jsonl --metadata evals/runs/run-001-metadata.json --output evals/runs/run-001-report
```

Omit `--reviews` for component scoring. Use `--split development` or `held_out`
with capture files restricted to that selection. Unknown, duplicate, or
unselected case IDs are rejected. CLI exit codes: 0 means every selected case's
implemented checks passed; 1 means failed/missing/pending cases; 2 means invalid
input or output-path errors. Existing evidence files are never overwritten.

The report retains raw captures, reviews, expected/actual failure details,
observation hashes, metadata, per-category denominators, completion rates, and
observed-only retrieval/support metrics. Reports are JSON and Markdown. Retain
the hashed manifests and metadata alongside them to reproduce the scoring
command. Measured elapsed time is preserved in traces; no latency numbers are
estimated. Missing provenance is explicit. Reports always leave
`release_accepted=false`: release approval is not a scoring-script side effect.

## Remaining integration and release work

G1 must supply frozen procedure/stock schemas, budget/error mapping, traces, and
adapter fault seams. G2/C1 must bind the independent fixture definitions and
review the literal source/inventory expectations; C3 owns actual application
capture runners, integration environment, and CI wiring. Update only G3 files
after those interfaces settle; request shared-file changes through the coordinator.
Current fault scripts are declarative requirements, not implemented injections.

Targets remain: 100% deterministic inventory/schema/source checks; zero lost
required actions/warnings, unauthorized dispatches, or injection compliance;
held-out recall@5 at least 90%; claim support at least 95%; answerable completion
and appropriate uncertainty at least 90%; all reviewed answers at least 1 for
clarity. A case's context check is stricter than aggregate recall. Release gates
also require G1's full Pydantic validation, which this independent scorer does
not replace. Do not average away critical failures or treat observed-only metrics
as full-suite rates. Compare keyword and embedding runs on the same frozen cases;
report all repetitions and failures, not only the best run.

Publish real measured outcomes and limitations only. Small samples, visible
candidate labels, unverified fixture bindings, human review disagreement, and
provider nondeterminism limit conclusions. No business KPIs, validated
accessibility outcomes, or model-training claims are supported by this work.
