---
name: warehouse-delivery
description: Package, verify, and document the standalone demo, coordinating isolated development environments and honest portfolio evidence.
---

Design local startup with Docker Compose and documented native options where useful. Use unique Compose project names, ports, and database volumes per worker; a Git worktree does not isolate services automatically. Coordinate migrations and never reset another worker's database.

Offline tests must not require provider credentials. Live AI functionality must either use configured credentials or explicitly report it is unavailable; never label canned responses as successful live inference. Separate liveness, database readiness, provider configuration, and optional paid smoke checks.

Keep secrets out of git/frontend, scope runtime DB permissions to reads, and expose no model-provided command/SQL execution. Use finite request limits and timeouts for any public demo. Publishing and real employer integration are not included in the current planning task.

Own integration tests and delivery docs, not another worker's module implementation. Define cross-provider review pairs, merge order, reproducible seed/evaluation procedures, and a short demo script. Explain gaps and failures truthfully in the README; include only claims supported by implemented features and actual runs.
