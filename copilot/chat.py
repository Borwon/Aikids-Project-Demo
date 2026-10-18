"""VisaConnect Case Copilot -- scoped, read-only case chat.

One case at a time. The chat explains, summarizes and answers questions from
that case's own data. It never takes or confirms an action, never picks an
airport when there is a transport conflict, never invents an owner, and says
"insufficient information" rather than guessing.

Like `draft.py`, the model call is a pure function by default so the whole
feature runs offline and deterministically. `answer_llm` is the drop-in for a
real chat-completion call; it reuses the exact same context builder and the same
post-generation `validate_chat_reply` safety boundary.

`build_chat_context` hard-excludes `customer_nationality` and `message_language`
(nested included) -- the mechanism, not a filter applied afterwards.
"""

from __future__ import annotations

import json
import re
from typing import Callable

from .draft import detect_transport_conflict

EXCLUDED_FIELDS = ("customer_nationality", "message_language")

INSUFFICIENT_EN = "insufficient information in this case's data"
INSUFFICIENT_TH = "\u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25\u0e43\u0e19\u0e40\u0e04\u0e2a\u0e19\u0e35\u0e49\u0e44\u0e21\u0e48\u0e40\u0e1e\u0e35\u0e22\u0e07\u0e1e\u0e2d"

ACTION_REFUSAL_TOKEN = "Approve button"  # the plan names this control explicitly


# --------------------------------------------------------------------------- #
# Scoped context (single case, excluded fields never included)
# --------------------------------------------------------------------------- #
def _strip(d: dict | None) -> dict | None:
    if not d:
        return d
    return {k: v for k, v in d.items() if k not in EXCLUDED_FIELDS}


def build_chat_context(case: dict) -> dict:
    """The chat's only source of truth: this one case, minus excluded fields."""
    ctx = {k: v for k, v in case.items() if k not in EXCLUDED_FIELDS}
    ctx["contacts"] = [_strip(c) for c in case.get("contacts", [])]
    latest = case.get("latest_contact")
    ctx["latest_contact"] = _strip(latest) if latest else None

    t = case.get("transport") or {}
    ctx["transport_flag"] = {
        "conflict": bool(t.get("conflict")) or detect_transport_conflict(t),
        "itinerary_value": t.get("itinerary_value", ""),
        "internal_note_value": t.get("internal_note_value", ""),
        "airport_code": t.get("airport_code", ""),
    }
    for field in EXCLUDED_FIELDS:
        ctx.pop(field, None)
    return ctx


def build_system_prompt(case: dict) -> str:
    """Per-request system prompt built from the case's own data only."""
    context = build_chat_context(case)
    instructions = (
        "You are a read-only assistant answering staff questions about this one "
        "case only, using only the data given. You cannot take, confirm, or send "
        "any action -- if asked to, say approval happens through the Approve "
        "button, not here. If the data doesn't contain what's asked, say "
        "\u201cinsufficient information in this case's data.\u201d If there's a transport "
        "conflict, state both values and say it needs human confirmation -- never "
        "pick one. If there's no assigned owner, say so plainly. Never use the "
        "customer's nationality or language as a reason for anything. Do not "
        "invent a contact channel that is not in the data."
    )
    return (
        f"{instructions}\n\n"
        "CASE DATA (the only source of truth):\n"
        f"{json.dumps(context, ensure_ascii=False)}"
    )


def build_messages(case: dict, message: str, history: list[dict] | None = None) -> list[dict]:
    """Full chat-completion message list: system + running history + new turn."""
    msgs = [{"role": "system", "content": build_system_prompt(case)}]
    for turn in history or []:
        role = turn.get("role")
        if role in ("user", "assistant") and turn.get("content"):
            msgs.append({"role": role, "content": str(turn["content"])})
    msgs.append({"role": "user", "content": message})
    return msgs


# --------------------------------------------------------------------------- #
# Deterministic responder
# --------------------------------------------------------------------------- #
def _has_thai(s: str) -> bool:
    return bool(re.search(r"[\u0e00-\u0e7f]", s or ""))


def _fmt(iso: str) -> str:
    return str(iso).replace("T", " ")[:16] if iso else "\u2014"


def _last_contact(case: dict) -> dict | None:
    contacts = case.get("contacts") or []
    if contacts:
        return contacts[-1]
    return case.get("latest_contact")


def _missing_docs(case: dict) -> list[str]:
    required = case.get("required_documents") or []
    received = set(case.get("documents_received") or [])
    return [d for d in required if d not in received]


def _conflict_of(case: dict) -> dict:
    t = case.get("transport") or {}
    return {
        "conflict": bool(t.get("conflict")) or detect_transport_conflict(t),
        "itinerary_value": t.get("itinerary_value", ""),
        "internal_note_value": t.get("internal_note_value", ""),
        "airport_code": t.get("airport_code", ""),
    }


def _has(msg: str, words) -> bool:
    return any(w in msg for w in words)


# Keyword sets (English + Thai)
KW = {
    "transport": ["transport", "airport", "pickup", "pick-up", "pick up", "flight",
                  "itinerary", "departure", "transfer", "terminal", "\u0e2a\u0e19\u0e32\u0e21\u0e1a\u0e34\u0e19", "\u0e23\u0e31\u0e1a\u0e2a\u0e48\u0e07",
                  "\u0e40\u0e17\u0e35\u0e48\u0e22\u0e27\u0e1a\u0e34\u0e19", "\u0e02\u0e36\u0e49\u0e19\u0e40\u0e04\u0e23\u0e37\u0e48\u0e2d\u0e07", "\u0e40\u0e14\u0e34\u0e19\u0e17\u0e32\u0e07"],
    "owner": ["owner", "owns", "assigned", "who is handling", "who handles", "responsible", "caseworker",
              "\u0e40\u0e08\u0e49\u0e32\u0e02\u0e2d\u0e07", "\u0e1c\u0e39\u0e49\u0e14\u0e39\u0e41\u0e25", "\u0e1c\u0e39\u0e49\u0e23\u0e31\u0e1a\u0e1c\u0e34\u0e14\u0e0a\u0e2d\u0e1a", "\u0e21\u0e2d\u0e1a\u0e2b\u0e21\u0e32\u0e22", "\u0e43\u0e04\u0e23\u0e14\u0e39\u0e41\u0e25"],
    "contact": ["contact", "channel", "called", "call", "emailed", "email", "line",
                "last contact", "reached", "who contacted", "messaged", "touch",
                "\u0e15\u0e34\u0e14\u0e15\u0e48\u0e2d", "\u0e0a\u0e48\u0e2d\u0e07\u0e17\u0e32\u0e07", "\u0e42\u0e17\u0e23", "\u0e2d\u0e35\u0e40\u0e21\u0e25", "\u0e25\u0e48\u0e32\u0e2a\u0e38\u0e14", "\u0e17\u0e31\u0e01"],
    "documents": ["document", "documents", "passport", "photo", "upload", "paperwork",
                  "acceptance_letter", "financial_proof", "\u0e40\u0e2d\u0e01\u0e2a\u0e32\u0e23", "\u0e2b\u0e19\u0e31\u0e07\u0e2a\u0e37\u0e2d\u0e40\u0e14\u0e34\u0e19\u0e17\u0e32\u0e07",
                  "\u0e2d\u0e31\u0e1b\u0e42\u0e2b\u0e25\u0e14", "\u0e41\u0e19\u0e1a"],
    "sla": ["sla", "breach", "overdue", "deadline", "target", "how long", "too long",
            "\u0e40\u0e25\u0e22\u0e01\u0e33\u0e2b\u0e19\u0e14", "\u0e40\u0e01\u0e34\u0e19\u0e01\u0e33\u0e2b\u0e19\u0e14", "\u0e17\u0e31\u0e19\u0e40\u0e27\u0e25\u0e32", "\u0e19\u0e32\u0e19\u0e41\u0e04\u0e48\u0e44\u0e2b\u0e19", "\u0e04\u0e49\u0e32\u0e07"],
    "flags": ["flag", "issue", "problem", "wrong", "conflict", "concern",
              "\u0e1b\u0e31\u0e0d\u0e2b\u0e32", "\u0e1c\u0e34\u0e14", "\u0e02\u0e31\u0e14\u0e41\u0e22\u0e49\u0e07"],
    "payment": ["payment", "paid", "unpaid", "invoice", "fee",
                "\u0e08\u0e48\u0e32\u0e22", "\u0e0a\u0e33\u0e23\u0e30", "\u0e40\u0e07\u0e34\u0e19"],
    "status": ["status", "progress", "where is", "state of", "update on", "how far",
               "\u0e2a\u0e16\u0e32\u0e19\u0e30", "\u0e04\u0e27\u0e32\u0e21\u0e04\u0e37\u0e1a\u0e2b\u0e19\u0e49\u0e32", "\u0e16\u0e36\u0e07\u0e44\u0e2b\u0e19", "\u0e40\u0e1b\u0e47\u0e19\u0e22\u0e31\u0e07\u0e44\u0e07"],
    "destination": ["destination", "where are they going", "which country", "\u0e1b\u0e25\u0e32\u0e22\u0e17\u0e32\u0e07", "\u0e44\u0e1b\u0e44\u0e2b\u0e19"],
    "reviews": ["review", "rating", "feedback", "complaint", "\u0e23\u0e35\u0e27\u0e34\u0e27", "\u0e23\u0e49\u0e2d\u0e07\u0e40\u0e23\u0e35\u0e22\u0e19", "\u0e04\u0e30\u0e41\u0e19\u0e19"],
    "summary": ["summary", "summar", "overview", "situation", "what's going on", "recap",
                "\u0e2a\u0e23\u0e38\u0e1b"],
    "action": ["send", "rebook", "re-book", "go ahead", "submit", "cancel", "escalate",
               "forward this", "approve it", "approve this", "just approve", "do it",
               "make the booking", "tell the customer", "email the customer",
               "message the customer", "update the customer", "process it",
               "confirm the booking", "confirm my booking",
               "\u0e2a\u0e48\u0e07", "\u0e2d\u0e19\u0e38\u0e21\u0e31\u0e15\u0e34", "\u0e08\u0e2d\u0e07", "\u0e22\u0e01\u0e40\u0e25\u0e34\u0e01",
               "\u0e41\u0e08\u0e49\u0e07\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32", "\u0e14\u0e33\u0e40\u0e19\u0e34\u0e19\u0e01\u0e32\u0e23", "\u0e17\u0e33\u0e40\u0e25\u0e22"],
}

CASE_ID_RE = re.compile(r"\bVC-\d{3,5}\b", re.IGNORECASE)
STAFF_ID_RE = re.compile(r"\bST-\d{2,4}\b")


def _refusal(case: dict, lang: str) -> str:
    c = _conflict_of(case)
    if lang == "th":
        base = ("แชทนี้เป็นแบบอ่านอย่างเดียว จึงไม่สามารถส่ง อนุมัติ หรือดำเนินการใด ๆ ได้ "
                "การอนุมัติทำได้ผ่านปุ่ม Approve บนแผงร่างข้อความเท่านั้น")
        if c["conflict"]:
            base += (f" และเรื่องการรับส่งต้องให้เจ้าหน้าที่ตรวจสอบยืนยันก่อน "
                     f"ใบเดินทางระบุ '{c['itinerary_value']}' แต่บันทึกภายในระบุ "
                     f"'{c['internal_note_value']}' จะไม่สรุปว่าอันไหนถูก")
        return base
    base = ("This chat is read-only, so I can't send, approve or take any action. "
            "Approval happens through the Approve button on the draft panel, not here.")
    if c["conflict"]:
        base += (f" On the transport question: the itinerary lists '{c['itinerary_value']}' "
                 f"while the internal note says '{c['internal_note_value']}' -- this needs "
                 f"human confirmation and I won't pick which is correct.")
    return base


def _answer_transport(case: dict, lang: str) -> str:
    c = _conflict_of(case)
    t = case.get("transport")
    if not t or (not c["itinerary_value"] and not c["internal_note_value"]):
        return INSUFFICIENT_TH if lang == "th" else INSUFFICIENT_EN
    if c["conflict"]:
        if lang == "th":
            return (f"เรื่องการรับส่งต้องให้เจ้าหน้าที่ตรวจสอบและยืนยันก่อน "
                    f"ใบเดินทางระบุ '{c['itinerary_value']}' แต่บันทึกภายในระบุ "
                    f"'{c['internal_note_value']}' (รหัสระบบจอง: {c['airport_code'] or '—'}) "
                    f"จะไม่สรุปว่าอันไหนถูกต้อง ต้องยืนยันกับลูกค้าก่อน")
        return (f"Transport needs human confirmation. The itinerary lists "
                f"'{c['itinerary_value']}' while the internal note says "
                f"'{c['internal_note_value']}' (booking system code: {c['airport_code'] or '—'}). "
                f"I won't say which is correct -- this must be confirmed with the customer "
                f"by a staff member before anything is rebooked.")
    if lang == "th":
        return f"ข้อมูลการเดินทางที่มีคือ '{c['itinerary_value']}' (รหัส {c['airport_code'] or '—'}) ยังไม่มีการเปลี่ยนแปลง"
    return (f"The transport on file is '{c['itinerary_value']}' "
            f"(booking code {c['airport_code'] or '—'}). No conflict is recorded.")


def _answer_owner(case: dict, lang: str) -> str:
    owner = str(case.get("case_owner_staff_id") or "").strip()
    if not owner:
        if lang == "th":
            return "เคสนี้ยังไม่มีผู้ดูแล assigned — ช่อง case_owner_staff_id ว่างอยู่ จึงไม่ระบุชื่อใคร"
        return ("No owner is assigned to this case -- case_owner_staff_id is blank, so I "
                "won't name anyone who isn't actually on the case.")
    return (f"เคสนี้ดูแลโดย {owner}" if lang == "th"
            else f"This case is assigned to {owner}.")


def _answer_contact(case: dict, lang: str, msg_low: str) -> str:
    last = _last_contact(case)
    if not last:
        return INSUFFICIENT_TH if lang == "th" else INSUFFICIENT_EN
    channel = last.get("channel") or last.get("contact_category") or "\u2014"
    when = _fmt(last.get("contact_at", ""))
    summary = last.get("message_summary", "")
    sentiment = last.get("sentiment_label", "")
    facebook_note = ""
    if "facebook" in msg_low:
        facebook_note = ("\u0e44\u0e21\u0e48\u0e21\u0e35\u0e0a\u0e48\u0e2d\u0e07\u0e17\u0e32\u0e07 Facebook \u0e43\u0e19\u0e0a\u0e38\u0e14\u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25\u0e19\u0e35\u0e49 "
                         if lang == "th" else
                         "There is no Facebook channel in this dataset. ")
    if lang == "th":
        return (f"{facebook_note}การติดต่อล่าสุดมาทาง {channel} เมื่อ {when} สรุปข้อความ: "
                f"\"{summary}\" (ความรู้สึก: {sentiment})")
    return (f"{facebook_note}The last contact was via {channel} on {when}. Summary: "
            f"\"{summary}\" (sentiment: {sentiment}).")


def _answer_documents(case: dict, lang: str) -> str:
    required = case.get("required_documents") or []
    if not required and not (case.get("documents_received") or []):
        return INSUFFICIENT_TH if lang == "th" else INSUFFICIENT_EN
    missing = _missing_docs(case)
    received = case.get("documents_received") or []
    if lang == "th":
        body = f"เอกสารที่ต้องใช้: {', '.join(required) or '—'} รับแล้ว: {', '.join(received) or '—'}"
        body += f" ยังขาด: {', '.join(missing)}" if missing else " ครบแล้ว"
        return body
    body = (f"Required: {', '.join(required) or '—'}. "
            f"Received: {', '.join(received) or '—'}.")
    body += f" Missing: {', '.join(missing)}." if missing else " Nothing is missing."
    return body


def _answer_sla(case: dict, lang: str) -> str:
    if not case.get("sla_target_hours"):
        return INSUFFICIENT_TH if lang == "th" else INSUFFICIENT_EN
    hrs = case.get("hours_elapsed")
    target = case.get("sla_target_hours")
    breached = case.get("sla_breached")
    if lang == "th":
        return (f"ผ่านมา {hrs} ชม. เทียบเป้าหมาย {target} ชม. สำหรับเคส {case.get('journey_type','')} "
                f"สถานะ SLA: {'เกินกำหนด' if breached else 'อยู่ในเกณฑ์'}")
    return (f"{hrs}h have elapsed against a {target}h target for this "
            f"{case.get('journey_type', '')} case, so the SLA is "
            f"{'breached' if breached else 'within target'}.")


def _answer_flags(case: dict, lang: str) -> str:
    flags = case.get("flags") or []
    if not flags:
        return ("เคสนี้ไม่มีธงแจ้งเตือน" if lang == "th"
                else "No flags are recorded on this case.")
    parts = []
    for f in flags:
        conf = f.get("confidence", "")
        ev = f.get("evidence", "")
        parts.append(f"{f.get('issue_type')} [{conf}] \u2014 {ev}")
    if lang == "th":
        return f"เคสนี้มี {len(flags)} ธง: " + "; ".join(parts)
    return f"This case has {len(flags)} flag(s): " + "; ".join(parts)


def _answer_payment(case: dict, lang: str) -> str:
    status = str(case.get("payment_status") or "").strip()
    if not status:
        return INSUFFICIENT_TH if lang == "th" else INSUFFICIENT_EN
    return (f"\u0e2a\u0e16\u0e32\u0e19\u0e30\u0e01\u0e32\u0e23\u0e0a\u0e33\u0e23\u0e30\u0e40\u0e07\u0e34\u0e19: {status}" if lang == "th"
            else f"Payment status is '{status}'.")


def _answer_status(case: dict, lang: str) -> str:
    status = str(case.get("current_status") or "").strip()
    if not status:
        return (f"{INSUFFICIENT_TH} \u2014 \u0e2a\u0e16\u0e32\u0e19\u0e30\u0e27\u0e48\u0e32\u0e07" if lang == "th"
                else f"{INSUFFICIENT_EN} -- the current status is blank.")
    if lang == "th":
        return (f"สถานะปัจจุบัน '{status}' ({case.get('journey_type','')} ไป {case.get('destination_country','')}) "
                f"เปิดเคสเมื่อ {_fmt(case.get('case_created_at',''))} รวม {case.get('days_open')} วัน")
    return (f"Current status is '{status}' ({case.get('journey_type', '')} to "
            f"{case.get('destination_country', '')}), opened "
            f"{_fmt(case.get('case_created_at', ''))} ({case.get('days_open')} days ago).")


def _answer_destination(case: dict, lang: str) -> str:
    dest = str(case.get("destination_country") or "").strip()
    return (f"\u0e1b\u0e25\u0e32\u0e22\u0e17\u0e32\u0e07\u0e04\u0e37\u0e2d {dest}" if lang == "th" else f"The destination is {dest}.") \
        if dest else (INSUFFICIENT_TH if lang == "th" else INSUFFICIENT_EN)


def _answer_reviews(case: dict, lang: str) -> str:
    reviews = case.get("reviews") or []
    if not reviews:
        return ("เคสนี้ไม่มีรีวิว" if lang == "th" else "No reviews are on file for this case.")
    bits = [f"{r.get('rating')}\u2605 {r.get('review_text','')}" for r in reviews]
    return ("; ".join(bits))


def _answer_summary(case: dict, lang: str) -> str:
    status = str(case.get("current_status") or "").strip()
    contacts = case.get("contacts") or []
    if not status and not contacts:
        return INSUFFICIENT_TH if lang == "th" else INSUFFICIENT_EN
    flags = len(case.get("flags") or [])
    last = _last_contact(case)
    last_txt = (f"last contact via {last.get('channel')} on {_fmt(last.get('contact_at',''))}"
                if last else "no contact recorded")
    if lang == "th":
        return (f"เคส {case.get('case_id')} ({case.get('journey_type','')}) สถานะ '{status or 'ไม่มีสถานะ'}' "
                f"มี {flags} ธง · {last_txt} · ผ่านมา {case.get('hours_elapsed')} ชม. เทียบเป้า {case.get('sla_target_hours')} ชม.")
    return (f"Case {case.get('case_id')} ({case.get('journey_type', '')}) is "
            f"'{status or 'no status'}' with {flags} flag(s); {last_txt}; "
            f"{case.get('hours_elapsed')}h elapsed vs {case.get('sla_target_hours')}h target.")


def answer(case: dict, message: str, history: list[dict] | None = None) -> str:
    """Deterministic, grounded, read-only answer for one case."""
    lang = "th" if _has_thai(message) else "en"
    msg = (message or "").lower()
    this_id = case.get("case_id", "")
    insufficient = INSUFFICIENT_TH if lang == "th" else INSUFFICIENT_EN

    # 1. scoped to one case --------------------------------------------------
    ids = {m.upper() for m in CASE_ID_RE.findall(message or "")}
    other = [i for i in ids if i.upper() != this_id.upper()]
    if other or _has(message, ["\u0e40\u0e04\u0e2a\u0e2d\u0e37\u0e48\u0e19", "other case", "another case", "different case"]):
        if lang == "th":
            return (f"แชทนี้ตอบได้เฉพาะเคส {this_id} ที่เปิดอยู่เท่านั้น "
                    f"หากต้องการถามถึงเคสอื่น กรุณาเปิดเคสนั้นก่อน")
        return (f"This chat is scoped to the open case ({this_id}) only. "
                f"Open {', '.join(other) if other else 'that case'} first to ask about it.")

    # 2. read-only refusal ---------------------------------------------------
    asked_who = _has(msg, ["who ", "\u0e43\u0e04\u0e23"]) and not _has(msg, KW["action"][:1])
    if _has(msg, KW["action"]) and not asked_who:
        return _refusal(case, lang)

    # 3. transport -----------------------------------------------------------
    if _has(msg, KW["transport"]):
        return _answer_transport(case, lang)

    # 4. owner ---------------------------------------------------------------
    if _has(msg, KW["owner"]):
        return _answer_owner(case, lang)

    # 5. contact / channel ---------------------------------------------------
    if _has(msg, KW["contact"]):
        return _answer_contact(case, lang, msg)

    # 6. documents -----------------------------------------------------------
    if _has(msg, KW["documents"]):
        return _answer_documents(case, lang)

    # 7. SLA -----------------------------------------------------------------
    if _has(msg, KW["sla"]):
        return _answer_sla(case, lang)

    # 8. flags ---------------------------------------------------------------
    if _has(msg, KW["flags"]):
        return _answer_flags(case, lang)

    # 9. payment -------------------------------------------------------------
    if _has(msg, KW["payment"]):
        return _answer_payment(case, lang)

    # 10. status -------------------------------------------------------------
    if _has(msg, KW["status"]):
        return _answer_status(case, lang)

    # 11. destination --------------------------------------------------------
    if _has(msg, KW["destination"]):
        return _answer_destination(case, lang)

    # 12. reviews ------------------------------------------------------------
    if _has(msg, KW["reviews"]):
        return _answer_reviews(case, lang)

    # 13. general summary ----------------------------------------------------
    if _has(msg, KW["summary"]):
        return _answer_summary(case, lang)

    # 14. nothing grounded ---------------------------------------------------
    return insufficient


def answer_llm(case: dict, message: str, history: list[dict] | None,
               llm_fn: Callable[[list[dict]], str]) -> str:
    """Live-LLM path: same context, same validator, safe fallback on violation."""
    reply = llm_fn(build_messages(case, message, history))
    ok, _ = validate_chat_reply(case, message, reply)
    if not ok:
        return answer(case, message, history)
    return reply


# --------------------------------------------------------------------------- #
# Post-generation safety boundary for chat replies
# --------------------------------------------------------------------------- #
DONE_CLAIMS = (
    "has been sent", "i have sent", "i sent it", "already sent", "has been approved",
    "i approved", "i have approved", "booking confirmed", "i have rebooked",
    "i rebooked", "has been rebooked", "i've sent", "i've approved", "done.",
)


def validate_chat_reply(case: dict, question: str, reply: str) -> tuple[bool, list[str]]:
    """Re-check the hard rules on any reply (text, LLM or deterministic)."""
    reasons: list[str] = []
    if not isinstance(reply, str) or not reply.strip():
        return False, ["empty reply"]

    low = reply.lower()
    c = _conflict_of(case)
    owner = str(case.get("case_owner_staff_id") or "").strip()
    q = (question or "").lower()

    # Rule A: never claim an action happened.
    for bad in DONE_CLAIMS:
        if bad in low:
            reasons.append(f"reply implies an action already happened: '{bad}'")

    # Rule B: action requests must be refused, pointing at the Approve button.
    if _has(q, KW["action"]) and not _has(q, ["who ", "\u0e43\u0e04\u0e23"]):
        if "approve" not in low:
            reasons.append("action request not refused via the Approve button")

    # Rule C: transport conflict -> if transport is discussed, both values + confirm.
    transport_words = ["airport", "transport", "itinerary", "rebook", "booking", "flight", "pickup"]
    if c["conflict"] and _has(low, transport_words):
        both = (c["itinerary_value"].lower() in low) and (c["internal_note_value"].lower() in low)
        if not both:
            reasons.append("transport conflict but both values not stated")
        if not ("confirm" in low or "\u0e22\u0e37\u0e19\u0e22\u0e31\u0e19" in reply):
            reasons.append("transport conflict but no human-confirmation wording")

    # Rule D: blank owner -> never name a staff id.
    if not owner and STAFF_ID_RE.search(reply):
        reasons.append("blank owner but reply names a staff id")

    return (len(reasons) == 0), reasons
