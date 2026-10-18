"""VisaConnect Case Copilot -- zero-dependency app server (stdlib only).

Serves the three-screen frontend from `app/`, exposes `data/cases.json`, and
provides the small write API the human-in-the-loop rule needs:

  GET  /api/cases                 -> cases.json
  GET  /api/approvals             -> the approval log (JSON array)
  POST /api/approvals             -> append one approve|edit|reject entry
  GET  /api/draft?case_id=VC-...  -> regenerate a draft live for one case
  GET  /api/bias                  -> fairness audit stats (from bias_audit.csv)

Everything is append-only on disk: approvals land in data/approval_log.jsonl
and are never overwritten. Nothing here transmits anything anywhere.

Run:  python server.py   then open http://127.0.0.1:8000
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(HERE, "app")
DATA_DIR = os.path.join(HERE, "data")
CASES_JSON = os.path.join(DATA_DIR, "cases.json")
APPROVAL_LOG = os.path.join(DATA_DIR, "approval_log.jsonl")
BIAS_CSV = os.path.join(DATA_DIR, "bias_audit.csv")

sys.path.insert(0, HERE)
from copilot.chat import answer as chat_answer, validate_chat_reply  # noqa: E402
from copilot.conversation import build_thread  # noqa: E402
from copilot.data import load_cases  # noqa: E402
from copilot.draft import generate_draft, validate_draft, build_llm_payload  # noqa: E402

VALID_ACTIONS = {"approve", "edit", "reject"}
CHAT_PATH_RE = re.compile(r"^/cases/([^/]+)/chat$")
CUSTMSG_PATH_RE = re.compile(r"^/cases/([^/]+)/customer-messages$")
CUSTOMER_MSG_LOG = os.path.join(DATA_DIR, "customer_messages.jsonl")


def read_approvals() -> list[dict]:
    if not os.path.exists(APPROVAL_LOG):
        return []
    out = []
    with open(APPROVAL_LOG, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def append_approval(entry: dict) -> dict:
    entry = {
        "ts": entry.get("ts") or datetime.now().isoformat(timespec="seconds"),
        "case_id": entry.get("case_id", ""),
        "staff_id": entry.get("staff_id", ""),
        "action": entry.get("action", ""),
        "ai_output": entry.get("ai_output", {}),
        "final_output": entry.get("final_output", {}),
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(APPROVAL_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_customer_messages(case_id: str | None = None) -> list[dict]:
    if not os.path.exists(CUSTOMER_MSG_LOG):
        return []
    out = []
    with open(CUSTOMER_MSG_LOG, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                entry = json.loads(line)
                if case_id is None or entry.get("case_id") == case_id:
                    out.append(entry)
    return out


def append_customer_message(entry: dict) -> dict:
    entry = {
        "ts": entry.get("ts") or datetime.now().isoformat(timespec="seconds"),
        "case_id": entry.get("case_id", ""),
        "staff_id": entry.get("staff_id", ""),
        "channel": entry.get("channel", ""),
        "text": entry.get("text", ""),
        "direction": "outbound",
        "sent": False,
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CUSTOMER_MSG_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def bias_stats() -> dict:
    if not os.path.exists(BIAS_CSV):
        return {"cases_audited": 0, "comparisons": 0, "differences": 0, "pass_rate": 100.0}
    with open(BIAS_CSV, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    comparisons = len(rows)
    differences = sum(1 for r in rows if r["match"] == "fail")
    cases = {r["case_id"] for r in rows}
    cases_pass = len([c for c in cases if all(
        r["match"] == "pass" for r in rows if r["case_id"] == c)])
    return {
        "cases_audited": len(cases),
        "cases_all_pass": cases_pass,
        "comparisons": comparisons,
        "differences": differences,
        "pass_rate": round(100.0 * (comparisons - differences) / comparisons, 1) if comparisons else 100.0,
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=APP_DIR, **kwargs)

    def log_message(self, fmt, *args):  # quieter console
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    # -- helpers -------------------------------------------------------------
    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._json({"error": "invalid json"}, 400)
            return None

    def _find_case(self, case_id):
        try:
            return next(c for c in load_cases() if c["case_id"] == case_id)
        except StopIteration:
            return None

    # -- POST /cases/{case_id}/chat -----------------------------------------
    def _handle_chat(self, case_id):
        body = self._read_json()
        if body is None:
            return
        message = str(body.get("message", "")).strip()
        history = body.get("history") or []
        if not isinstance(history, list):
            history = []
        if not message:
            self._json({"error": "message required"}, 400)
            return
        case = self._find_case(case_id)
        if case is None:
            self._json({"error": "unknown case_id"}, 404)
            return
        reply = chat_answer(case, message, history)
        ok, reasons = validate_chat_reply(case, message, reply)
        self._json({"reply": reply, "validator": {"ok": ok, "reasons": reasons}})

    # -- GET /cases/{case_id}/customer-messages -----------------------------
    def _handle_customer_get(self, case_id):
        case = self._find_case(case_id)
        if case is None:
            self._json({"error": "unknown case_id"}, 404)
            return
        self._json({"thread": build_thread(case, read_customer_messages(case_id))})

    # -- POST /cases/{case_id}/customer-messages ----------------------------
    def _handle_customer_post(self, case_id):
        body = self._read_json()
        if body is None:
            return
        text = str(body.get("text", "")).strip()
        if not text:
            self._json({"error": "text required"}, 400)
            return
        case = self._find_case(case_id)
        if case is None:
            self._json({"error": "unknown case_id"}, 404)
            return
        entry = append_customer_message({
            "case_id": case_id,
            "staff_id": body.get("staff_id", ""),
            "channel": body.get("channel", ""),
            "text": text,
        })
        self._json({
            "ok": True,
            "entry": entry,
            "thread": build_thread(case, read_customer_messages(case_id)),
        }, 201)

    def _serve_data_file(self, name):
        path = os.path.join(DATA_DIR, os.path.basename(name))
        if not os.path.exists(path):
            self.send_error(404, "not found")
            return
        with open(path, "rb") as fh:
            body = fh.read()
        ctype = "application/json" if name.endswith(".json") else "text/plain"
        self.send_response(200)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # -- GET -----------------------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/cases":
            self._json(json.load(open(CASES_JSON, encoding="utf-8")))
            return
        if path == "/api/approvals":
            self._json(read_approvals())
            return
        if path == "/api/bias":
            self._json(bias_stats())
            return

        cust = CUSTMSG_PATH_RE.match(path)
        if cust:
            self._handle_customer_get(cust.group(1))
            return

        if path == "/api/draft":
            qs = parse_qs(parsed.query)
            case_id = (qs.get("case_id") or [""])[0]
            try:
                case = next(c for c in load_cases() if c["case_id"] == case_id)
            except StopIteration:
                self._json({"error": "unknown case_id"}, 404)
                return
            draft = generate_draft(case)
            ok, reasons = validate_draft(build_llm_payload(case), draft)
            self._json({"case_id": case_id, "draft": draft,
                        "validator": {"ok": ok, "reasons": reasons}})
            return
        if path.startswith("/data/"):
            self._serve_data_file(path[len("/data/"):])
            return

        # static frontend
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()

    # -- POST ----------------------------------------------------------------
    def do_POST(self):
        parsed = urlparse(self.path)

        m = CHAT_PATH_RE.match(parsed.path)
        if m:
            self._handle_chat(m.group(1))
            return

        cust = CUSTMSG_PATH_RE.match(parsed.path)
        if cust:
            self._handle_customer_post(cust.group(1))
            return

        if parsed.path != "/api/approvals":
            self._json({"error": "not found"}, 404)
            return

        payload = self._read_json()
        if payload is None:
            return

        action = payload.get("action", "")
        if action not in VALID_ACTIONS:
            self._json({"error": f"action must be one of {sorted(VALID_ACTIONS)}"}, 400)
            return
        if not payload.get("case_id"):
            self._json({"error": "case_id required"}, 400)
            return

        entry = append_approval(payload)
        self._json({"ok": True, "entry": entry}, 201)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"VisaConnect Case Copilot running at http://127.0.0.1:{port}")
    print("Human-in-the-loop: approvals are logged, never transmitted.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
