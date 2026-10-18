# VisaConnect Case Copilot

An internal staff tool for a *fictional* visa service company. It reads the
synthetic VisaConnect data and helps one staff member work one case at a time:
it summarizes a case, flags anything missing / stale / conflicting, and
recommends a next action or drafts a customer-update message.

**The one rule every screen respects:** the AI only flags and drafts. A staff
member must click **Approve / Edit / Reject** before anything counts as decided.
Nothing here calls a messaging API — there is no live VisaConnect system, since
VisaConnect is fictional. Approvals are logged, never transmitted.

---

## Quickstart

```powershell
python run_pipeline.py      # generate synthetic data -> clean/flag -> cases.json -> bias audit
python -m pytest -q tests   # 5 safety tests + bias audit
python server.py            # http://127.0.0.1:8000
```

No third-party runtime dependencies: the whole pipeline, server and tests run
on the Python standard library. `pytest` is the only optional install
(`pip install pytest`); every test file also runs on its own
(`python tests/test_safety.py`) if you'd rather not install it.

Requirements: Python 3.10+ (developed on 3.14).

---

## Project layout

```
scripts/
  generate_synthetic_data.py   Stage 1 raw data  -> data/raw/*.csv
  clean_data.py                Stage 2 clean+flag -> data/clean/*.csv (+ issue_log, sla_breach_analysis)
  build_cases_json.py          Stage 3 join       -> data/cases.json (app-ready, drafts pre-baked)
  run_bias_audit.py                               -> data/bias_audit.csv
copilot/
  draft.py                     payload builder + deterministic draft engine + hard-rule validator
  bias_audit.py                nationality/language swap harness
  data.py                      cases.json loaders
app/                           three-screen frontend (no framework, no CDN)
  index.html                   Case List
  case.html                    Case Copilot (detail)
  log.html                     Approval Log
server.py                      stdlib HTTP server + approvals/draft/bias API
run_pipeline.py                runs all four pipeline steps in order
tests/                         5 safety tests + bias audit test
data/                          raw/, clean/, cases.json, approval_log.jsonl, bias_audit.csv
```

---

## The pipeline (3 stages)

1. **Raw** — `visa_cases.csv`, `customer_contacts.csv`, `transport_bookings.csv`,
   `customer_reviews.csv`, plus reference files `service_catalog_sla.csv` and
   `DATA_DICTIONARY.csv`. VisaConnect is fictional, so these are generated with a
   fixed seed and planted edge cases (airport conflicts, blank owners, timestamp
   conflicts, ambiguous cases, a spread of nationalities/languages).
2. **Clean/flag** — nothing is altered; the `*_flagged.csv` files carry the
   originals plus `flags` / `has_flag`. Also emits `issue_log.csv` (one row per
   issue, with evidence) and `sla_breach_analysis.csv`.
3. **App-ready** — one object per case in `cases.json`: case fields, linked
   contacts / transport / reviews, its flags, its SLA numbers, and a **pre-baked
   draft** so the static frontend renders without a live model call.

The frontend reads only `cases.json` (via `/api/cases`); it never touches raw CSVs.

---

## Draft generation

`copilot/draft.py` implements the exact contract the build plan specifies, but the
model is a **pure function** so the whole thing runs offline, instantly, and
deterministically.

- **Input** to the model is a structured JSON block built only from `cases.json`
  fields. `customer_nationality` and `message_language` are **hard-excluded in
  `build_llm_payload`** — the mechanism, not a policy note. The generator only
  ever reads the payload, so it cannot bias on what it never receives.
- **Output** is strict JSON: `summary`, `flags[]` (each tagged
  `confirmed` / `conflicting` / `insufficient`), `recommended_action`,
  `draft_message`, `confidence_overall`, `insufficient_information`.
- **Hard rules:** transport conflict → say the destination needs confirmation,
  never state an airport as correct, recommended action is "confirm with
  customer". Blank owner → flag it, name no one. Missing required fields →
  output says `insufficient information to recommend an action` instead of guessing.
- **Post-generation validator** (`validate_draft`) re-checks those rules after
  generation and rejects/regenerates violations. This is the real safety boundary
  — a prompt can be ignored, this check cannot.

Swap in a live model later with `generate_draft_llm(case, llm_fn)`: same payload,
same validator, same screens.

---

## Screens

1. **Case List** — sortable/filterable table with SLA badge, flag count and a
   conflict badge. Nationality/language columns are hidden by default behind a
   "show nationality / language columns" toggle.
2. **Case Copilot** — one case, three columns. Left: case identity plus the AI
   **Case Summary** (its numbered key points) and a "full case details" panel that
   opens the raw field dump — nothing is hidden. Centre: the customer conversation
   as a thread, the yellow **AI Suggest Answer** card above the composer
   (`Use this answer` drops the draft into the box, `Edit` and `⋯` are the other two
   decisions). Right: **AI Insights** — key points to watch, recommended next action,
   evidence tags, SLA status and case documents.
   Every AI item has **Approve / Edit / Reject**; nothing leaves the screen until a
   control is clicked. A live `/api/draft` call shows the hard-rule validator status.
3. **Approval Log** — read-only, timestamped audit trail of every decision, with
   the AI's proposal next to the human's final text, plus the fairness badge.

---

## Safety & fairness tests

```powershell
python -m pytest -q tests      # 24 passed
```

| # | Test | File |
|---|---|---|
| 1 | Airport conflict → flags, never picks | `tests/test_safety.py::test_airport_conflict_flags_not_picks` |
| 2 | Blank owner → says so, names no one | `tests/test_safety.py::test_blank_owner_says_so_and_names_no_staff` |
| 3 | Bias — identical cases differing only by nationality/language | `tests/test_safety.py::test_identical_cases_differ_only_by_nationality` |
| 4 | Timestamp conflict (response before creation) is flagged | `tests/test_safety.py::test_timestamp_conflict_is_flagged` |
| 5 | Ambiguous case → literal "insufficient information" | `tests/test_safety.py::test_ambiguous_case_reports_insufficient_information` |
| 3′ | Bias audit, N=20 real cases × every nationality/language | `tests/test_bias_audit.py` |

The bias audit runs 20 real cases through every nationality and language value
and asserts the recommended action, confidence, flags and draft text are
byte-identical across variants. Results land in `data/bias_audit.csv` and the
Approval Log surfaces `20/20 cases · 100%`.

---

## API (stdlib server)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/cases` | `cases.json` |
| GET | `/api/approvals` | the approval log (JSON array) |
| POST | `/api/approvals` | append one `approve` / `edit` / `reject` entry |
| GET | `/api/draft?case_id=VC-00004` | regenerate a draft live + validator status |
| GET | `/api/bias` | fairness audit stats |

`data/approval_log.jsonl` is append-only: one line per action —
`{ ts, case_id, staff_id, action, ai_output, final_output }`. It is never
overwritten and never used as a training signal (explicitly cut scope).
