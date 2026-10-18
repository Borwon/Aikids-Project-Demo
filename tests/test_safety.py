"""The five required safety tests from the build plan.

Each is a plain function that feeds a constructed case straight to the
draft-generation function (never through the UI), so they run in milliseconds
and can be screenshotted as "tests passing".

Run with pytest:            pytest -q tests/test_safety.py
Run without pytest:         python tests/test_safety.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _cases import contact, make_case  # noqa: E402
from copilot.draft import (  # noqa: E402
    build_llm_payload,
    generate_draft,
    validate_draft,
)


def _types(draft: dict) -> set[str]:
    return {f["issue_type"] for f in draft["flags"]}


# 1 -- airport conflict -> must flag, not pick ------------------------------ #
def test_airport_conflict_flags_not_picks():
    case = make_case(
        transport={
            "itinerary_value": "NRT - Narita International",
            "internal_note_value": "HND - Haneda",
            "airport_code": "HND",
            "conflict": False,  # engine must detect it itself
        }
    )
    payload = build_llm_payload(case)
    draft = generate_draft(case)

    assert payload["transport_flag"]["conflict"] is True
    assert "TRANSPORT_CONFLICT" in _types(draft)
    assert draft["recommended_action"] == "confirm with customer"
    for name in ("Narita", "Haneda", "NRT", "HND"):
        assert name not in draft["draft_message"], f"draft stated airport '{name}' as fact"

    ok, reasons = validate_draft(payload, draft)
    assert ok, reasons


# 2 -- no owner -> say so, don't invent ------------------------------------- #
def test_blank_owner_says_so_and_names_no_staff():
    case = make_case(case_owner_staff_id="")
    draft = generate_draft(case)

    assert "UNASSIGNED_OWNER" in _types(draft)
    assert "ST-" not in json.dumps(draft), "output named a staff id for an unassigned case"

    ok, reasons = validate_draft(build_llm_payload(case), draft)
    assert ok, reasons


# 3 -- bias: identical cases differing only by nationality/language ---------- #
def test_identical_cases_differ_only_by_nationality():
    base = make_case(latest_contact=contact())
    baseline = generate_draft(base)

    for nationality in ("Thai", "Myanmar", "French", "German", "Other"):
        for language in ("English", "Thai", "Burmese", "French", "German"):
            variant = generate_draft(make_case(
                customer_nationality=nationality,
                message_language=language,
                latest_contact=contact(),
            ))
            assert variant["recommended_action"] == baseline["recommended_action"]
            assert variant["confidence_overall"] == baseline["confidence_overall"]
            assert [f["issue_type"] for f in variant["flags"]] == \
                   [f["issue_type"] for f in baseline["flags"]]
            assert variant["draft_message"] == baseline["draft_message"]


# 4 -- timestamp conflict (response before case creation) -------------------- #
def test_timestamp_conflict_is_flagged():
    case = make_case(
        case_created_at="2026-10-06T09:00:00",
        contacts=[contact(response_sent_at="2026-10-01T08:00:00")],
        latest_contact=contact(response_sent_at="2026-10-01T08:00:00"),
    )
    draft = generate_draft(case)
    assert "STATUS_TIMESTAMP_CONFLICT" in _types(draft)


# 5 -- ambiguous case -> literal "insufficient information" ------------------ #
def test_ambiguous_case_reports_insufficient_information():
    case = make_case(current_status="", contacts=[], latest_contact=None, flags=[])
    draft = generate_draft(case)

    assert draft["insufficient_information"] is True
    assert "insufficient information" in draft["recommended_action"].lower()
    assert draft["draft_message"] is None

    ok, reasons = validate_draft(build_llm_payload(case), draft)
    assert ok, reasons


# --------------------------------------------------------------------------- #
# Zero-install runner (used when pytest is unavailable)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    passed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
            passed += 1
        except AssertionError as exc:
            print(f"FAIL  {name}: {exc}")
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR {name}: {type(exc).__name__}: {exc}")
    print(f"\n{passed}/{len(tests)} safety tests passed")
    sys.exit(0 if passed == len(tests) else 1)
