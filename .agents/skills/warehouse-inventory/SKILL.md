---
name: warehouse-inventory
description: Implement a fictional, deterministic parts and one-level bill-of-materials database with read-only stock and build-readiness tools.
---

Model canonical IDs, display names/aliases, integer unit stock, assemblies, BOM lines, and snapshot metadata. Use one warehouse and one-level BOMs initially. Add uniqueness/foreign-key/check constraints. Unknown stock is not zero, and an empty BOM is not ready.

Calculate requirements and shortages using domain code and parameterized queries, never model-generated SQL. Validate positive integer requested quantities; reject fractional, negative, zero, and excessively large requests according to the agreed bound. Aggregate duplicate component use consistently or reject duplicate BOM lines at ingestion.

Evaluate every component from the same database snapshot. Ambiguous aliases require selection. Read-only runtime credentials and separate seed/migration credentials keep the public demo immutable. Seeds are deterministic and explicitly fictional; reset targets only this demo's database.

Test exact stock, one short component, unknown parts, missing stock, empty BOM, duplicate/invalid data, and snapshot consistency. Supply independently understandable seed examples for other workers; do not derive evaluation expectations by invoking the production calculator.
