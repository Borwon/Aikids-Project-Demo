"""VisaConnect Case Copilot -- offline, deterministic draft engine.

The design mirrors the build plan's LLM contract exactly, but the "model" is a
pure function so the whole thing runs with no API key, no network, and no
nondeterminism. Swapping in a real chat-completion call is a one-function
change (`generate_draft_llm`); the payload shape, the hard rules, and the
post-generation validator all stay identical.

Two guarantees this module enforces, both structurally:

  1. `build_llm_payload` NEVER includes `customer_nationality` or
     `message_language`. The generator only ever reads the sanitized payload
     plus case-level structural facts, so it cannot bias on excluded fields.
  2. `validate_draft` re-checks the hard rules AFTER generation. A prompt can
     be ignored; this check cannot. Anything that fails is rejected.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Callable

CONFIDENCE_VALUES = ("confirmed", "conflicting", "insufficient")

# Fields excluded from the payload by design -- the mechanism, not a note.
EXCLUDED_FIELDS = ("customer_nationality", "message_language")

INSUFFICIENT_PHRASE = "insufficient information to recommend an action"

DRAFT_SCHEMA_KEYS = {
    "summary",
    "flags",
    "recommended_action",
    "draft_message",
    "confidence_overall",
    "insufficient_information",
}


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------- #
# Deterministic structural detection (mirrors clean_data.py, no LLM involved)
# --------------------------------------------------------------------------- #
def detect_transport_conflict(transport: dict | None) -> bool:
    if not transport:
        return False
    itin = str(transport.get("itinerary_value") or "").strip()
    note = str(transport.get("internal_note_value") or "").strip()
    code = str(transport.get("airport_code") or "").strip()
    if not itin and not note:
        return False
    values = {v for v in (itin, note) if v}
    if len(values) > 1:
        return True
    ci = itin.split(" ")[0] if itin else ""
    cn = note.split(" ")[0] if note else ""
    cp = code.split(" ")[0] if code else ""
    if cp and cp not in {ci, cn}:
        return True
    return False


def detect_timestamp_conflict(case: dict) -> bool:
    created = _parse_dt(case.get("case_created_at"))
    if not created:
        return False
    for c in case.get("contacts", []) or []:
        resp = _parse_dt(c.get("response_sent_at"))
        if resp and resp < created:
            return True
    return False


def structural_flags(case: dict) -> list[dict]:
    """Flags derived directly from case structure -- independent of any model."""
    flags: list[dict] = []

    if not str(case.get("case_owner_staff_id", "")).strip():
        flags.append({
            "issue_type": "UNASSIGNED_OWNER",
            "field": "case_owner_staff_id",
            "evidence": "case_owner_staff_id is blank",
            "confidence": "confirmed",
        })

    if not str(case.get("current_status", "")).strip():
        flags.append({
            "issue_type": "MISSING_REQUIRED_FIELD",
            "field": "current_status",
            "evidence": "current_status is blank",
            "confidence": "insufficient",
        })

    transport = case.get("transport")
    if detect_transport_conflict(transport):
        t = transport or {}
        flags.append({
            "issue_type": "TRANSPORT_CONFLICT",
            "field": "transport_bookings",
            "evidence": (
                f"itinerary='{t.get('itinerary_value', '')}' "
                f"internal_note='{t.get('internal_note_value', '')}' "
                f"airport_code='{t.get('airport_code', '')}'"
            ),
            "confidence": "conflicting",
        })

    if detect_timestamp_conflict(case):
        flags.append({
            "issue_type": "STATUS_TIMESTAMP_CONFLICT",
            "field": "response_sent_at",
            "evidence": "a response_sent_at precedes case_created_at",
            "confidence": "conflicting",
        })

    if not (case.get("contacts") or []) and not str(case.get("current_status", "")).strip():
        flags.append({
            "issue_type": "AMBIGUOUS_CASE",
            "field": "current_status",
            "evidence": "No status and no contact history",
            "confidence": "insufficient",
        })

    return flags


def _merge_flags(case: dict) -> list[dict]:
    """Union of pipeline flags (issue_log) and structural flags, deduped by type."""
    merged: dict[str, dict] = {}
    for f in case.get("flags", []) or []:
        merged.setdefault(f.get("issue_type", ""), f)
    for f in structural_flags(case):
        merged.setdefault(f["issue_type"], f)
    return list(merged.values())


# --------------------------------------------------------------------------- #
# Payload construction
# --------------------------------------------------------------------------- #
def build_llm_payload(case: dict) -> dict:
    """Build the structured JSON block sent to the model.

    Only fields already present in `cases.json` are read, and nationality /
    language are hard-excluded here so no downstream code can reintroduce them.
    """
    transport = case.get("transport") or {}
    latest = case.get("latest_contact") or {}

    payload = {
        "case_id": case.get("case_id", ""),
        "current_status": case.get("current_status", ""),
        "journey_type": case.get("journey_type", ""),
        "case_created_at": case.get("case_created_at", ""),
        "last_customer_update_at": case.get("last_customer_update_at", ""),
        "sla_target_hours": case.get("sla_target_hours", 0),
        "hours_elapsed": case.get("hours_elapsed", 0),
        "sla_breached": case.get("sla_breached", False),
        "case_owner_staff_id": case.get("case_owner_staff_id", ""),
        "flags": [
            {
                "issue_type": f.get("issue_type", ""),
                "field": f.get("field", ""),
                "evidence": f.get("evidence", ""),
                "confidence": f.get("confidence", "confirmed"),
            }
            for f in _merge_flags(case)
        ],
        "latest_contact": (
            {
                "channel": latest.get("channel", ""),
                "message_summary": latest.get("message_summary", ""),
                "sentiment_label": latest.get("sentiment_label", ""),
            }
            if latest
            else None
        ),
        "transport_flag": {
            "conflict": bool(transport.get("conflict", False)) or detect_transport_conflict(transport),
            "itinerary_value": transport.get("itinerary_value", ""),
            "internal_note_value": transport.get("internal_note_value", ""),
        },
    }

    for field in EXCLUDED_FIELDS:
        payload.pop(field, None)

    return payload


# --------------------------------------------------------------------------- #
# Deterministic generation
# --------------------------------------------------------------------------- #
def _flag_line(flag: dict) -> dict:
    conf = flag.get("confidence", "confirmed")
    if conf not in CONFIDENCE_VALUES:
        conf = "confirmed"
    if conf == "insufficient":
        note = "insufficient data \u2014 do not guess"
    else:
        note = str(flag.get("evidence", "")).strip()
    return {
        "issue_type": flag.get("issue_type", ""),
        "field": flag.get("field", ""),
        "confidence": conf,
        "note": note,
    }


def generate_draft(case: dict) -> dict:
    """Pure, deterministic draft generator."""
    payload = build_llm_payload(case)

    flags = [_flag_line(f) for f in payload["flags"]]
    types = {f["issue_type"] for f in flags}

    transport = payload["transport_flag"]
    has_transport_conflict = bool(transport["conflict"])

    no_status = not str(payload.get("current_status", "")).strip()
    has_history = payload.get("latest_contact") is not None or bool(case.get("contacts"))
    insufficient = (
        "AMBIGUOUS_CASE" in types
        or "MISSING_REQUIRED_FIELD" in types
        or (no_status and not has_history)
    )

    status = payload.get("current_status") or "no status"
    summary = (
        f"Case {payload['case_id']} ({payload.get('journey_type') or 'unknown journey'}) "
        f"is '{status}' with {len(flags)} flag(s); "
        f"SLA {'breached' if payload.get('sla_breached') else 'within target'} "
        f"({payload.get('hours_elapsed')}h elapsed vs {payload.get('sla_target_hours')}h target)."
    )

    if insufficient:
        recommended_action = INSUFFICIENT_PHRASE
        draft_message = None
        confidence_overall = "low"
    elif has_transport_conflict:
        recommended_action = "confirm with customer"
        draft_message = (
            "Hello, thank you for your patience. Before we proceed we need to "
            "confirm the departure airport for your booking \u2014 our records hold "
            "more than one value and we will not assume which is correct. Could "
            "you confirm the airport you intend to depart from? "
            "(Suggested draft \u2014 not sent.)"
        )
        confidence_overall = "medium"
    else:
        if "MISSING_DOCUMENT" in types:
            recommended_action = "request the outstanding documents from the customer"
            draft_message = (
                "Hello, thank you for your patience. To move your application "
                "forward we still need one or more outstanding documents on file. "
                "Could you upload them at your earliest convenience? "
                "(Suggested draft \u2014 not sent.)"
            )
        elif "UNASSIGNED_OWNER" in types:
            recommended_action = "assign a case owner before further action"
            draft_message = (
                "Hello, thank you for your patience. We are arranging the right "
                "case owner for your application and will follow up shortly. "
                "(Suggested draft \u2014 not sent.)"
            )
        elif payload.get("sla_breached"):
            recommended_action = "send the customer a status update to recover the SLA"
            draft_message = (
                "Hello, thank you for your patience. We are reviewing your case "
                "and will update you with next steps shortly. "
                "(Suggested draft \u2014 not sent.)"
            )
        else:
            recommended_action = "no action required; continue monitoring the case"
            draft_message = (
                "Hello, thank you for your patience. Your case is progressing "
                "normally and we will contact you if anything is needed. "
                "(Suggested draft \u2014 not sent.)"
            )
        confidence_overall = (
            "medium" if any(f["confidence"] == "conflicting" for f in flags) else "high"
        )

    return {
        "summary": summary,
        "flags": flags,
        "recommended_action": recommended_action,
        "draft_message": draft_message,
        "confidence_overall": confidence_overall,
        "insufficient_information": insufficient,
    }


def generate_draft_llm(case: dict, llm_fn: Callable[[dict], dict]) -> dict:
    """Live-LLM path. Same payload, same validator, so the safety boundary holds.

    `llm_fn` receives the sanitized payload and must return an object matching
    DRAFT_SCHEMA_KEYS. Its output is validated; on failure it is regenerated
    deterministically so an unusable draft never reaches the screen.
    """
    payload = build_llm_payload(case)
    candidate = llm_fn(payload)
    ok, _ = validate_draft(payload, candidate)
    if not ok:
        return generate_draft(case)
    return candidate


# --------------------------------------------------------------------------- #
# Post-generation hard-rule validator (the actual safety boundary)
# --------------------------------------------------------------------------- #
_STAFF_ID_RE = re.compile(r"\bST-\d{2,4}\b")


def validate_draft(payload: dict, draft: dict) -> tuple[bool, list[str]]:
    """Re-check the hard rules after generation. Returns (ok, reasons)."""
    reasons: list[str] = []

    if not isinstance(draft, dict):
        return False, ["draft is not an object"]

    missing_keys = DRAFT_SCHEMA_KEYS - set(draft.keys())
    if missing_keys:
        reasons.append(f"schema missing keys: {sorted(missing_keys)}")

    text = " ".join(
        str(draft.get(k, "")) for k in ("summary", "recommended_action", "draft_message")
    )

    transport = payload.get("transport_flag", {})
    conflict = bool(transport.get("conflict", False))

    # Rule 1: transport conflict -> never state an airport as correct.
    if conflict:
        itin = (transport.get("itinerary_value") or "").strip()
        note = (transport.get("internal_note_value") or "").strip()
        for value in (itin, note):
            if not value:
                continue
            for token in {value, value.split(" ")[0]}:
                if token and token.lower() in text.lower():
                    reasons.append(
                        f"transport conflict but output states airport '{token}' as fact"
                    )
        action = str(draft.get("recommended_action", "")).lower()
        if "confirm" not in action:
            reasons.append("transport conflict but recommended action is not 'confirm with customer'")
        if not draft.get("draft_message"):
            reasons.append("transport conflict but no draft message produced")

    # Rule 2: blank owner -> never name a staff member.
    if not str(payload.get("case_owner_staff_id", "")).strip():
        if _STAFF_ID_RE.search(text):
            reasons.append("blank owner but output names a staff id")
        types = {f.get("issue_type") for f in draft.get("flags", [])}
        if "UNASSIGNED_OWNER" not in types:
            reasons.append("blank owner but UNASSIGNED_OWNER flag missing")

    # Rule 3: insufficient cases must say so and must not fabricate an action.
    if draft.get("insufficient_information"):
        if INSUFFICIENT_PHRASE not in str(draft.get("recommended_action", "")):
            reasons.append("insufficient case but recommended action is not the insufficient phrase")
        if draft.get("draft_message"):
            reasons.append("insufficient case but a draft message was produced")

    # Rule 4: never phrase as already done / sent / decided.
    lowered = text.lower()
    for banned in ("has been sent", "we have sent", "has been approved", "we approved",
                   "has been decided", "is now approved"):
        if banned in lowered:
            reasons.append(f"output implies an action already happened: '{banned}'")

    # Rule 5: every flag carries a valid confidence tag.
    for f in draft.get("flags", []):
        if f.get("confidence") not in CONFIDENCE_VALUES:
            reasons.append(f"flag '{f.get('issue_type')}' has invalid confidence tag")

    return (len(reasons) == 0), reasons
