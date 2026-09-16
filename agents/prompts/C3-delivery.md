# C3: Claude delivery and integration planner

Read AGENTS.md, docs/PROJECT_BRIEF.md, docs/CONTRACTS.md, agents/ROSTER.md, and .agents/skills/warehouse-delivery/SKILL.md using your read tools. This pass is planning only. Do not create files, run commands, or spawn subagents.

Plan local packaging, CI, isolated databases/ports per worktree, separate offline and live checks, secrets/configuration, and an honest README/demo. Review the six-agent division for ownership conflicts and unnecessary complexity. Propose a dependency graph, cross-provider review pairs, concrete merge order, and acceptance gates. Identify exactly what remains blocked on actual provider credentials during later implementation. Publication and employer integration are future work.

Future write scope: infra/, scripts/, .github/, tests/integration/, .env.example, README.md, docs/demo.md, docs/operations.md. Never take over other workers' application modules. Root contracts and shared configuration changes go through the coordinator.

Return a 700-1100 word Markdown report in your final response, with decisions, ordered tasks, file ownership, dependencies, acceptance tests, and risks. The coordinator will save it to docs/agent-reports/C3-delivery.md. Do not implement the project or claim checks were executed.
