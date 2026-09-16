# Project instructions

## Current phase

This turn is planning and agent setup only. Produce the assigned implementation plan; do not implement the application, install dependencies, provision services, or deploy. Do not spawn additional agents. The coordinator will combine six independent reports.

## Context to load

Read `docs/PROJECT_BRIEF.md`, `docs/CONTRACTS.md`, and your assigned file under `agents/prompts/`. Load only the role-specific `SKILL.md` named there. Claude can read those Markdown skills directly; no global skill installation is required. `CLAUDE.md` points to this file.

## Ownership and collaboration

- Work only inside the absolute worktree assigned by the coordinator. Always set the working directory explicitly for commands.
- In the planning phase, OpenAI workers may edit only their assigned file in `docs/agent-reports/`. Claude workers return their report as their final response for the coordinator to save.
- Do not commit, change branches, edit other worktrees, or change shared contracts. Identify proposed contract changes in the report.
- For later implementation, use the write scopes in `agents/ROSTER.md`. Shared manifests and contract changes go through the coordinator.
- Distinguish proposed checks from checks actually run, and intended behavior from implemented behavior.
- Do not access employer systems, private SOPs, credentials, or any unrelated user files.

## Product invariants

Fictional data only. A small working application, not an enterprise platform. The six coding agents are development workers; the product itself uses one bounded assistant workflow. Database calculations run in deterministic code. No model-generated SQL or write tools. Missing information is different from zero stock. Preserve required steps and warnings when simplifying sample procedures. Backend model keys never enter the frontend.
