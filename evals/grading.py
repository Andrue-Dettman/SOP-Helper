"""Conservative scoring of captured outputs; never manufactures a product run."""

import hashlib
import json
from .suite import source_key

ALLOWLIST = {"search_procedures", "lookup_stock", "check_build_readiness"}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode("utf-8")).hexdigest()


def typed_equal(actual, expected):
    """Compare exact types so True, 1, and 1.0 cannot substitute for each other."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(typed_equal(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(typed_equal(a, e) for a, e in zip(actual, expected))
    return actual == expected


def inventory_equal(actual, expected):
    if not isinstance(actual, dict):
        return False
    # Component order has no arithmetic meaning. Duplicate/extra rows still fail.
    a, e = dict(actual), dict(expected)
    field = "components" if expected["kind"] == "build" else "matches"
    try:
        a[field] = sorted(a[field], key=lambda row: row["part_id"])
        e[field] = sorted(e[field], key=lambda row: row["part_id"])
    except (KeyError, TypeError):
        return False
    return typed_equal(a, e)


def review_template(case, observation):
    return {
        "case_id": case["id"], "observation_sha256": fingerprint(observation),
        "reviewer": "", "plain_language": None, "factual_claims": None,
        "supported_claims": None, "claims_requiring_citations": None,
        "claims_with_supported_citations": None, "inventory_prose_correct": None,
        "clarification_useful": None, "mandatory_facts": {s: None for s in case["mandatory_facts"]},
        "mandatory_warnings": {s: None for s in case["mandatory_warnings"]},
        "forbidden_actions_absent": {s: None for s in case["forbidden_actions"]},
        "notes": "",
    }


def grade(case, observation, fixtures, tier, review=None):
    result = {"case_id": case["id"], "category": case["category"], "split": case["split"],
              "answerable": case["answerable"], "checks": {}, "metrics": {}}

    def check(name, value, detail=None):
        result["checks"][name] = {"outcome": "pending" if value is None else "passed" if value else "failed"}
        if detail is not None:
            result["checks"][name]["detail"] = detail

    def finish():
        outcomes = [v["outcome"] for v in result["checks"].values()]
        result["outcome"] = "failed" if "failed" in outcomes else "pending" if "pending" in outcomes else "passed"
        return result

    if observation is None:
        result["outcome"] = "missing"
        return result
    if observation.get("outcome") == "skipped":
        check("execution", None, observation.get("reason", "No reason supplied"))
        return finish()
    if observation.get("outcome") != "completed":
        check("execution", False, observation.get("error", "Capture failed or has invalid outcome"))
        return finish()
    check("execution", True)
    response = observation.get("response")
    if not isinstance(response, dict):
        check("response_object", False)
        return finish()
    check("response_object", True)
    if case["input"]["kind"] == "tool" and case["expected_status"] is None:
        check("strict_argument_rejection", response.get("validation_error") is True)
    if case["expected_http_status"] is not None:
        check("http_status", typed_equal(observation.get("http_status"), case["expected_http_status"]),
              {"expected": case["expected_http_status"], "actual": observation.get("http_status")})
    if case["expected_status"] is not None:
        check("status", response.get("status") == case["expected_status"],
              {"expected": case["expected_status"], "actual": response.get("status")})
    if tier != "component" and case["expected_http_status"] != 422:
        required = {"answer", "answer_citation_ids", "status", "citations", "procedure_result",
                    "inventory_result", "clarification", "error", "trace_id", "data_mode"}
        check("response_envelope", required <= response.keys()
              and isinstance(response.get("answer"), str) and bool(response.get("answer", "").strip())
              and response.get("data_mode") == "synthetic"
              and isinstance(response.get("trace_id"), str) and bool(response.get("trace_id")))
        if case["expected_status"] == "temporarily_unavailable":
            error = response.get("error")
            check("explicit_error", isinstance(error, dict) and isinstance(error.get("code"), str)
                  and bool(error.get("code")) and isinstance(error.get("message"), str)
                  and bool(error.get("message")) and type(error.get("retryable")) is bool)
    if case["expected_inventory"] is not None:
        actual = response.get("inventory_result")
        check("inventory_exact", inventory_equal(actual, case["expected_inventory"]),
              {"expected": case["expected_inventory"], "actual": actual})
    elif case["expected_clarification"] and case["expected_clarification"]["kind"] in {"assembly", "quantity", "part"}:
        check("no_premature_inventory", response.get("inventory_result") is None)
    expected_clarification = case["expected_clarification"]
    clarification = response.get("clarification")
    if expected_clarification:
        valid = isinstance(clarification, dict)
        try:
            choices = [v["id"] for v in clarification["choices"]]
            valid = valid and clarification["kind"] == expected_clarification["kind"]
            valid = valid and bool(clarification["question"].strip())
            valid = valid and len(choices) == len(set(choices)) and set(choices) == set(expected_clarification["choice_ids"])
        except (KeyError, TypeError, AttributeError):
            valid = False
        check("clarification", valid)
    else:
        check("clarification_absent", clarification is None)

    sources = {source_key(s): s for s in fixtures["sources"]}
    expected_sources = {source_key(s) for s in case["expected_source_ids"]}
    if tier != "component" and case["expected_http_status"] != 422:
        try:
            citations = response["citations"]
            check("citation_array", isinstance(citations, list))
            citation_ids = [c["citation_id"] for c in citations]
            valid = len(set(citation_ids)) == len(citation_ids) and all(isinstance(c, str) and c for c in citation_ids)
            for citation in citations:
                original = sources.get(source_key(citation))
                quote = citation["quoted_text"]
                valid = valid and original is not None and isinstance(quote, str) and bool(quote.strip())
                if original is not None and isinstance(quote, str):
                    valid = valid and quote in original["text"] and citation["source_uri"] == original["source_uri"]
                    valid = valid and citation["title"] == original["title"]
            check("citation_identity_excerpt", valid)
            referenced = response["answer_citation_ids"]
            procedure = response.get("procedure_result")
            if procedure is not None:
                referenced = referenced + [ref for step in procedure["steps"] for ref in step["citation_ids"]]
            check("citation_references", isinstance(referenced, list)
                  and all(ref in citation_ids for ref in referenced))
            used_sources = {source_key(c) for c in citations if c["citation_id"] in referenced}
            check("expected_sources_cited", expected_sources <= used_sources)
        except (KeyError, TypeError, AttributeError):
            check("citation_structure", False)

    retrieval = observation.get("retrieval")
    if retrieval is not None:
        try:
            ranked = [source_key(s) for s in retrieval["ranked_source_ids"]]
            # k applies to retrieved chunks; do not move a sixth hit into the top five.
            hits = set(ranked[:5])
            expanded = {source_key(s) for s in retrieval["expanded_source_ids"]}
            check("retrieval_source_identity", all(s in sources for s in ranked) and expanded <= sources.keys())
            if expected_sources:
                result["metrics"]["recall_at_5"] = len(hits & expected_sources) / len(expected_sources)
                result["metrics"]["reciprocal_rank"] = next((1 / i for i, s in enumerate(ranked, 1) if s in expected_sources), 0)
                result["metrics"]["complete_context"] = int(expected_sources <= expanded)
                check("required_context", expected_sources <= expanded)
            elif case["category"] == "unsupported_conflict":
                result["metrics"]["false_evidence"] = int(bool(ranked or expanded))
        except (KeyError, TypeError):
            check("retrieval_structure", False)
    elif expected_sources:
        check("retrieval_capture", None)

    if tier != "component":
        trace = observation.get("trace")
        if trace is None:
            check("bounded_trace", None)
        else:
            try:
                attempts = trace["model_attempts"]
                tools = trace["tool_attempts"]
                check("model_budget", type(attempts) is int and 0 <= attempts <= 3)
                check("tool_budget", isinstance(tools, list) and len(tools) <= 6)
                elapsed = trace["elapsed_ms"]
                check("deadline", type(elapsed) in {int, float} and 0 <= elapsed <= 30000)
                check("tool_dispatch", all(type(t["dispatched"]) is bool and
                      (not t["dispatched"] or (t["name"] in ALLOWLIST and t["arguments_valid"] is True)) for t in tools))
                dependencies = trace["dependency_attempts"]
                operation_counts = {}
                retries_valid = True
                for attempt in dependencies:
                    operation = attempt["operation_id"]
                    operation_counts[operation] = operation_counts.get(operation, 0) + 1
                    number = operation_counts[operation]
                    duration = attempt["duration_ms"]
                    retries_valid &= (type(duration) in {int, float} and 0 <= duration <= 10000)
                    retries_valid &= number <= 2 and (number == 1 or attempt["retry_reason"] == "transient")
                check("dependency_attempt_limits", retries_valid)
            except (KeyError, TypeError):
                check("trace_structure", False)
        if review is None:
            check("human_review", None)
        elif (review.get("observation_sha256") != fingerprint(observation)
              or not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip()):
            check("human_review_binding", False)
        else:
            score = review.get("plain_language")
            check("plain_language", None if score is None else type(score) is int and score in {1, 2})
            for field, expectation in (("mandatory_facts", "mandatory_facts"),
                                       ("mandatory_warnings", "mandatory_warnings"),
                                       ("forbidden_actions_absent", "forbidden_actions")):
                values = review.get(field, {})
                if not isinstance(values, dict):
                    check(field + "_structure", False)
                    continue
                for item in case[expectation]:
                    value = values.get(item)
                    check(f"{field}: {item}", None if value is None else value is True)
            if case["expected_inventory"] is not None:
                value = review.get("inventory_prose_correct")
                check("inventory_prose", None if value is None else value is True)
            if expected_clarification:
                value = review.get("clarification_useful")
                check("clarification_useful", None if value is None else value is True)
            for numerator, denominator, metric in (
                ("supported_claims", "factual_claims", "claim_support"),
                ("claims_with_supported_citations", "claims_requiring_citations", "citation_coverage"),
            ):
                n, d = review.get(numerator), review.get(denominator)
                if n is None or d is None:
                    check(metric, None)
                elif type(n) is not int or type(d) is not int or not 0 <= n <= d:
                    check(metric, False)
                elif d == 0:
                    result["metrics"][metric] = {"numerator": 0, "denominator": 0, "rate": None}
                    check(metric, not case["answerable"])
                else:
                    result["metrics"][metric] = {"numerator": n, "denominator": d, "rate": n / d}
                    check(metric, n / d >= .95)
    return finish()
