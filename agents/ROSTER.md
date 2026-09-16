# Six-agent roster

The coordinator maintains the main checkout, final contracts, merge order, and consolidated plan. There are exactly six worker roles, not six runtime agents inside the product.

| ID | Provider | Role | Branch | Worktree directory |
| --- | --- | --- | --- | --- |
| G1 | OpenAI/Codex | API and assistant orchestration | agent/g1-api | work/warehouse-agents/g1-api |
| G2 | OpenAI/Codex | Retrieval and sample SOP ingestion | agent/g2-retrieval | work/warehouse-agents/g2-retrieval |
| G3 | OpenAI/Codex | Evaluation and evidence | agent/g3-evaluation | work/warehouse-agents/g3-evaluation |
| C1 | Claude Code | Inventory and seeded database | agent/c1-inventory | work/warehouse-agents/c1-inventory |
| C2 | Claude Code | Frontend and plain-language experience | agent/c2-frontend | work/warehouse-agents/c2-frontend |
| C3 | Claude Code | Local delivery and integration review | agent/c3-delivery | work/warehouse-agents/c3-delivery |

Worktree paths above are relative to the original task folder, two directories above this repository. Each role has a prompt under `agents/prompts/` and a project skill under `.agents/skills/`. The individual prompts specify exact future code ownership and current report destinations.

OpenAI workers inherit the coordinator's model. Claude workers use the authenticated local CLI's configured default; record the actual model if available rather than assuming a particular model. No permissions bypass is required.

## Shared-file rule

G1 proposes changes to backend dependencies, application bootstrap, and shared schemas. C2 owns frontend package manifests. C3 owns delivery configuration after contracts settle. All other cross-scope changes are requested through the coordinator. Each branch gets the coordinator's approved baseline before implementation; do not merge other workers directly.
