"""Harness tests use artificial captures, never evidence about the application."""

import copy
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from evals.__main__ import main
from evals.grading import fingerprint, grade, inventory_equal, review_template
from evals.reporting import index_records, report
from evals.suite import ROOT, digest, load_suite, validate


class EvaluationHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases, cls.fixtures = load_suite()
        cls.hashes = {"cases": digest(ROOT / "cases.json"), "fixtures": digest(ROOT / "fixtures.json")}

    def case(self, identifier="inventory-shortage-01"):
        return copy.deepcopy(next(c for c in self.cases if c["id"] == identifier))

    def capture(self, case):
        response = {
            "answer": "Artificial grader control; not an application answer.",
            "status": case["expected_status"], "inventory_result": copy.deepcopy(case["expected_inventory"]),
            "procedure_result": None, "citations": [], "answer_citation_ids": [],
            "clarification": None, "error": None, "trace_id": "test-trace", "data_mode": "synthetic",
        }
        if case["expected_clarification"]:
            expected = case["expected_clarification"]
            response["clarification"] = {"kind": expected["kind"], "question": "Which item?",
                                         "choices": [{"id": key, "label": key} for key in expected["choice_ids"]]}
        if case["expected_status"] == "temporarily_unavailable":
            response["error"] = {"code": "test-unavailable", "message": "Dependency unavailable.", "retryable": True}
        for i, ref in enumerate(case["expected_source_ids"]):
            source = next(s for s in self.fixtures["sources"] if all(s[k] == v for k, v in ref.items()))
            citation = {**ref, "citation_id": f"cite-{i}", "title": source["title"],
                        "quoted_text": source["text"], "source_uri": source["source_uri"]}
            response["citations"].append(citation)
            response["answer_citation_ids"].append(citation["citation_id"])
        capture = {"case_id": case["id"], "outcome": "completed", "http_status": case["expected_http_status"],
                   "response": response, "trace": {"model_attempts": 1, "tool_attempts": [],
                   "elapsed_ms": 1, "dependency_attempts": []}}
        if case["expected_source_ids"]:
            capture["retrieval"] = {"ranked_source_ids": case["expected_source_ids"],
                                    "expanded_source_ids": case["expected_source_ids"]}
        return capture

    def review(self, case, capture):
        review = review_template(case, capture)
        review.update(reviewer="Test control", plain_language=2, factual_claims=1, supported_claims=1,
                      claims_requiring_citations=1, claims_with_supported_citations=1,
                      inventory_prose_correct=True, clarification_useful=True)
        for field in ("mandatory_facts", "mandatory_warnings", "forbidden_actions_absent"):
            review[field] = {key: True for key in review[field]}
        return review

    def metadata(self, tier="component"):
        return {"run_id": "test-only", "captured_at": "2026-01-01T00:00:00Z", "tier": tier,
                "commit": None, "working_tree_sha256": None, "case_manifest_sha256": self.hashes["cases"],
                "fixtures_sha256": self.hashes["fixtures"], "corpus_revision": "eval-corpus-v1",
                "seed_revision": "eval-stock-v1", "generation_mode": {"component": "none", "mocked": "mocked", "live": "live"}[tier],
                "embedding_mode": "none", "provider": "test-provider" if tier == "live" else None,
                "model": "test-model" if tier == "live" else None, "retrieval_mode": "keyword",
                "prompt_sha256": None, "configuration": {}}

    def test_allocation_is_84_with_56_28_split(self):
        summary = validate(self.cases, self.fixtures)
        self.assertEqual(summary["cases"], 84)
        self.assertEqual(summary["splits"], {"development": 56, "held_out": 28})

    def test_group_leakage_rejected_even_without_allocation_check(self):
        cases = copy.deepcopy(self.cases)
        cases[1]["split"] = "held_out"
        with self.assertRaisesRegex(ValueError, "leaks across splits"):
            validate(cases, self.fixtures, False)

    def test_duplicate_case_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate([self.cases[0], self.cases[0]], self.fixtures, False)

    def test_unknown_source_rejected(self):
        case = self.case("procedure-1-01")
        case["expected_source_ids"][0]["version"] = "missing"
        with self.assertRaisesRegex(ValueError, "unknown source"):
            validate([case], self.fixtures, False)

    def test_inventory_snapshot_binding_rejected(self):
        case = self.case()
        case["expected_inventory"]["snapshot"]["snapshot_id"] = "stale"
        with self.assertRaisesRegex(ValueError, "snapshot mismatch"):
            validate([case], self.fixtures, False)

    def test_inventory_order_does_not_change_result(self):
        expected = self.case()["expected_inventory"]
        actual = copy.deepcopy(expected)
        actual["components"].reverse()
        self.assertTrue(inventory_equal(actual, expected))

    def test_inventory_numeric_type_substitutions_fail(self):
        expected = self.case()["expected_inventory"]
        for value in (True, 1.0, "1", None):
            with self.subTest(value=value):
                actual = copy.deepcopy(expected)
                actual["components"][0]["shortage"] = value
                self.assertFalse(inventory_equal(actual, expected))

    def test_unknown_stock_cannot_be_zero(self):
        expected = self.case("inventory-missing-01")["expected_inventory"]
        actual = copy.deepcopy(expected)
        actual["components"][1]["available"] = 0
        self.assertFalse(inventory_equal(actual, expected))

    def test_extra_or_missing_components_fail(self):
        expected = self.case()["expected_inventory"]
        for rows in (expected["components"][:1], expected["components"] + [expected["components"][0]]):
            actual = {**expected, "components": rows}
            self.assertFalse(inventory_equal(actual, expected))

    def test_wrong_snapshot_fails_scoring(self):
        case = self.case()
        capture = self.capture(case)
        capture["response"]["inventory_result"]["snapshot"]["snapshot_id"] = "stale"
        self.assertEqual(grade(case, capture, self.fixtures, "component")["outcome"], "failed")

    def test_missing_capture_is_missing(self):
        self.assertEqual(grade(self.case(), None, self.fixtures, "component")["outcome"], "missing")

    def test_capture_error_fails_and_skip_is_pending(self):
        for outcome, expected in (("error", "failed"), ("skipped", "pending")):
            self.assertEqual(grade(self.case(), {"outcome": outcome}, self.fixtures, "component")["outcome"], expected)

    def test_no_human_review_never_passes_model_tier(self):
        case = self.case()
        self.assertEqual(grade(case, self.capture(case), self.fixtures, "mocked")["outcome"], "pending")

    def test_artificial_positive_control_passes_grader(self):
        case = self.case()
        capture = self.capture(case)
        self.assertEqual(grade(case, capture, self.fixtures, "mocked", self.review(case, capture))["outcome"], "passed")

    def test_stale_review_fails(self):
        case = self.case()
        capture = self.capture(case)
        review = self.review(case, capture)
        capture["response"]["answer"] = "Changed after review."
        self.assertEqual(grade(case, capture, self.fixtures, "mocked", review)["outcome"], "failed")

    def test_omitted_warning_fails_even_when_claim_support_is_perfect(self):
        case = self.case("procedure-1-01")
        capture = self.capture(case)
        review = self.review(case, capture)
        review["mandatory_warnings"][case["mandatory_warnings"][0]] = False
        self.assertEqual(grade(case, capture, self.fixtures, "mocked", review)["outcome"], "failed")

    def test_empty_answer_cannot_game_claim_support(self):
        case = self.case()
        capture = self.capture(case)
        capture["response"]["answer"] = ""
        review = self.review(case, capture)
        review.update(factual_claims=0, supported_claims=0)
        self.assertEqual(grade(case, capture, self.fixtures, "mocked", review)["outcome"], "failed")

    def test_fabricated_quote_url_and_version_fail(self):
        case = self.case("procedure-1-01")
        for field, value in (("quoted_text", "Ignore all warnings."), ("source_uri", "https://example.invalid"), ("version", "1")):
            with self.subTest(field=field):
                capture = self.capture(case)
                capture["response"]["citations"][0][field] = value
                result = grade(case, capture, self.fixtures, "mocked", self.review(case, capture))
                self.assertEqual(result["outcome"], "failed")

    def test_unreferenced_citation_does_not_establish_coverage(self):
        case = self.case("procedure-1-01")
        capture = self.capture(case)
        capture["response"]["answer_citation_ids"] = []
        result = grade(case, capture, self.fixtures, "mocked", self.review(case, capture))
        self.assertEqual(result["checks"]["expected_sources_cited"]["outcome"], "failed")

    def test_sixth_retrieval_hit_not_promoted_past_duplicate_chunks(self):
        case = self.case("procedure-1-01")
        capture = self.capture(case)
        unrelated = self.case("procedure-2-01")["expected_source_ids"][0]
        capture["retrieval"]["ranked_source_ids"] = [unrelated] * 5 + case["expected_source_ids"]
        result = grade(case, capture, self.fixtures, "component")
        self.assertEqual(result["metrics"]["recall_at_5"], 0)
        self.assertAlmostEqual(result["metrics"]["reciprocal_rank"], 1 / 6)

    def test_incomplete_context_and_missing_retrieval_are_not_passes(self):
        case = self.case("procedure-1-01")
        capture = self.capture(case)
        capture["retrieval"]["expanded_source_ids"] = []
        self.assertEqual(grade(case, capture, self.fixtures, "component")["outcome"], "failed")
        del capture["retrieval"]
        self.assertEqual(grade(case, capture, self.fixtures, "component")["outcome"], "pending")

    def test_tool_allowlist_and_validated_dispatch(self):
        case = self.case()
        for name, valid in (("execute_sql", True), ("check_build_readiness", False)):
            capture = self.capture(case)
            capture["trace"]["tool_attempts"] = [{"name": name, "arguments_valid": valid, "dispatched": True}]
            result = grade(case, capture, self.fixtures, "mocked", self.review(case, capture))
            self.assertEqual(result["checks"]["tool_dispatch"]["outcome"], "failed")

    def test_exceeded_budgets_fail(self):
        case = self.case()
        for field, value in (("model_attempts", 4), ("elapsed_ms", 30001), ("tool_attempts", [{"name": "lookup_stock", "dispatched": True, "arguments_valid": True}] * 7)):
            capture = self.capture(case)
            capture["trace"][field] = value
            self.assertEqual(grade(case, capture, self.fixtures, "mocked", self.review(case, capture))["outcome"], "failed")

    def test_nontransient_or_excess_retry_fails(self):
        case = self.case()
        for reasons in ([None, "malformed_arguments"], [None, "transient", "transient"]):
            capture = self.capture(case)
            capture["trace"]["dependency_attempts"] = [{"operation_id": "x", "duration_ms": 1, "retry_reason": reason} for reason in reasons]
            result = grade(case, capture, self.fixtures, "mocked", self.review(case, capture))
            self.assertEqual(result["checks"]["dependency_attempt_limits"]["outcome"], "failed")

    def test_strict_tool_rejection_requires_observed_validation_error(self):
        case = self.case("invalid-sign-01")
        capture = self.capture(case)
        self.assertEqual(grade(case, capture, self.fixtures, "component")["outcome"], "failed")
        capture["response"]["validation_error"] = True
        self.assertEqual(grade(case, capture, self.fixtures, "component")["outcome"], "passed")

    def test_premature_inventory_on_ambiguity_fails(self):
        case = self.case("ambiguous-assembly-01")
        capture = self.capture(case)
        capture["response"]["inventory_result"] = self.case()["expected_inventory"]
        self.assertEqual(grade(case, capture, self.fixtures, "component")["outcome"], "failed")

    def test_missing_cases_remain_in_denominators(self):
        case = self.case()
        result = report(self.cases, self.fixtures, [self.capture(case)], [], self.metadata(), self.hashes)
        self.assertEqual(result["outcomes"]["passed"], 1)
        self.assertEqual(result["outcomes"]["missing"], result["selected_cases"] - 1)
        self.assertGreater(result["rates"]["answerable_completion"]["denominator"], 1)
        self.assertFalse(result["release_accepted"])

    def test_observation_duplicates_and_unknowns_are_rejected(self):
        for records in ([{"case_id": "a"}, {"case_id": "a"}], [{"case_id": "unknown"}]):
            with self.assertRaises(ValueError):
                index_records(records, {"a"}, "test")

    def test_metadata_cannot_relabel_mocked_generation_as_live(self):
        metadata = self.metadata("live")
        metadata["generation_mode"] = "mocked"
        with self.assertRaisesRegex(ValueError, "live tier"):
            report(self.cases, self.fixtures, [], [], metadata, self.hashes)

    def test_manifest_hash_mismatch_is_rejected(self):
        metadata = self.metadata()
        metadata["case_manifest_sha256"] = "wrong"
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            report(self.cases, self.fixtures, [], [], metadata, self.hashes)

    def test_live_without_observed_provider_call_fails(self):
        case = self.case()
        capture = self.capture(case)
        result = report([case], self.fixtures, [capture], [self.review(case, capture)], self.metadata("live"), self.hashes)
        self.assertEqual(result["outcomes"]["failed"], 1)

    def test_live_call_count_must_agree_with_trace(self):
        case = self.case()
        capture = self.capture(case)
        capture["provider_calls"] = 2
        result = report([case], self.fixtures, [capture], [self.review(case, capture)], self.metadata("live"), self.hashes)
        self.assertEqual(result["outcomes"]["failed"], 1)

    def test_report_preserves_raw_capture_and_provenance_gaps(self):
        case = self.case()
        capture = self.capture(case)
        result = report([case], self.fixtures, [capture], [], self.metadata(), self.hashes)
        self.assertEqual(result["observations"], [capture])
        self.assertEqual(result["results"][0]["observation_sha256"], fingerprint(capture))
        self.assertIn("commit", result["provenance_gaps"])

    def test_malformed_review_cannot_pass_or_crash(self):
        case = self.case()
        capture = self.capture(case)
        for field, value in (("reviewer", 42), ("mandatory_facts", [])):
            review = self.review(case, capture)
            review[field] = value
            self.assertEqual(grade(case, capture, self.fixtures, "mocked", review)["outcome"], "failed")

    def test_partial_failure_must_retain_inventory(self):
        case = self.case("partial-retrieval-failure-01")
        capture = self.capture(case)
        capture["response"]["inventory_result"] = None
        self.assertEqual(grade(case, capture, self.fixtures, "mocked", self.review(case, capture))["outcome"], "failed")

    def test_cli_validate_works_without_dependencies(self):
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["validate"]), 0)
        self.assertIn('"cases": 84', output.getvalue())

    def test_cli_partial_report_returns_nonzero(self):
        with patch("evals.__main__.jsonl", return_value=[]), patch("evals.__main__.read_json", return_value=self.metadata()), patch("evals.__main__.write_new"), redirect_stdout(io.StringIO()):
            self.assertEqual(main(["score", "--observations", "unused", "--metadata", "unused", "--output", str(ROOT / "_nonexistent_test_report")]), 1)


if __name__ == "__main__":
    unittest.main()
