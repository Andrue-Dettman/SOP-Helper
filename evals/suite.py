"""Load and validate versioned, independently authored evaluation artifacts."""

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TIERS = {"component", "mocked", "live"}
STATUSES = {"answered", "needs_clarification", "insufficient_evidence", "temporarily_unavailable"}
ALLOCATION = {
    "procedure": (12, 6), "explanation": (8, 4), "inventory": (12, 6),
    "missing_input_data": (8, 4), "unsupported_conflict": (6, 3),
    "failure_limits": (4, 2), "injection": (6, 3),
}
FIELDS = {
    "id", "group_id", "split", "category", "input", "answerable", "expected_status",
    "expected_http_status", "expected_source_ids", "expected_inventory",
    "expected_clarification", "mandatory_facts", "mandatory_warnings",
    "forbidden_actions", "fixture_id", "applicable_tiers", "notes",
}


def reject_constant(value):
    raise ValueError(f"Non-finite JSON value: {value}")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), parse_constant=reject_constant)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_key(source):
    return tuple(source[field] for field in ("document_id", "version", "section_id"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(cases, fixtures, enforce_allocation=True):
    require(isinstance(cases, list) and bool(cases), "cases must be a nonempty list")
    sources = fixtures["sources"]
    source_ids = [source_key(source) for source in sources]
    require(len(set(source_ids)) == len(source_ids), "duplicate source identity")
    for source in sources:
        require(all(isinstance(v, str) and v for v in source_key(source)), "invalid source identity")
        require(isinstance(source["text"], str) and bool(source["text"]), "empty source")
        require(isinstance(source["source_uri"], str), "missing source URI")
        require(type(source["is_current"]) is bool, "invalid current flag")
    ids, groups, counts = set(), {}, Counter()
    for case in cases:
        require(isinstance(case, dict), "case must be an object")
        label = case.get("id", "<missing>")
        require(set(case) == FIELDS, f"{label}: case fields differ from contracts v1")
        require(isinstance(label, str) and label and label not in ids, f"{label}: duplicate/invalid ID")
        ids.add(label)
        require(case["split"] in {"development", "held_out"}, f"{label}: invalid split")
        require(case["category"] in ALLOCATION, f"{label}: invalid category")
        group = case["group_id"]
        require(isinstance(group, str) and bool(group), f"{label}: missing group")
        require(groups.get(group, case["split"]) == case["split"], f"{label}: group leaks across splits")
        groups[group] = case["split"]
        counts[case["category"], case["split"]] += 1
        require(type(case["answerable"]) is bool, f"{label}: answerable must be boolean")
        require(case["expected_status"] in STATUSES or case["expected_status"] is None,
                f"{label}: invalid status")
        http = case["expected_http_status"]
        require(http is None or (type(http) is int and http in {200, 404, 422, 503, 504}),
                f"{label}: invalid HTTP status")
        require(isinstance(case["input"], dict) and case["input"].get("kind") in {"chat", "tool"},
                f"{label}: invalid input")
        if case["input"]["kind"] == "chat":
            require(isinstance(case["input"].get("request"), dict), f"{label}: missing chat request")
        else:
            require(case["input"].get("name") in {"lookup_stock", "check_build_readiness", "search_procedures"},
                    f"{label}: invalid tool input")
            require(isinstance(case["input"].get("arguments"), dict), f"{label}: missing arguments")
        tiers = case["applicable_tiers"]
        require(isinstance(tiers, list) and bool(tiers) and set(tiers) <= TIERS
                and len(tiers) == len(set(tiers)), f"{label}: invalid tiers")
        require(case["fixture_id"] in fixtures["scenarios"], f"{label}: unknown fixture")
        refs = case["expected_source_ids"]
        require(isinstance(refs, list), f"{label}: source IDs must be a list")
        require(all(set(ref) == {"document_id", "version", "section_id"} for ref in refs),
                f"{label}: invalid source reference")
        require(all(source_key(ref) in source_ids for ref in refs), f"{label}: unknown source")
        require(len(refs) == len({source_key(ref) for ref in refs}), f"{label}: duplicate reference")
        for field in ("mandatory_facts", "mandatory_warnings", "forbidden_actions"):
            values = case[field]
            require(isinstance(values, list) and all(isinstance(v, str) and v for v in values)
                    and len(values) == len(set(values)), f"{label}: invalid {field}")
        clarification = case["expected_clarification"]
        require((clarification is not None) == (case["expected_status"] == "needs_clarification"),
                f"{label}: clarification/status mismatch")
        if clarification is not None:
            require(clarification["kind"] in {"assembly", "part", "quantity", "procedure"},
                    f"{label}: invalid clarification kind")
            require(isinstance(clarification["choice_ids"], list), f"{label}: invalid choices")
        inventory = case["expected_inventory"]
        if inventory is not None:
            require(inventory["kind"] in {"build", "stock"}, f"{label}: invalid inventory kind")
            require(inventory["snapshot"] == fixtures["scenarios"][case["fixture_id"]]["snapshot"],
                    f"{label}: snapshot mismatch")
            if inventory["kind"] == "build":
                require(type(inventory["requested_units"]) is int
                        and 1 <= inventory["requested_units"] <= 10000, f"{label}: invalid quantity")
                require(inventory["ready"] is None or type(inventory["ready"]) is bool,
                        f"{label}: invalid readiness")
                parts = [p["part_id"] for p in inventory["components"]]
                require(len(parts) == len(set(parts)), f"{label}: duplicate oracle component")
                for component in inventory["components"]:
                    for field in ("per_assembly", "required", "available", "shortage"):
                        value = component[field]
                        require((value is None and field in {"available", "shortage"})
                                or (type(value) is int and value >= 0), f"{label}: invalid oracle number")
        require(isinstance(case["notes"], str), f"{label}: missing notes")
    if enforce_allocation:
        for category, (dev, held) in ALLOCATION.items():
            require(counts[category, "development"] == dev
                    and counts[category, "held_out"] == held, f"{category}: allocation mismatch")
    return {"cases": len(cases), "groups": len(groups), "splits": dict(Counter(c["split"] for c in cases))}


def load_suite(cases_path=ROOT / "cases.json", fixtures_path=ROOT / "fixtures.json"):
    cases, fixtures = read_json(cases_path), read_json(fixtures_path)
    validate(cases, fixtures)
    return cases, fixtures
