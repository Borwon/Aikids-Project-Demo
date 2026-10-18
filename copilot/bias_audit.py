"""Bias guardrail audit.

Nationality and language are already excluded from the LLM payload, so the
audit exists to *prove* that exclusion holds rather than to patch bias after
the fact. For each sampled case we regenerate the draft with every nationality
and language value swapped in, and assert the non-greeting output is identical.

Output: data/bias_audit.csv (`case_id, variant_field, variant_value, match, diff`)
plus a stats dict the Approval Log screen surfaces as a fairness badge.
"""

from __future__ import annotations

import json

from .draft import generate_draft

NATIONALITIES = ["Thai", "Myanmar", "French", "German", "Other"]
LANGUAGES = ["English", "Thai", "Burmese", "French", "German"]


def canonical(case: dict, draft: dict) -> dict:
    """The part of the output that must be invariant to excluded fields."""
    return {
        "recommended_action": draft["recommended_action"],
        "confidence_overall": draft["confidence_overall"],
        "flags": [[f["issue_type"], f["confidence"], f["note"]] for f in draft["flags"]],
        "draft_message": draft["draft_message"],
        "insufficient_information": draft["insufficient_information"],
    }


def sample_cases(cases: list[dict], n: int) -> list[dict]:
    if len(cases) <= n:
        return list(cases)
    step = max(1, len(cases) // n)
    return cases[::step][:n]


def run_audit(cases: list[dict], n: int = 20) -> tuple[list[dict], dict]:
    sample = sample_cases(cases, n)
    rows: list[dict] = []
    cases_all_pass = 0

    for case in sample:
        baseline = canonical(case, generate_draft(case))
        case_ok = True

        for field, values in (("customer_nationality", NATIONALITIES),
                              ("message_language", LANGUAGES)):
            for value in values:
                variant = {**case, field: value}
                got = canonical(variant, generate_draft(variant))
                match = got == baseline
                case_ok = case_ok and match
                diff = ""
                if not match:
                    diff = json.dumps(
                        {k: [baseline[k], got[k]] for k in baseline if baseline[k] != got[k]},
                        ensure_ascii=False,
                    )[:400]
                rows.append({
                    "case_id": case["case_id"],
                    "variant_field": field,
                    "variant_value": value,
                    "match": "pass" if match else "fail",
                    "diff": diff,
                })
        if case_ok:
            cases_all_pass += 1

    comparisons = len(rows)
    fails = sum(1 for r in rows if r["match"] == "fail")
    stats = {
        "cases_audited": len(sample),
        "cases_all_pass": cases_all_pass,
        "comparisons": comparisons,
        "differences": fails,
        "pass_rate": round(100.0 * (comparisons - fails) / comparisons, 1) if comparisons else 100.0,
    }
    return rows, stats
