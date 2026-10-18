"""Customer-conversation thread tests.

Run with pytest:      pytest -q tests/test_conversation.py
Run without pytest:   python tests/test_conversation.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _cases import contact, make_case  # noqa: E402
from copilot.conversation import build_thread  # noqa: E402


def test_thread_orders_customer_messages_and_keeps_channel():
    case = make_case(contacts=[
        contact(contact_id="CT-2", channel="LINE", message_summary="Second message.",
                contact_at="2026-10-03T09:00:00"),
        contact(contact_id="CT-1", channel="Email", message_summary="First message.",
                contact_at="2026-10-02T09:00:00"),
    ])
    thread = build_thread(case)
    customers = [m for m in thread if m["kind"] == "customer"]
    assert [m["text"] for m in customers] == ["First message.", "Second message."]
    assert [m["channel"] for m in customers] == ["Email", "LINE"]


def test_logged_response_becomes_a_system_marker_without_inventing_text():
    case = make_case(contacts=[
        contact(channel="Phone", response_sent_at="2026-10-05T12:00:00",
                responded_by_staff_id="ST-007"),
    ])
    thread = build_thread(case)
    systems = [m for m in thread if m["kind"] == "system"]
    assert len(systems) == 1
    assert systems[0]["staff_id"] == "ST-007"
    assert "not stored" in systems[0]["text"]


def test_queued_staff_replies_are_outbound_and_not_sent():
    case = make_case(contacts=[contact(channel="Email")])
    queued = [{"ts": "2026-10-06T10:00:00", "channel": "Email",
               "text": "We'll follow up shortly.", "staff_id": "ST-003"}]
    thread = build_thread(case, queued)
    staff = [m for m in thread if m["kind"] == "staff"]
    assert len(staff) == 1
    assert staff[0]["sent"] is False
    assert staff[0]["text"] == "We'll follow up shortly."


def test_thread_is_time_ordered_end_to_end():
    case = make_case(contacts=[
        contact(channel="LINE", contact_at="2026-10-02T09:00:00",
                response_sent_at="2026-10-02T15:00:00", responded_by_staff_id="ST-001"),
    ])
    queued = [{"ts": "2026-10-03T08:00:00", "channel": "LINE", "text": "Update sent.", "staff_id": "ST-001"}]
    ts = [m["ts"] for m in build_thread(case, queued)]
    assert ts == sorted(ts)


def test_no_contacts_gives_empty_thread():
    assert build_thread(make_case(contacts=[], latest_contact=None)) == []


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
    print(f"\n{passed}/{len(tests)} conversation tests passed")
    sys.exit(0 if passed == len(tests) else 1)
