# C1: Claude inventory planner

Read AGENTS.md, docs/PROJECT_BRIEF.md, docs/CONTRACTS.md, and .agents/skills/warehouse-inventory/SKILL.md using your read tools. You are one of six workers. This pass is planning only. Do not create files, run commands, or spawn subagents.

Design the seeded PostgreSQL inventory/BOM module and typed tool results. Supply concrete tables/constraints, a tiny worked build-readiness example, seed characteristics, read-only access, transaction/snapshot semantics, missing/ambiguous data handling, and deterministic acceptance tests. Keep the scope to a single warehouse, integer quantities, and one-level assemblies. Challenge defects in the shared v0 contract and suggest precise fixes.

Future write scope: backend/app/inventory/, data/inventory/, tests/inventory/, and explicitly allocated inventory migration files. Request dependencies/shared schema changes from G1/coordinator.

Return a 700-1100 word Markdown report in your final response, with decisions, ordered tasks, file ownership, dependencies, acceptance tests, and risks. The coordinator will save it to docs/agent-reports/C1-inventory.md. Do not implement the project or claim checks were executed.
