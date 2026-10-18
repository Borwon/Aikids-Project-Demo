"""Loading helpers for cases.json -- used by the tests, the audit, and the server."""

from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
CASES_JSON = os.path.join(ROOT, "data", "cases.json")


def load_cases(path: str = CASES_JSON) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)
    if isinstance(payload, dict) and "cases" in payload:
        return payload["cases"]
    return payload


def load_meta(path: str = CASES_JSON) -> dict:
    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)
    if isinstance(payload, dict):
        return {k: v for k, v in payload.items() if k != "cases"}
    return {}


def get_case(cases: list[dict], case_id: str) -> dict:
    for c in cases:
        if c["case_id"] == case_id:
            return c
    raise KeyError(case_id)
