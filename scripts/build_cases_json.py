"""Stage 3: join the cleaned tables into a single app-ready `cases.json`.

Reads only the Stage-2 outputs (nothing raw) and produces one object per case:
the case fields, its linked contacts/transport/reviews, its flags (from
issue_log.csv), its SLA numbers, and a pre-baked draft so the static frontend
can render without a live model call.

Run:  python scripts/build_cases_json.py
In:   data/clean/*.csv
Out:  data/cases.json
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)

from copilot.draft import generate_draft  # noqa: E402

CLEAN = os.path.join(ROOT, "data", "clean")
OUT = os.path.join(ROOT, "data", "cases.json")

NOW = datetime(2026, 10, 18, 12, 0, 0)


def read_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def split_list(value: str) -> list[str]:
    return [v for v in (value or "").split(";") if v]


def parse_dt(value: str):
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def main() -> None:
    cases = read_csv(os.path.join(CLEAN, "visa_cases_flagged.csv"))
    contacts = read_csv(os.path.join(CLEAN, "customer_contacts_flagged.csv"))
    transport = read_csv(os.path.join(CLEAN, "transport_bookings_flagged.csv"))
    reviews = read_csv(os.path.join(CLEAN, "customer_reviews_flagged.csv"))
    issues = read_csv(os.path.join(CLEAN, "issue_log.csv"))
    sla = {r["case_id"]: r for r in read_csv(os.path.join(CLEAN, "sla_breach_analysis.csv"))}

    contacts_by_case: dict[str, list[dict]] = {}
    for c in contacts:
        contacts_by_case.setdefault(c["case_id"], []).append(c)
    transport_by_case = {t["case_id"]: t for t in transport}
    reviews_by_case: dict[str, list[dict]] = {}
    for r in reviews:
        reviews_by_case.setdefault(r["case_id"], []).append(r)
    issues_by_case: dict[str, list[dict]] = {}
    for i in issues:
        issues_by_case.setdefault(i["case_id"], []).append(i)

    out = []
    for case in cases:
        cid = case["case_id"]
        case_issues = issues_by_case.get(cid, [])
        case_contacts = sorted(contacts_by_case.get(cid, []), key=lambda c: c["contact_at"])
        latest_contact = case_contacts[-1] if case_contacts else None

        booking = transport_by_case.get(cid)
        transport_obj = None
        if booking:
            transport_obj = {
                "booking_id": booking["booking_id"],
                "itinerary_value": booking["itinerary_value"],
                "internal_note_value": booking["internal_note_value"],
                "airport_code": booking["airport_code"],
                "departure_date": booking["departure_date"],
                "conflict": "TRANSPORT_CONFLICT" in split_list(case["flags"]),
            }

        sla_row = sla.get(cid, {})
        created = parse_dt(case["case_created_at"])
        days_open = round((NOW - created).total_seconds() / 86400.0, 1) if created else 0.0

        obj = {
            "case_id": cid,
            "customer_id": case["customer_id"],
            "customer_nationality": case["customer_nationality"],
            "message_language": case["message_language"],
            "case_owner_staff_id": case["case_owner_staff_id"],
            "current_status": case["current_status"],
            "journey_type": case["journey_type"],
            "destination_country": case["destination_country"],
            "case_created_at": case["case_created_at"],
            "last_customer_update_at": case["last_customer_update_at"],
            "required_documents": split_list(case["required_documents"]),
            "documents_received": split_list(case["documents_received"]),
            "payment_status": case["payment_status"],
            "days_open": days_open,
            "hours_elapsed": float(sla_row.get("hours_elapsed", 0) or 0),
            "sla_target_hours": int(float(sla_row.get("sla_target_hours", 0) or 0)),
            "sla_breached": str(sla_row.get("sla_breached", "false")).lower() == "true",
            "flag_count": len(case_issues),
            "has_conflict": any(i["issue_type"] == "TRANSPORT_CONFLICT" for i in case_issues),
            "flag_types": split_list(case["flags"]),
            "flags": case_issues,
            "contacts": case_contacts,
            "latest_contact": latest_contact,
            "transport": transport_obj,
            "reviews": reviews_by_case.get(cid, []),
        }
        obj["draft"] = generate_draft(obj)
        out.append(obj)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    payload = {
        "generated_at": NOW.isoformat(),
        "case_count": len(out),
        "cases": out,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)

    insufficient = sum(1 for c in out if c["draft"]["insufficient_information"])
    print(f"Wrote {len(out)} cases to {OUT} "
          f"({sum(1 for c in out if c['has_conflict'])} transport conflicts, "
          f"{insufficient} insufficient-information).")


if __name__ == "__main__":
    main()
