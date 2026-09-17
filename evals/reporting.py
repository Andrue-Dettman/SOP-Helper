"""Reproducible reports with explicit missing, failed, and pending denominators."""

from collections import Counter, defaultdict
from .grading import fingerprint, grade
from .suite import TIERS, require

METADATA_FIELDS = {
    "run_id", "captured_at", "tier", "commit", "working_tree_sha256",
    "case_manifest_sha256", "fixtures_sha256", "corpus_revision", "seed_revision",
    "generation_mode", "embedding_mode", "provider", "model", "retrieval_mode",
    "prompt_sha256", "configuration",
}


def index_records(records, allowed_ids, label):
    indexed = {}
    for record in records:
        require(isinstance(record, dict), f"{label}: record must be an object")
        key = record.get("case_id")
        require(key in allowed_ids, f"{label}: unknown or unselected case {key}")
        require(key not in indexed, f"{label}: duplicate case {key}")
        indexed[key] = record
    return indexed


def validate_metadata(metadata, hashes):
    require(METADATA_FIELDS <= metadata.keys(), f"metadata missing fields: {sorted(METADATA_FIELDS - metadata.keys())}")
    require(metadata["tier"] in TIERS, "unknown execution tier")
    require(metadata["generation_mode"] in {"none", "mocked", "live"}, "invalid generation mode")
    require(metadata["embedding_mode"] in {"none", "fixture", "live", "local"}, "invalid embedding mode")
    require(metadata["case_manifest_sha256"] == hashes["cases"], "case manifest hash mismatch")
    require(metadata["fixtures_sha256"] == hashes["fixtures"], "fixtures hash mismatch")
    require(isinstance(metadata["configuration"], dict), "configuration must be an object")
    require(bool(metadata["run_id"]) and bool(metadata["captured_at"]), "missing run identity/time")
    if metadata["tier"] == "live":
        require(metadata["generation_mode"] == "live" and bool(metadata["provider"])
                and bool(metadata["model"]), "live tier requires a named live provider and model")
    elif metadata["tier"] == "mocked":
        require(metadata["generation_mode"] == "mocked", "mocked tier requires mocked generation")
    else:
        require(metadata["generation_mode"] == "none", "component tier cannot claim model generation")


def report(cases, fixtures, observations, reviews, metadata, hashes, split="all"):
    validate_metadata(metadata, hashes)
    tier = metadata["tier"]
    selected = [c for c in cases if tier in c["applicable_tiers"]
                and (split == "all" or c["split"] == split)]
    ids = {c["id"] for c in selected}
    captures = index_records(observations, ids, "observations")
    human = index_records(reviews, ids, "reviews")
    require(set(human) <= set(captures), "review has no matching observation")
    results = [grade(case, captures.get(case["id"]), fixtures, tier, human.get(case["id"])) for case in selected]
    for result in results:
        observation = captures.get(result["case_id"])
        result["observation_sha256"] = fingerprint(observation) if observation is not None else None
    if tier == "live":
        for result in results:
            observation = captures.get(result["case_id"])
            if observation and observation.get("outcome") == "completed":
                calls = observation.get("provider_calls")
                trace = observation.get("trace")
                if (type(calls) is not int or not 1 <= calls <= 3
                        or not isinstance(trace, dict) or trace.get("model_attempts") != calls):
                    result["checks"]["live_provider_evidence"] = {"outcome": "failed", "detail": "Live provider_calls must be 1..3 and agree with trace model_attempts."}
                    result["outcome"] = "failed"
    counts = Counter(r["outcome"] for r in results)
    by_category = {}
    for category in sorted({r["category"] for r in results}):
        rows = [r for r in results if r["category"] == category]
        by_category[category] = {"denominator": len(rows), **dict(Counter(r["outcome"] for r in rows))}
    rates = {}
    for answerable, name in ((True, "answerable_completion"), (False, "uncertainty_completion")):
        rows = [r for r in results if r["answerable"] is answerable]
        n, d = sum(r["outcome"] == "passed" for r in rows), len(rows)
        rates[name] = {"numerator": n, "denominator": d, "rate": n / d if d else None}
    metrics = defaultdict(list)
    for result in results:
        for key, value in result["metrics"].items():
            metrics[key].append(value)
    aggregates = {}
    for key, values in metrics.items():
        if isinstance(values[0], dict):
            n = sum(v["numerator"] for v in values)
            d = sum(v["denominator"] for v in values)
            aggregates[key] = {"numerator": n, "denominator": d, "rate": n / d if d else None,
                               "observed_cases": len(values)}
        else:
            aggregates[key] = {"sum": sum(values), "observed_cases": len(values), "mean": sum(values) / len(values)}
    return {
        "schema_version": 1, "metadata": metadata, "split": split,
        "fixture_binding": fixtures["binding_status"],
        "provenance_gaps": [field for field in ("commit", "working_tree_sha256", "corpus_revision", "seed_revision")
                            if not metadata[field]] + (["prompt_sha256"] if tier != "component" and not metadata["prompt_sha256"] else []),
        "release_accepted": False,
        "release_note": "Scoring captured evidence is not release acceptance. Fixture integration, independent review, and live acceptance remain coordinator responsibilities.",
        "selected_cases": len(selected), "captured_cases": len(captures),
        "outcomes": {key: counts[key] for key in ("passed", "failed", "pending", "missing")},
        "by_category": by_category, "rates": rates, "observed_metrics": aggregates,
        "results": results, "observations": observations, "reviews": reviews,
    }


def markdown_report(result):
    lines = ["# Evaluation capture report", "", f"Run: `{result['metadata']['run_id']}`; tier: `{result['metadata']['tier']}`; split: `{result['split']}`.",
             "", result["release_note"], "", f"Fixture binding: `{result['fixture_binding']}`.", "",
             "| Category | Selected | Passed | Failed | Pending | Missing |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for category, counts in result["by_category"].items():
        lines.append(f"| {category} | {counts['denominator']} | {counts.get('passed', 0)} | {counts.get('failed', 0)} | {counts.get('pending', 0)} | {counts.get('missing', 0)} |")
    lines.extend(["", "Missing and pending cases remain in completion denominators. Observed-only metrics in the JSON report are not whole-suite completion rates.", "", "## Cases needing attention", ""])
    for case in result["results"]:
        if case["outcome"] != "passed":
            checks = ", ".join(name for name, check in case["checks"].items() if check["outcome"] != "passed")
            lines.append(f"- `{case['case_id']}`: {case['outcome']}" + (f" ({checks})" if checks else ""))
    return "\n".join(lines) + "\n"
