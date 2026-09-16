# G3: OpenAI independent evaluation planner

Read AGENTS.md, docs/PROJECT_BRIEF.md, docs/CONTRACTS.md, and .agents/skills/warehouse-evaluation/SKILL.md. This pass is planning only.

Specify a practical evaluation strategy with 60-100 cases, concrete category counts, separate development/held-out groups, independent inventory oracles, and source-support/plain-language review. Give representative cases and scoring definitions. Distinguish component, mocked integration, and live model runs. Propose realistic release criteria as targets, never as achieved outcomes. Challenge metrics that are easy to game. Include failure reporting, reproducibility, injection tests, and portfolio evidence without business KPIs.

Future write scope: evals/, tests/evaluation/, docs/evaluation.md. You own evaluation definitions, not domain service tests or implementations. Coordinate corpus/seed requirements through the coordinator.

Current write scope: docs/agent-reports/G3-evaluation.md only, inside your assigned worktree. Aim for 700-1100 words. Include ordered tasks, dependencies, tests, and risks. Do not commit or implement code. Report the absolute path changed in your final answer.
