"""Case-chat tests: every hard requirement has an assertion.

Run with pytest:            pytest -q tests/test_chat.py
Run without pytest:         python tests/test_chat.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _cases import contact, make_case  # noqa: E402
from copilot.chat import (  # noqa: E402
    answer,
    build_chat_context,
    build_system_prompt,
    validate_chat_reply,
)


def _conflict_case(**over):
    base = make_case(
        transport={
            "itinerary_value": "MEL - Melbourne",
            "internal_note_value": "HND - Haneda",
            "airport_code": "SYD",
            "conflict": True,
        },
    )
    base.update(over)
    return base


# 1 -- scoped to one case ---------------------------------------------------- #
def test_other_case_is_refused_as_out_of_scope():
    case = make_case(case_id="VC-00004")
    reply = answer(case, "What about VC-00001 — what's its status?")
    assert "VC-00004" in reply
    assert "VC-00001" in reply
    assert "open" in reply.lower()


# 2 -- read-only refusal ----------------------------------------------------- #
def test_send_approve_rebook_are_refused_pointing_at_approve_button():
    for case, q in [
        (make_case(), "Please send this to the customer"),
        (make_case(), "approve it and move on"),
        (_conflict_case(), "go ahead and rebook to HND"),
    ]:
        reply = answer(case, q)
        assert "Approve button" in reply, (q, reply)
        low = reply.lower()
        for banned in ("has been sent", "i have sent", "booking confirmed", "i have rebooked"):
            assert banned not in low
        ok, reasons = validate_chat_reply(case, q, reply)
        assert ok, reasons


# 3 -- never pick an airport on conflict ------------------------------------- #
def test_transport_conflict_states_both_and_asks_for_confirmation():
    case = _conflict_case()
    reply = answer(case, "Which airport is the pickup from?")
    assert "MEL - Melbourne" in reply
    assert "HND - Haneda" in reply
    low = reply.lower()
    assert "confirm" in low or "ยืนยัน" in reply
    # never assert a single airport as the answer
    assert "is MEL - Melbourne" not in reply
    assert "is HND - Haneda" not in reply
    ok, reasons = validate_chat_reply(case, "Which airport is the pickup from?", reply)
    assert ok, reasons


# 4 -- never invent an owner ------------------------------------------------- #
def test_blank_owner_says_no_owner_and_names_no_staff():
    case = make_case(case_owner_staff_id="")
    reply = answer(case, "Who owns this case?")
    assert "No owner is assigned" in reply
    import re
    assert not re.search(r"\bST-\d{2,4}\b", reply)
    ok, reasons = validate_chat_reply(case, "Who owns this case?", reply)
    assert ok, reasons


def test_named_owner_is_reported_verbatim():
    case = make_case(case_owner_staff_id="ST-007")
    reply = answer(case, "who is the assigned owner?")
    assert "ST-007" in reply


# 5 -- insufficient information instead of guessing -------------------------- #
def test_unknown_fact_says_insufficient_information():
    reply = answer(make_case(), "What is the applicant's date of birth?")
    assert "insufficient information" in reply.lower()


def test_blank_status_case_reports_insufficient_information():
    case = make_case(current_status="", contacts=[], latest_contact=None)
    reply = answer(case, "What's the status?")
    assert "insufficient information" in reply.lower()


# 6 -- excluded fields never included ---------------------------------------- #
def test_context_excludes_nationality_and_language_everywhere():
    case = make_case(
        customer_nationality="Myanmar",
        message_language="Burmese",
        contacts=[contact(message_language="Burmese")],
        latest_contact=contact(message_language="Burmese"),
    )
    ctx = build_chat_context(case)
    blob = json.dumps(ctx, ensure_ascii=False)

    assert "customer_nationality" not in ctx
    assert "message_language" not in ctx
    assert "Myanmar" not in blob
    assert "Burmese" not in blob
    # nested objects too
    assert all("message_language" not in c for c in ctx["contacts"])
    assert "message_language" not in ctx["latest_contact"]

    prompt = build_system_prompt(case)
    assert "Myanmar" not in prompt and "Burmese" not in prompt


# 7 -- channel-aware, never invents a channel -------------------------------- #
def test_last_contact_channel_is_answered_from_data():
    c = contact(channel="LINE", message_summary="Resent the acceptance letter.",
                sentiment_label="neutral", contact_at="2026-10-02T09:00:00")
    case = make_case(contacts=[c], latest_contact=c)
    reply = answer(case, "ลูกค้าติดต่อมาทางไหนล่าสุด")
    assert "LINE" in reply
    assert "Facebook" not in reply


def test_facebook_is_never_claimed():
    c = contact(channel="Email")
    case = make_case(contacts=[c], latest_contact=c)
    reply = answer(case, "Did they contact us via Facebook?")
    assert "no Facebook" in reply
    assert "Email" in reply


def test_contact_question_without_contacts_is_insufficient():
    case = make_case(contacts=[], latest_contact=None)
    reply = answer(case, "Which channel did they use?")
    assert "insufficient information" in reply.lower()


# validator catches LLM-style violations ------------------------------------- #
def test_validator_catches_conflict_pick_and_fabrications():
    case = _conflict_case(case_owner_staff_id="")
    ok, reasons = validate_chat_reply(case, "which airport?", "The airport is MEL - Melbourne.")
    assert not ok and reasons

    ok, reasons = validate_chat_reply(
        case, "which airport?",
        "MEL - Melbourne and HND - Haneda differ but please confirm.")
    assert ok, reasons

    ok, reasons = validate_chat_reply(make_case(), "send it", "I have sent the message to the customer.")
    assert not ok and reasons

    ok, reasons = validate_chat_reply(
        make_case(case_owner_staff_id=""), "who owns it?", "It is handled by ST-004.")
    assert not ok and reasons


def test_deterministic_answers_are_flagged_safe_by_validator():
    cases = [
        (_conflict_case(), "Which airport?"),
        (make_case(case_owner_staff_id=""), "Who owns this?"),
        (make_case(), "What are the flags?"),
        (make_case(), "Is the SLA breached?"),
        (make_case(), "What's the destination?"),
    ]
    for case, q in cases:
        reply = answer(case, q)
        ok, reasons = validate_chat_reply(case, q, reply)
        assert ok, (q, reasons)


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
    print(f"\n{passed}/{len(tests)} chat tests passed")
    sys.exit(0 if passed == len(tests) else 1)
