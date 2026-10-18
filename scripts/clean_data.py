"""Stage 2: clean + flag the raw VisaConnect CSVs.

Nothing is altered -- the flagged files carry the originals plus `flags` /
`has_flag` columns. This module also emits the two derived tables the app
consumes: `issue_log.csv` (one row per detected issue, with evidence) and
`sla_breach_analysis.csv` (per-case SLA comparison).

Run:  python scripts/clean_data.py
In:   data/raw/*.csv
Out:  data/clean/*.csv
"""

from __future__ import annotations

import csv
import os
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
RAW = os.path.join(ROOT, "data", "raw")
CLEAN = os.path.join(ROOT, "data", "clean")

NOW = datetime(2026, 10, 18, 12, 0, 0)

OPEN_STATUSES = {"Submitted", "Documents Pending", "Under Review", "Awaiting Payment", "On Hold"}


def read_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: str, fieldnames, rows) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_dt(value: str):
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def split_list(value: str) -> list[str]:
    return [v for v in (value or "").split(";") if v]


def main() -> None:
    cases = read_csv(os.path.join(RAW, "visa_cases.csv"))
    contacts = read_csv(os.path.join(RAW, "customer_contacts.csv"))
    transport = read_csv(os.path.join(RAW, "transport_bookings.csv"))
    reviews = read_csv(os.path.join(RAW, "customer_reviews.csv"))
    sla_catalog = {r["journey_type"]: r for r in read_csv(os.path.join(RAW, "service_catalog_sla.csv"))}

    # Index children by case_id ---------------------------------------------------
    contacts_by_case: dict[str, list[dict]] = {}
    for c in contacts:
        contacts_by_case.setdefault(c["case_id"], []).append(c)

    transport_by_case: dict[str, dict] = {t["case_id"]: t for t in transport}
    reviews_by_case: dict[str, list[dict]] = {}
    for r in reviews:
        reviews_by_case.setdefault(r["case_id"], []).append(r)

    issue_seq = 0
    issues: list[dict] = []
    sla_rows: list[dict] = []

    def add_issue(case_id, issue_type, field, evidence, confidence):
        nonlocal issue_seq
        issue_seq += 1
        issues.append(
            {
                "issue_id": f"IS-{issue_seq:05d}",
                "case_id": case_id,
                "issue_type": issue_type,
                "field": field,
                "evidence": evidence,
                "confidence": confidence,
                "detected_at": NOW.isoformat(),
            }
        )

    flagged_cases = []
    for case in cases:
        case_id = case["case_id"]
        flags: list[str] = []

        # 1. missing documents -------------------------------------------------
        required = split_list(case["required_documents"])
        received = split_list(case["documents_received"])
        missing = [d for d in required if d not in received]
        if missing:
            flags.append("MISSING_DOCUMENT")
            add_issue(case_id, "MISSING_DOCUMENT", "documents_received",
                      "Missing: " + ", ".join(missing), "confirmed")

        # 2. unassigned owner --------------------------------------------------
        if not case["case_owner_staff_id"].strip():
            flags.append("UNASSIGNED_OWNER")
            add_issue(case_id, "UNASSIGNED_OWNER", "case_owner_staff_id",
                      "case_owner_staff_id is blank", "confirmed")

        # 3. ambiguous / missing required field --------------------------------
        case_contacts = contacts_by_case.get(case_id, [])
        if not case["current_status"].strip():
            flags.append("MISSING_REQUIRED_FIELD")
            add_issue(case_id, "MISSING_REQUIRED_FIELD", "current_status",
                      "current_status is blank", "insufficient")
        if not case_contacts and not case["current_status"].strip():
            flags.append("AMBIGUOUS_CASE")
            add_issue(case_id, "AMBIGUOUS_CASE", "current_status",
                      "No status and no contact history", "insufficient")

        # 4. transport conflict -------------------------------------------------
        booking = transport_by_case.get(case_id)
        if booking:
            vals = {
                booking["itinerary_value"].strip(),
                booking["internal_note_value"].strip(),
            }
            # airport_code is compared on its IATA prefix
            code = booking["airport_code"].strip()
            code_prefix = code.split(" ")[0].strip() if code else ""
            itin_prefix = booking["itinerary_value"].split(" ")[0].strip()
            note_prefix = booking["internal_note_value"].split(" ")[0].strip()
            conflict = len(vals) > 1 or (code_prefix and code_prefix not in {itin_prefix, note_prefix})
            if conflict:
                flags.append("TRANSPORT_CONFLICT")
                add_issue(
                    case_id, "TRANSPORT_CONFLICT", "transport_bookings",
                    f"itinerary='{booking['itinerary_value']}' "
                    f"internal_note='{booking['internal_note_value']}' "
                    f"airport_code='{booking['airport_code']}'",
                    "conflicting",
                )

        # 5. timestamp conflict + SLA ------------------------------------------
        created = parse_dt(case["case_created_at"])
        latest_contact_dt = created
        ts_conflict = False
        for c in case_contacts:
            resp = parse_dt(c["response_sent_at"])
            if resp and created and resp < created:
                ts_conflict = True
            sent = parse_dt(c["contact_at"])
            if sent and (latest_contact_dt is None or sent > latest_contact_dt):
                latest_contact_dt = sent
            if c["sentiment_label"] == "negative":
                flags.append("NEGATIVE_SENTIMENT")
                add_issue(case_id, "NEGATIVE_SENTIMENT", "sentiment_label",
                          f"contact {c['contact_id']}: negative sentiment", "confirmed")
            if sent and not c["response_sent_at"].strip():
                flags.append("UNRESPONDED_CONTACT")
                add_issue(case_id, "UNRESPONDED_CONTACT", "response_sent_at",
                          f"contact {c['contact_id']} has no response", "confirmed")

        if ts_conflict:
            flags.append("STATUS_TIMESTAMP_CONFLICT")
            add_issue(case_id, "STATUS_TIMESTAMP_CONFLICT", "response_sent_at",
                      "a response_sent_at precedes case_created_at", "conflicting")

        # SLA: hours since the most recent customer-originated activity
        sla_target = int(sla_catalog[case["journey_type"]]["sla_target_hours"])
        hours_elapsed = 0.0
        if latest_contact_dt:
            hours_elapsed = round((NOW - latest_contact_dt).total_seconds() / 3600.0, 1)
        sla_breached = case["current_status"] in OPEN_STATUSES and hours_elapsed > sla_target
        if sla_breached:
            flags.append("SLA_BREACH")
            add_issue(case_id, "SLA_BREACH", "sla_target_hours",
                      f"{hours_elapsed}h elapsed vs target {sla_target}h", "confirmed")

        sla_rows.append(
            {
                "case_id": case_id,
                "journey_type": case["journey_type"],
                "sla_target_hours": sla_target,
                "hours_elapsed": hours_elapsed,
                "sla_breached": str(sla_breached).lower(),
                "last_activity_at": latest_contact_dt.isoformat() if latest_contact_dt else "",
            }
        )

        # dedupe flags, keep order
        seen = set()
        deduped = [f for f in flags if not (f in seen or seen.add(f))]
        flagged_cases.append({**case, "flags": ";".join(deduped), "has_flag": str(bool(deduped)).lower()})

    # Flag the child tables too (kept simple: mark rows tied to a flagged case).
    flagged_case_ids = {c["case_id"] for c in flagged_cases if c["has_flag"] == "true"}

    def flag_child(rows, key="case_id"):
        out = []
        for r in rows:
            f = r[key] in flagged_case_ids
            out.append({**r, "flags": "RELATED_CASE_FLAGGED" if f else "", "has_flag": str(f).lower()})
        return out

    write_csv(os.path.join(CLEAN, "visa_cases_flagged.csv"), list(flagged_cases[0].keys()), flagged_cases)
    fc = flag_child(contacts)
    write_csv(os.path.join(CLEAN, "customer_contacts_flagged.csv"), list(fc[0].keys()), fc)
    ft = flag_child(transport)
    write_csv(os.path.join(CLEAN, "transport_bookings_flagged.csv"), list(ft[0].keys()), ft)
    fr = flag_child(reviews)
    write_csv(os.path.join(CLEAN, "customer_reviews_flagged.csv"), list(fr[0].keys()), fr)

    write_csv(
        os.path.join(CLEAN, "issue_log.csv"),
        ["issue_id", "case_id", "issue_type", "field", "evidence", "confidence", "detected_at"],
        issues,
    )
    write_csv(
        os.path.join(CLEAN, "sla_breach_analysis.csv"),
        ["case_id", "journey_type", "sla_target_hours", "hours_elapsed", "sla_breached", "last_activity_at"],
        sla_rows,
    )

    print(f"Flagged {sum(1 for c in flagged_cases if c['has_flag'] == 'true')}/{len(flagged_cases)} cases; "
          f"{len(issues)} issues logged into {CLEAN}")


if __name__ == "__main__":
    main()
