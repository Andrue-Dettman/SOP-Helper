# G2: OpenAI retrieval planner

Read AGENTS.md, docs/PROJECT_BRIEF.md, docs/CONTRACTS.md, and .agents/skills/warehouse-retrieval/SKILL.md. This pass is planning only.

Plan a small fictional SOP corpus, canonical document metadata, section/step chunking, ingestion, lexical and embedding retrieval, exact source lookup, and version/conflict handling. Propose a concrete document/section fixture and identify how mandatory warnings survive simplification. Explain what evidence justifies hybrid search or reranking later. Coordinate schema/migration needs, embedding contracts, and development cases without designing the held-out labels.

Future write scope: backend/app/retrieval/, backend/app/ingestion/, data/sops/, tests/retrieval/, and explicitly allocated retrieval migration files. Request dependency/shared-schema changes from G1/coordinator.

Current write scope: docs/agent-reports/G2-retrieval.md only, inside your assigned worktree. Aim for 700-1100 words. Include decisions, ordered tasks, file scope, dependencies, tests, and risks. Do not commit or implement code. Report the absolute path changed in your final answer.
