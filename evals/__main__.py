"""CLI for suite validation and scoring externally captured results."""

import argparse
import json
from pathlib import Path
from .grading import review_template
from .reporting import index_records, markdown_report, report
from .suite import ROOT, digest, load_suite, read_json, reject_constant, validate


def jsonl(path):
    if path is None:
        return []
    return [json.loads(line, parse_constant=reject_constant)
            for line in Path(path).read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def write_new(path, content):
    """Do not silently replace an earlier evidence artifact."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(content)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "cases.json")
    parser.add_argument("--fixtures", type=Path, default=ROOT / "fixtures.json")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate")
    review = commands.add_parser("review-template")
    review.add_argument("--observations", required=True, type=Path)
    review.add_argument("--output", required=True, type=Path)
    score = commands.add_parser("score")
    score.add_argument("--observations", required=True, type=Path)
    score.add_argument("--reviews", type=Path)
    score.add_argument("--metadata", required=True, type=Path)
    score.add_argument("--split", choices=("all", "development", "held_out"), default="all")
    score.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        cases, fixtures = load_suite(args.cases, args.fixtures)
        hashes = {"cases": digest(args.cases), "fixtures": digest(args.fixtures)}
        if args.command == "validate":
            print(json.dumps({**validate(cases, fixtures), "hashes": hashes,
                              "binding_status": fixtures["binding_status"]}, indent=2))
            return 0
        observations = jsonl(args.observations)
        if args.command == "review-template":
            captures = index_records(observations, {c["id"] for c in cases}, "observations")
            forms = [review_template(c, captures[c["id"]]) for c in cases
                     if c["id"] in captures and captures[c["id"]].get("outcome") == "completed"]
            write_new(args.output, "".join(json.dumps(form, ensure_ascii=False) + "\n" for form in forms))
            print(f"Wrote {len(forms)} unscored human review forms.")
            return 0
        result = report(cases, fixtures, observations, jsonl(args.reviews), read_json(args.metadata), hashes, args.split)
        json_path, markdown_path = args.output.with_suffix(".json"), args.output.with_suffix(".md")
        if json_path.exists() or markdown_path.exists():
            raise ValueError("Report path already exists; choose a new run name")
        write_new(json_path, json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        write_new(markdown_path, markdown_report(result))
        print(json.dumps({"selected_cases": result["selected_cases"], "outcomes": result["outcomes"]}))
        # A partial or failed capture can never produce a green CI exit status.
        return 0 if result["selected_cases"] and result["outcomes"]["passed"] == result["selected_cases"] else 1
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f"Evaluation input error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
