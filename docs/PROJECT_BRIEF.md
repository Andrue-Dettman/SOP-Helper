# Product brief

## Purpose

Build an independently runnable portfolio demo inspired by warehouse operations at a social enterprise. Help workers find and understand procedures and help supervisors answer stock/build-readiness questions. The author already has React, FastAPI, PostgreSQL, AWS, SQL, and warehouse software experience. The project should add demonstrable RAG, embeddings, LLM tool calling, validation, and evaluation experience.

## Constraints

- All SOPs, products, parts, stock, and bills of materials are invented for this demo.
- No access to employer production systems and no dependency on them.
- No claims of revenue recovered, time saved, reduced absenteeism, user adoption, or validated accessibility outcomes.
- Plain language, short ordered steps, visible source passages, keyboard access, and readable responsive screens are design requirements. Do not claim that these meet every disabled user's needs.
- Future production integration belongs in a roadmap, not in present-tense resume claims.
- Six development workers: 3 OpenAI/Codex, 3 Claude Code. Keep file ownership disjoint. The coordinator integrates.

## Three primary workflows

1. Ask how to receive a delivery. Retrieve the current sample procedure; provide a plain-language explanation with citations and original text.
2. Ask what a term or step means. Explain using the selected procedure; preserve quantities, sequence, warnings, and stop/escalation instructions.
3. Ask whether 20 units of a selected assembly can be built. Query seeded inventory/BOM data; calculate shortages and cite the fictional dataset snapshot. A combined question can also request the applicable shortage procedure.

## Proposed stack

Python/FastAPI backend, PostgreSQL with pgvector, React/TypeScript/Vite frontend, SQLAlchemy/Alembic, pytest, Playwright, Docker Compose, and a small provider interface for an LLM and embeddings. Use maintained libraries for parsing and retrieval primitives. Pin versions during implementation after checking compatibility. Do not invent package versions or model availability.

Build keyword retrieval as a baseline and embedding retrieval as the main comparison. Combine/rerank only if evaluation supports it. Avoid fine-tuning, multi-agent runtime orchestration, Kubernetes, a custom auth platform, real purchasing, employee records, or production integration in this version.

## Data size and boundaries

Initial scope: approximately 8-12 fictional SOPs, 25-40 parts, 5-8 one-level assemblies. Markdown is the canonical SOP source; preserve headings and stable section IDs. PDF import is optional after core retrieval works. Integer unit quantities and one warehouse simplify the first inventory implementation. Nested BOMs, reservations against multiple orders, alternative parts, and unit conversion are future work.

## Evaluation expectations

Plan 60-100 independently specified cases split into development and held-out groups. Score reference retrieval, citation correctness, expected inventory values, useful clarification, and missing-information behavior. Include instruction-like malicious text in a fictional document as a robustness test. Report actual outcomes and limitations; no invented metrics. Use deterministic checks and human review before adding an LLM judge. Offline fixtures are not proof of live LLM behavior.

## Definition of done for the future application

A fresh checkout can launch with documented local steps, seed/reset only its own demo database, and exercise all three workflows. The UI shows that data is fictional. Citations resolve to original passages. Inventory arithmetic is correct. Provider failures are explicit. Tests and a reproducible evaluation report exist. A short demo and honest project README support the resume bullets. Publishing is a later explicit step; local runnability is required.
