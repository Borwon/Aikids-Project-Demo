"""Generate the synthetic VisaConnect dataset (Stage 1: raw data).

VisaConnect is fictional, so the four operational CSVs plus the two reference
files are generated here with a fixed seed. The generator deliberately plants
the edge cases the safety tests need:

  * transport itinerary / internal-note / airport-code conflicts
  * blank case owners
  * response timestamps that precede case creation
  * ambiguous cases with no status and no contact history
  * a spread of nationalities + message languages (for the bias audit)

Run:  python scripts/generate_synthetic_data.py
Out:  data/raw/*.csv
"""

from __future__ import annotations

import csv
import os
import random
from datetime import datetime, timedelta

SEED = 20261018
N_CASES = 200
NOW = datetime(2026, 10, 18, 12, 0, 0)

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(HERE, "..", "data", "raw")

NATIONALITIES = ["Thai", "Myanmar", "French", "German", "Other"]
LANGUAGES = ["English", "Thai", "Burmese", "French", "German"]
STATUSES = [
    "Submitted",
    "Documents Pending",
    "Under Review",
    "Awaiting Payment",
    "Approved",
    "Rejected",
    "On Hold",
]
JOURNEY_TYPES = ["Tourist", "Business", "Student", "Work", "Family"]
DESTINATIONS = ["Japan", "United Kingdom", "Germany", "Australia", "United States", "Canada", "Schengen Area"]
CONTACT_CATEGORIES = ["Phone", "Email", "Web chat", "LINE", "Office visit"]
SENTIMENTS = ["positive", "neutral", "negative"]

# journey_type -> (sla_target_hours, required_documents)
SLA_CATALOG = {
    "Tourist": (48, ["passport", "photo", "bank_statement", "itinerary"]),
    "Business": (72, ["passport", "photo", "invitation_letter", "bank_statement"]),
    "Student": (120, ["passport", "photo", "acceptance_letter", "financial_proof"]),
    "Work": (168, ["passport", "photo", "work_permit", "employment_contract"]),
    "Family": (96, ["passport", "photo", "relationship_proof", "sponsor_letter"]),
}

STAFF_IDS = [f"ST-{i:03d}" for i in range(1, 13)]

# Airport pool: (display name, IATA code). Consistent bookings reuse one entry;
# conflict bookings pull from three different entries on purpose.
AIRPORTS = [
    ("NRT - Narita International", "NRT"),
    ("HND - Haneda", "HND"),
    ("LHR - Heathrow", "LHR"),
    ("LGW - Gatwick", "LGW"),
    ("FRA - Frankfurt", "FRA"),
    ("MUC - Munich", "MUC"),
    ("SYD - Sydney", "SYD"),
    ("MEL - Melbourne", "MEL"),
]

DOC_SUMMARY_TEMPLATES = [
    "Customer asked whether their {doc} was received.",
    "Following up on the outstanding {doc} request.",
    "Customer resent a clearer copy of their {doc}.",
    "Asked for an update on the {doc} review.",
    "Confirmed the {doc} has been uploaded to the portal.",
    "Requested clarification about the {doc} requirement.",
]

REVIEW_TEXTS = {
    5: "Very prompt and clear communication, thank you.",
    4: "Helpful staff, small delay but kept informed.",
    3: "Dealt with eventually, communication could be faster.",
    2: "Slow updates, had to chase several times.",
    1: "Still waiting with no clear answer. Frustrating.",
}


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def write_csv(path: str, fieldnames, rows) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rng = random.Random(SEED)

    cases = []
    contacts = []
    transport = []
    reviews = []

    contact_seq = 0
    booking_seq = 0
    review_seq = 0

    # Deterministic edge-case landing spots so a human can eyeball them.
    conflict_idxs = {3, 17, 44, 88, 132}
    blank_owner_idxs = {7, 25, 60, 111, 170}
    ts_conflict_idxs = {12, 33, 77, 140}
    ambiguous_idxs = {1, 50, 99, 199}

    for i in range(N_CASES):
        case_id = f"VC-{i + 1:05d}"
        customer_id = f"CUST-{rng.randint(1000, 9999)}"
        journey_type = rng.choice(JOURNEY_TYPES)
        status = rng.choice(STATUSES)
        nationality = rng.choice(NATIONALITIES)
        language = rng.choice(LANGUAGES)
        destination = rng.choice(DESTINATIONS)
        sla_target, required_docs = SLA_CATALOG[journey_type]

        created_days_ago = rng.randint(1, 45)
        created_at = NOW - timedelta(days=created_days_ago, hours=rng.randint(0, 23))
        last_update = created_at + timedelta(hours=rng.randint(1, created_days_ago * 24))

        owner = rng.choice(STAFF_IDS + [""])  # "" happens naturally too
        if i in blank_owner_idxs:
            owner = ""

        # --- ambiguous cases: no status, no docs, no contacts -----------------
        if i in ambiguous_idxs:
            status = ""
            required_docs = []
            docs_received = []
            last_update = created_at
        else:
            # Randomly drop some required documents (missing-document flags).
            docs_received = [d for d in required_docs if rng.random() > 0.25]

        # --- transport bookings -------------------------------------------------
        if i in conflict_idxs:
            a, b, c = rng.sample(AIRPORTS, 3)
            transport.append(
                {
                    "booking_id": f"BK-{booking_seq:05d}",
                    "case_id": case_id,
                    "itinerary_value": a[0],
                    "internal_note_value": b[0],
                    "airport_code": c[1],
                    "departure_date": (created_at + timedelta(days=30)).strftime("%Y-%m-%d"),
                }
            )
            booking_seq += 1
        elif rng.random() < 0.5:
            name, code = rng.choice(AIRPORTS)
            transport.append(
                {
                    "booking_id": f"BK-{booking_seq:05d}",
                    "case_id": case_id,
                    "itinerary_value": name,
                    "internal_note_value": name,  # consistent
                    "airport_code": code,
                    "departure_date": (created_at + timedelta(days=30)).strftime("%Y-%m-%d"),
                }
            )
            booking_seq += 1

        # --- contacts -----------------------------------------------------------
        n_contacts = 0 if i in ambiguous_idxs else rng.randint(0, 4)
        for _ in range(n_contacts):
            contact_seq += 1
            sent = created_at + timedelta(hours=rng.randint(1, max(2, created_days_ago * 24)))
            responded_by = rng.choice(STAFF_IDS + ["", ""])
            if responded_by:
                resp = sent + timedelta(hours=rng.randint(1, 72))
            else:
                resp = ""
            if i in ts_conflict_idxs and contact_seq % 7 == 0:
                # response BEFORE case creation -> timestamp conflict
                resp = created_at - timedelta(hours=rng.randint(1, 10))

            doc = rng.choice(required_docs) if required_docs else "passport"
            contacts.append(
                {
                    "contact_id": f"CT-{contact_seq:05d}",
                    "case_id": case_id,
                    "channel": rng.choice(CONTACT_CATEGORIES),
                    "message_summary": rng.choice(DOC_SUMMARY_TEMPLATES).format(doc=doc),
                    "message_language": language,
                    "sentiment_label": rng.choices(SENTIMENTS, weights=[2, 5, 3])[0],
                    "contact_at": iso(sent),
                    "response_sent_at": iso(resp) if resp else "",
                    "responded_by_staff_id": responded_by,
                }
            )
            if resp:
                last_update = max(last_update, resp)

        # --- reviews (only for some closed-ish cases) ---------------------------
        if status in ("Approved", "Rejected") and rng.random() < 0.7:
            review_seq += 1
            rating = rng.choices([1, 2, 3, 4, 5], weights=[1, 2, 3, 5, 4])[0]
            reviews.append(
                {
                    "review_id": f"RV-{review_seq:05d}",
                    "case_id": case_id,
                    "rating": rating,
                    "review_text": REVIEW_TEXTS[rating],
                    "review_at": iso(last_update + timedelta(hours=rng.randint(1, 48))),
                }
            )

        cases.append(
            {
                "case_id": case_id,
                "customer_id": customer_id,
                "customer_nationality": nationality,
                "case_owner_staff_id": owner,
                "current_status": status,
                "journey_type": journey_type,
                "destination_country": destination,
                "case_created_at": iso(created_at),
                "last_customer_update_at": iso(last_update),
                "required_documents": ";".join(required_docs),
                "documents_received": ";".join(docs_received),
                "payment_status": rng.choice(["unpaid", "partial", "paid", ""]),
                "message_language": language,
            }
        )

    write_csv(
        os.path.join(RAW_DIR, "visa_cases.csv"),
        [
            "case_id", "customer_id", "customer_nationality", "case_owner_staff_id",
            "current_status", "journey_type", "destination_country", "case_created_at",
            "last_customer_update_at", "required_documents", "documents_received",
            "payment_status", "message_language",
        ],
        cases,
    )
    write_csv(
        os.path.join(RAW_DIR, "customer_contacts.csv"),
        [
            "contact_id", "case_id", "channel", "message_summary",
            "message_language", "sentiment_label", "contact_at", "response_sent_at",
            "responded_by_staff_id",
        ],
        contacts,
    )
    write_csv(
        os.path.join(RAW_DIR, "transport_bookings.csv"),
        ["booking_id", "case_id", "itinerary_value", "internal_note_value", "airport_code", "departure_date"],
        transport,
    )
    write_csv(
        os.path.join(RAW_DIR, "customer_reviews.csv"),
        ["review_id", "case_id", "rating", "review_text", "review_at"],
        reviews,
    )

    # --- reference files --------------------------------------------------------
    write_csv(
        os.path.join(RAW_DIR, "service_catalog_sla.csv"),
        ["journey_type", "sla_target_hours", "required_documents", "description"],
        [
            {
                "journey_type": jt,
                "sla_target_hours": hours,
                "required_documents": ";".join(docs),
                "description": f"Standard {jt.lower()} visa service level target.",
            }
            for jt, (hours, docs) in SLA_CATALOG.items()
        ],
    )
    write_csv(
        os.path.join(RAW_DIR, "DATA_DICTIONARY.csv"),
        ["dataset", "column_name", "data_type", "contains_pii", "description"],
        [
            {"dataset": d, "column_name": c, "data_type": t, "contains_pii": p, "description": desc}
            for (d, c, t, p, desc) in [
                ("visa_cases", "case_id", "string", "no", "Primary key for a visa case."),
                ("visa_cases", "customer_id", "string", "yes", "Pseudonymous customer identifier."),
                ("visa_cases", "customer_nationality", "string", "yes", "Customer nationality. Excluded from LLM payload."),
                ("visa_cases", "case_owner_staff_id", "string", "no", "Assigned staff owner; blank means unassigned."),
                ("visa_cases", "current_status", "string", "no", "Current workflow status of the case."),
                ("visa_cases", "journey_type", "string", "no", "Visa service category; maps to an SLA target."),
                ("visa_cases", "destination_country", "string", "no", "Intended destination country."),
                ("visa_cases", "case_created_at", "datetime", "no", "When the case was opened."),
                ("visa_cases", "last_customer_update_at", "datetime", "no", "Most recent customer-originated update."),
                ("visa_cases", "required_documents", "list", "no", "Semicolon-separated required document keys."),
                ("visa_cases", "documents_received", "list", "no", "Semicolon-separated received document keys."),
                ("visa_cases", "payment_status", "string", "no", "unpaid | partial | paid | blank."),
                ("visa_cases", "message_language", "string", "yes", "Preferred message language. Excluded from LLM payload."),
                ("customer_contacts", "channel", "string", "no", "Phone | Email | Web chat | LINE | Office visit."),
                ("customer_contacts", "sentiment_label", "string", "no", "positive | neutral | negative."),
                ("customer_contacts", "contact_at", "datetime", "no", "When the customer made contact."),
                ("customer_contacts", "response_sent_at", "datetime", "no", "When staff responded; blank if none."),
                ("transport_bookings", "itinerary_value", "string", "no", "Airport as printed on the itinerary."),
                ("transport_bookings", "internal_note_value", "string", "no", "Airport as recorded in the internal note."),
                ("transport_bookings", "airport_code", "string", "no", "Airport code from the booking system."),
                ("customer_reviews", "rating", "int", "no", "1-5 star review score."),
            ]
        ],
    )

    print(f"Generated {len(cases)} cases, {len(contacts)} contacts, "
          f"{len(transport)} bookings, {len(reviews)} reviews into {RAW_DIR}")


if __name__ == "__main__":
    main()
