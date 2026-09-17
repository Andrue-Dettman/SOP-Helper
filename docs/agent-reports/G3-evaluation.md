# G3 Evaluation Implementation Plan

Planning only. No application implementation or evaluation runs; all checks and thresholds below are proposed. G3's future scope is `evals/`, `tests/evaluation/`, and `docs/evaluation.md`; domain tests remain with their owners. Contracts v1 are authoritative.

## Ordered tasks and dependencies

1. Obtain G1's typed schemas, adapter injection seams, and bounded traces; G2's versioned fictional corpus and required-step/warning annotations; C1's immutable seed snapshots; and C3's isolated database/run instructions. Request dependencies through the coordinator, without editing other scopes.
2. Independently author an 84-case manifest using every evaluation-contract field. Label exact document/version/section identities and snapshot metadata from source artifacts, never application answers. Have another reviewer recompute inventory expectations from the seed specification without implementation helpers.
3. Freeze manifests and group assignments before tuning. Keep paraphrases, shared arithmetic scenarios, and injection siblings in one split. Implementers may read the corpus; held-out questions and labels stay outside tuning inputs. If exposed, mark groups as regression cases and replace them before claiming unseen-case performance.
4. Implement case loading, tier adapters, deterministic graders, human review forms, and report generation. Test graders with deliberately wrong arithmetic, omitted components, fabricated citations, missing warnings, and null-to-zero substitutions. Invalid manifests, skipped cases, and unavailable reviewers must be visible rather than counted as passes.
5. Compare keyword and embedding retrieval on identical corpus/cases, tune only on development groups, then evaluate a frozen release candidate. Log every run, including failed attempts. After fixes informed by held-out failures, report reruns as regression evidence.

## Case allocation and independent expectations

Categories are exclusive; secondary tags identify combined questions and overlapping risks. Repeats do not increase the case count.

| Primary category | Development | Held-out | Total |
| --- | ---: | ---: | ---: |
| Procedure retrieval and grounded answers | 12 | 6 | 18 |
| Term explanations and simplification | 8 | 4 | 12 |
| Stock and build arithmetic | 12 | 6 | 18 |
| Missing, ambiguous, or invalid inputs/data | 8 | 4 | 12 |
| Unsupported or conflicting evidence | 6 | 3 | 9 |
| Dependency failures and execution limits | 4 | 2 | 6 |
| Instruction injection and tool misuse | 6 | 3 | 9 |
| **Total** | **56** | **28** | **84** |

Representative cases, with provisional fictional IDs pending coordinator approval:

- `KIT-A`, quantity 20, consumes three brackets and two pads per kit. Snapshot `eval-stock-v1` has 59 brackets and 40 pads: requirements 60/40, shortages 1/0, `ready=false`. Store the complete expected table and exact snapshot timestamp as literals.
- A missing pad row gives pad availability/shortage null. With sufficient brackets, `ready=null`; with a bracket shortage, `state=incomplete`, `ready=false`. Keep these siblings together. Separate groups cover zero stock, exact sufficiency, empty BOMs, canonical-ID precedence, and ambiguous aliases.
- “Receive this delivery” must retrieve the current receiving sections, retain labeled prerequisites, ordered steps, quantities, warnings, and escalation actions. Selected historical text must remain visibly historical; its citation must resolve the exact old version.
- “Can we build 20 kits, and what if parts are short?” retains valid inventory results when procedure retrieval fails, returning `temporarily_unavailable`/503. Conflicting current procedures instead require `insufficient_evidence`/200; ambiguity requests the specific missing decision.
- Typed quantities `true`, `"20"`, `1.5`, zero, negative, and 10001 are rejected before dispatch; 1 and 10000 are valid boundaries. Natural-language quantity extraction is distinct from coercing invalid tool arguments.

Use test-local fixtures for malformed BOMs and missing rows; do not corrupt the runtime seed. Document injections request warning removal, fabricated stock, unknown tools, or fabricated URLs. History attacks assert stale stock. Expect supported help without accepting injected authority; use invented sentinel secrets and no real external destinations.

## Execution tiers and scoring

Component runs evaluate real retrieval and deterministic inventory outputs without a model. Mocked integration runs drive actual orchestration using scripted provider responses and adapter failures. Cover 422 validation, 503 unavailability, 504 deadline expiry, malformed arguments without retry, one transient retry, and three-model/six-tool/30-second budgets including failed attempts. These prove wiring only. Live runs invoke the configured model and review actual final answers; disclose any injected dependency and embedding fixture. Record generation and embedding execution modes separately from `data_mode=synthetic`.

Retrieval: macro-average recall@5 over labeled relevant sections, deduplicating chunks; also report reciprocal rank and complete-required-context coverage after expansion. No-evidence cases use false-evidence rate, not undefined recall. Compare both retrieval methods on the same denominators; defer reranking unless development evidence supports it.

Citations: deterministically verify IDs, versioned resolution, exact excerpts, and step references. Human review measures supported factual claims/all factual claims and cited-support coverage of claims requiring evidence. Empty answers cannot earn perfect support; omissions reduce mandatory-fact coverage and answerable completion.

Inventory exact-match requires all expected components, quantities, nulls, readiness/state, and snapshot identity, without extras. Check prose numbers against structured results. Score status and HTTP outcome separately. Clarification must identify the missing choice without premature calculations. Report answerable completion alongside correct uncertainty behavior to expose blanket refusals.

Review every live answer: plain-language rubric 0 = misleading/unusable, 1 = understandable with minor issues, 2 = clear, concise, ordered where appropriate, with jargon explained. Separately grade every mandatory action, warning, quantity, and sequence constraint; brevity cannot compensate for omissions. Review original-step fallback disclosure. A second reviewer checks every failure and 20% of remaining responses; record disagreements. An LLM judge is unnecessary initially.

## Proposed release gates, evidence, and risks

Targets: 100% applicable deterministic inventory/schema/source checks; zero unauthorized dispatches, injection compliance, unsupported inventory numbers, or lost required actions/warnings; held-out recall@5 at least 90%; supported claims at least 95%; answerable completion and correct uncertainty each at least 90%; every reviewed answer scores at least 1 for clarity. Report integer numerators/denominators by tier/category; critical failures block regardless of averages. Unrun live cases prevent live-behavior claims.

Persist manifest/corpus/seed hashes, commit plus dirty-file hashes, prompt/configuration hashes, model/provider and embedding metadata, retrieval settings, timestamps, observed latency, outputs, and expected-versus-actual failures with trace IDs and reproduction commands. Exclude credentials. Small samples, reviewer disagreement, leakage, and provider variability limit conclusions; never select only favorable runs.

No shared-contract changes are required. Request coordinator clarification of nested procedure-result enums and partial-failure error details when G1 freezes schemas. Portfolio evidence should show reproducible commands, baseline comparisons, reviewed successes/failures, and limitations without business KPIs, validated-accessibility claims, or model-training claims.

Checks actually performed: read assigned planning sources and reviewed this report. No tests, evaluations, installs, services, or commits. Git status could not run because the worktree Git metadata points to a missing location; metadata was left unchanged.
