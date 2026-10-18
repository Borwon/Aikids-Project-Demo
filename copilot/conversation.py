"""Customer conversation thread for a case.

Built only from data already in the case object: each entry in `contacts[]`
becomes an inbound customer message (channel + time + summary), and a logged
response becomes a system marker (the dataset stores the response timestamp,
not its text, so no reply text is invented). Staff replies typed in the demo are
appended as outbound messages that are queued locally and never transmitted.
"""

from __future__ import annotations


def build_thread(case: dict, queued: list[dict] | None = None) -> list[dict]:
    items: list[dict] = []

    for c in sorted(case.get("contacts", []), key=lambda x: x.get("contact_at", "") or ""):
        items.append({
            "kind": "customer",
            "ts": c.get("contact_at", ""),
            "channel": c.get("channel") or c.get("contact_category") or "",
            "text": c.get("message_summary", ""),
            "sentiment": c.get("sentiment_label", ""),
        })
        if str(c.get("response_sent_at") or "").strip():
            staff = str(c.get("responded_by_staff_id") or "").strip()
            items.append({
                "kind": "system",
                "ts": c.get("response_sent_at", ""),
                "text": f"Reply sent by {staff} — reply text not stored in this dataset"
                        if staff else "Reply sent — reply text not stored in this dataset",
                "staff_id": staff,
            })

    for q in queued or []:
        items.append({
            "kind": "staff",
            "ts": q.get("ts", ""),
            "channel": q.get("channel", ""),
            "text": q.get("text", ""),
            "staff_id": q.get("staff_id", ""),
            "sent": False,
        })

    items.sort(key=lambda x: x.get("ts") or "")
    return items
