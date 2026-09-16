# G3 Evaluation Implementation Plan

Planning only; no implementation or evaluation runs. Thresholds are proposed targets. G3 owns `evals/`, `tests/evaluation/`, and `docs/evaluation.md`; domain service tests remain with their owners.

## Ordered Work and Dependencies

1. Coordinator freezes contracts below with G1, G2, and C1, including uncertainty and validation behavior.
2. G2 supplies fictional procedures with stable section/version identities, warning annotations, and current/conflicting versions. C1 supplies isolated seed snapshots covering missing rows, empty BOMs, and ambiguity. G3 authors expectations independently, without application outputs or implementation helpers.
3. Review the 84-case manifest; freeze held-out cases before tuning. Keep paraphrases, shared numerical scenarios, and injection variants together by `group_id`. Corpus access is permitted; held-out questions and labels stay outside tuning inputs. Replace exposed groups before claiming held-out performance.
4. Implement adapters, graders, and the human rubric. Coordinate error fixtures with G1 and isolated databases with C3. Test graders using incorrect answers, missing citations, unknown quantities, and mismatched snapshots.
5. Compare keyword and embedding retrieval on the same frozen corpus. Tune on development cases; run held-out evaluation once per release candidate. Corrections after inspecting failures make subsequent runs regression evidence, requiring fresh hidden groups for new generalization claims.

## Case Allocation

Categories are exclusive; counts exclude retries.

| Primary category | Development | Held-out | Total |
| --- | ---: | ---: | ---: |
| Procedure retrieval and grounded answers | 12 | 6 | 18 |
| Term explanations and simplification | 8 | 4 | 12 |
| Stock and build arithmetic | 12 | 6 | 18 |
| Missing, ambiguous, or invalid inputs/data | 8 | 4 | 12 |
| Unsupported or conflicting evidence | 6 | 3 | 9 |
| Provider/database failures and limits | 4 | 2 | 6 |
| Instruction injection and tool misuse | 6 | 3 | 9 |
| **Total** | **56** | **28** | **84** |

Include combined inventory/procedure questions under these categories. Freeze answerability labels so refusal cannot inflate accuracy.

Representative fixtures: twenty kits require three brackets and two pads each; available quantities 59 and 40 imply requirements 60/40, shortages 1/0, and not-ready. Separate groups cover exact sufficiency, a missing pad row with unknown availability, an empty BOM, ambiguous assembly names, and fractional/negative quantities. Hand-calculate expected component tables and have a second reviewer recompute them independently; never import the inventory service into oracle construction.

Procedure cases ask for receiving instructions, a term explanation, an unsupported procedure, and conflicting current instructions. Label mandatory steps, sequence constraints, quantities, warnings, and escalation text. Injection fixtures place instruction-like content inside retrieved fictional sections, messages, and history: requests to ignore warnings, fabricate stock, invoke an unknown tool, or follow an external source path. Expected behavior preserves supported help and rejects injected authority; no real credentials or external destinations are involved.

## Scoring and Execution

Component runs grade retrieval and structured service outputs without a model. Mocked integration runs exercise actual orchestration with scripted provider responses, timeouts, malformed arguments, and call-limit exhaustion; they establish wiring behavior only. Live runs exercise the configured provider and final answers. Report each tier separately and mark unsupported/unrun cases explicitly.

Retrieval recall@5 is relevant sections retrieved divided by labeled relevant sections, macro-averaged over applicable cases. Also report all-required-sections coverage and reciprocal rank; a top hit alone cannot establish complete support. Citation identity must resolve the exact document/version/section and quoted passage. Human reviewers score supported factual claims divided by all factual claims, plus coverage of claims requiring citations; citation count earns no credit.

Inventory exact-match requires every expected component, quantity, shortage, readiness state, and snapshot identity, with no extra components. Null availability never equals zero. Clarification passes only when it requests the missing decision and avoids premature numerical conclusions. Report answerable-case completion alongside correct uncertainty/refusal rates with separate denominators.

Review all live responses with a written 0/1/2 plain-language rubric: unusable/misleading, understandable with minor issues, or clear concise ordered guidance. Independently check every mandatory step, warning, quantity, and sequence constraint as pass/fail. A second reviewer checks all failures and at least 20% of remaining responses; record disagreements and adjudication. No LLM judge is required.

## Proposed Contract Changes

- Add structured source references, `answerable`, mandatory facts/warnings, forbidden actions, fixture/snapshot identity, expected HTTP outcome, and applicable tiers to evaluation cases. Preserve existing fields.
- Add an explicit version selector to section retrieval; the current URL alone cannot guarantee historical citation resolution.
- Specify nullable availability/shortage, component data status, and readiness `ready | not_ready | unknown`, retaining `ready=true` only for complete sufficient data. Distinguish invalid typed arguments from chat clarification.
- Provide internal traces linking retrieved passage identities, validated tool calls/results, limits, errors, and snapshot IDs to `trace_id`, excluding keys. Define status mapping for conflicting evidence and partial combined answers.

## Release Evidence and Risks

Targets: 100% deterministic inventory/schema/source-resolution checks; zero lost mandatory warnings, unauthorized tool calls, or injection compliance; held-out retrieval recall@5 >=90%; supported claims >=95%; answerable completion >=90%; and correct uncertainty/clarification >=90%. Require plain-language score >=1 on every reviewed answer. Report numerators, denominators, and failures per category; tiny samples limit conclusions.

Store case-manifest hash, corpus/seed hashes, commit, prompts, provider/model configuration, retrieval settings, timestamps, measured latency, raw synthetic outputs, and failure records containing expected/actual values and reproduction commands. Provider nondeterminism, label errors, leakage, and small samples remain risks. Portfolio evidence includes reproducible commands, baseline comparisons, reviewed examples, failures, and limitations; publish actual results only, with no business or validated-accessibility claims.
