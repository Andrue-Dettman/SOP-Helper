---
name: warehouse-evaluation
description: Specify and run independent retrieval, inventory, and response-quality evaluation for the fictional warehouse assistant.
---

Use independently authored expected outputs. Keep related questions and paraphrases in one split. Freeze held-out questions before tuning and separate corpus access from held-out answer labels.

Score retrieval against labeled relevant sections, citations against exact source identity plus human-checked support, and inventory against explicit expected quantities. Measure answering behavior on answerable cases alongside refusal on unanswerable ones so an assistant cannot score well by refusing everything.

Use deterministic grading for arithmetic, schema, and source existence; use a written human rubric for simplification, warning retention, and unsupported statements. An LLM judge is optional and needs calibration. Include ambiguity, missing rows, empty BOMs, provider timeouts, and document instruction injection.

Tag offline fixture runs separately from live provider runs. Record seed/corpus versions, commit, retrieval settings, prompts/model configuration, denominators, failures, and latency when measured. Publish genuine results and limitations only. Do not infer savings, accessibility outcomes, or model-training experience.
