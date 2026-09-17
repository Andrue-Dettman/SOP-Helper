"""Render facts from validated evidence; model output cannot replace required text."""
import hashlib
import re
from urllib.parse import quote, urlencode

from app.contracts.models import (
    BuildResult, Citation, Prerequisite, ProcedureResult, ProcedureStep, SearchResult,
    SourceIdentity, WarningBlock,
)
from app.providers.base import Draft


def source_uri(document_id: str, version: str, section_id: str) -> str:
    return f"/api/sops/{quote(document_id, safe='')}/sections/{quote(section_id, safe='')}?{urlencode({'version': version})}"


def stable_id(*parts: str) -> str:
    return hashlib.sha256("\x00".join(parts).encode()).hexdigest()[:24]


def procedure_evidence(result: SearchResult) -> tuple[ProcedureResult, list[Citation]]:
    procedure = ProcedureResult(state=result.status)
    if result.status != "ok":
        return procedure, []
    citations, seen_sources, seen_citations = [], set(), set()
    seen_steps, seen_warnings, seen_prerequisites = {}, {}, {}
    for passage in result.passages:
        identity = (passage.document_id, passage.version, passage.section_id)
        cid = "cite-" + stable_id(*identity, passage.text)
        if cid not in seen_citations:
            seen_citations.add(cid)
            citations.append(Citation(citation_id=cid, document_id=passage.document_id,
                                  version=passage.version, section_id=passage.section_id,
                                  title=passage.title, quoted_text=passage.text,
                                  source_uri=source_uri(*identity)))
        if identity not in seen_sources:
            seen_sources.add(identity)
            procedure.sources.append(SourceIdentity(document_id=passage.document_id,
                                                version=passage.version, section_id=passage.section_id,
                                                is_current=passage.is_current))
        ids = {s.step_id: "step-" + stable_id(*identity, s.step_id) for s in passage.steps}
        for step in passage.steps:
            sid = ids[step.step_id]
            if sid in seen_steps:
                if seen_steps[sid].text != step.text:
                    raise ValueError("Conflicting text for the same immutable source step")
                if cid not in seen_steps[sid].citation_ids:
                    seen_steps[sid].citation_ids.append(cid)
            else:
                value = ProcedureStep(step_id=sid, text=step.text, ordinal=len(procedure.steps) + 1, citation_ids=[cid])
                seen_steps[sid] = value
                procedure.steps.append(value)
        for warning in passage.warnings:
            wid = "warning-" + stable_id(*identity, warning.warning_id)
            value = WarningBlock(warning_id=wid, text=warning.text,
                                 applies_to_step_ids=[ids[x] for x in warning.applies_to_step_ids], citation_ids=[cid])
            if wid in seen_warnings:
                previous = seen_warnings[wid]
                if (previous.text, previous.applies_to_step_ids) != (value.text, value.applies_to_step_ids):
                    raise ValueError("Conflicting immutable source warning")
            else:
                seen_warnings[wid] = value
                procedure.warnings.append(value)
        for prerequisite in passage.prerequisites:
            pid = "pre-" + stable_id(*identity, prerequisite.id)
            if pid in seen_prerequisites:
                if seen_prerequisites[pid] != prerequisite.text:
                    raise ValueError("Conflicting immutable source prerequisite")
            else:
                seen_prerequisites[pid] = prerequisite.text
                procedure.prerequisites.append(Prerequisite(id=pid, text=prerequisite.text, citation_ids=[cid]))
    return procedure, citations


def apply_explanations(procedure: ProcedureResult, citations: list[Citation], draft: Draft) -> bool:
    """Conservative structural checks; semantic support still needs human evaluation."""
    known = {c.citation_id for c in citations}
    steps = {s.step_id: s for s in procedure.steps}
    valid = not (set(draft.answer_citation_ids) - known)
    proposed = {}
    for explanation in draft.explanations:
        step = steps.get(explanation.step_id)
        if step is None or explanation.step_id in proposed:
            valid = False
            continue
        # Never display markup/links, new numeric quantities, or a reversed obligation.
        text = explanation.text
        numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", text))
        source_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", step.text))
        unsafe = re.search(r"https?://|<[^>]+>|\]\(|\b(?:skip|ignore|omit|instead)\b", text, re.I)
        reversed_obligation = re.search(r"\b(?:not|never|must|stop)\b", step.text, re.I) and not re.search(r"\b(?:not|never|must|stop)\b", text, re.I)
        if numbers - source_numbers or unsafe or reversed_obligation:
            valid = False
        proposed[explanation.step_id] = text
    if valid:
        for step_id, text in proposed.items():
            steps[step_id].explanation = text
    else:
        procedure.fallback_used = True
    return valid


def render_inventory(result) -> str:
    if result is None:
        return ""
    if result.state == "unavailable":
        return "Inventory is temporarily unavailable."
    if result.state in {"ambiguous", "not_found"}:
        return "The requested inventory item could not be uniquely resolved."
    snapshot = f"Fictional snapshot: {result.snapshot.snapshot_id}."
    if isinstance(result, BuildResult):
        readiness = {True: "Ready", False: "Not ready", None: "Readiness unknown"}[result.ready]
        lines = [f"{readiness}: {result.requested_units} units of {result.assembly_id}. {snapshot}"]
        if result.state == "incomplete":
            lines.append("Some inventory or bill-of-materials data is missing.")
        for c in result.components:
            available = "unknown" if c.available is None else str(c.available)
            shortage = "unknown" if c.shortage is None else str(c.shortage)
            lines.append(f"{c.part_id}: required {c.required}; available {available}; shortage {shortage}.")
        return "\n".join(lines)
    return "\n".join([snapshot, *[
        f"{m.label}: {'unknown' if m.available is None else m.available} {m.unit} on hand."
        for m in result.matches]])
