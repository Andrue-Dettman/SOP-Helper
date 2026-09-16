# G1: OpenAI API and orchestration planner

Read AGENTS.md, docs/PROJECT_BRIEF.md, docs/CONTRACTS.md, and .agents/skills/warehouse-api/SKILL.md. You are one of six workers. This pass is planning only.

Produce a concrete implementation plan for typed FastAPI endpoints, provider/embedding interfaces, bounded tool calling, response/citation validation, and explicit errors. Describe exact proposed request/response fields and an implementable sequencing plan. Identify flaws or ambiguities in v0 contracts and propose resolutions. Keep the product small. Include acceptance tests and handoffs to retrieval, inventory, UI, and evaluation.

Future write scope: backend/app/api/, backend/app/assistant/, backend/app/providers/, backend/app/contracts/, backend/app/main.py, backend Python dependency files, tests/api/. No frontend, inventory implementation, or retrieval implementation edits.

Current write scope: docs/agent-reports/G1-api.md only, inside your assigned worktree. Aim for 700-1100 words. State decisions, ordered tasks, file scope, dependencies, tests, and risks. Do not commit or implement code. Report the absolute path changed in your final answer.
