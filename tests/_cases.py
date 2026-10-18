"""Shared test fixtures / builders."""

from __future__ import annotations


def make_case(**over) -> dict:
    """A minimal, valid case object shaped like an entry in cases.json."""
    base = {
        "case_id": "VC-TEST",
        "current_status": "Submitted",
        "journey_type": "Tourist",
        "case_created_at": "2026-10-01T09:00:00",
        "last_customer_update_at": "2026-10-02T09:00:00",
        "case_owner_staff_id": "ST-001",
        "destination_country": "Japan",
        "customer_nationality": "Thai",
        "message_language": "English",
        "sla_target_hours": 48,
        "hours_elapsed": 10.0,
        "sla_breached": False,
        "required_documents": ["passport"],
        "documents_received": ["passport"],
        "payment_status": "paid",
        "flags": [],
        "contacts": [],
        "latest_contact": None,
        "transport": None,
        "reviews": [],
    }
    base.update(over)
    return base


def contact(case_id="VC-TEST", **over) -> dict:
    c = {
        "contact_id": "CT-00001",
        "case_id": case_id,
        "contact_category": "email",
        "channel": "Email",
        "message_summary": "Asked for an update.",
        "message_language": "English",
        "sentiment_label": "neutral",
        "contact_at": "2026-10-02T09:00:00",
        "response_sent_at": "",
        "responded_by_staff_id": "ST-001",
    }
    c.update(over)
    return c
