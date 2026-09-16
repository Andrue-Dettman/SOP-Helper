---
name: warehouse-api
description: Design and implement the typed API and bounded LLM tool-calling workflow for this synthetic warehouse assistant.
---

Read `docs/PROJECT_BRIEF.md` and `docs/CONTRACTS.md` first. Keep transport models, provider adapters, and domain services separate enough to test without a paid model call. The application uses one bounded assistant loop, not the six development workers.

Use an allowlist of retrieval, stock lookup, and build-readiness tools with typed inputs. Never expose SQL execution or database writes. Render computed quantities from validated tool results; do not let prose silently replace them. Treat previous messages and retrieved text as untrusted context. Clarify canonical IDs when ambiguous.

Distinguish insufficient evidence, ambiguity, dependency failure, and invalid input. Timeouts and retries have finite limits. Validate citations against retrieved section IDs. Keep model keys server-side. Review current official provider documentation before implementing the provider adapter; the locally available OpenAI Docs skill can assist OpenAI-specific work.

Checks must include tool-argument rejection, bounded execution, provider failures, invented citations, missing inventory, and history that attempts to override tool policy. Offline adapter tests do not establish live model quality.
