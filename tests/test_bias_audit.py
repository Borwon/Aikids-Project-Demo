"""Bias audit as a test: N=20 real cases, every nationality/language swap.

Run with pytest:      pytest -q tests/test_bias_audit.py
Run without pytest:   python tests/test_bias_audit.py
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from copilot.bias_audit import run_audit  # noqa: E402
from copilot.data import CASES_JSON, load_cases  # noqa: E402


def test_bias_audit_has_zero_differences():
    cases = load_cases(CASES_JSON)
    rows, stats = run_audit(cases, n=20)
    assert stats["cases_audited"] == 20
    assert stats["differences"] == 0, [r for r in rows if r["match"] == "fail"][:3]
    assert stats["pass_rate"] == 100.0


if __name__ == "__main__":
    test_bias_audit_has_zero_differences()
    print("PASS  test_bias_audit_has_zero_differences")
