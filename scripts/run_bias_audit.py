"""Run the bias audit over the real cases and emit data/bias_audit.csv.

Run:  python scripts/run_bias_audit.py [N]
Out:  data/bias_audit.csv
"""

from __future__ import annotations

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)

from copilot.bias_audit import run_audit  # noqa: E402
from copilot.data import CASES_JSON, load_cases  # noqa: E402


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    cases = load_cases()
    rows, stats = run_audit(cases, n=n)

    out = os.path.join(ROOT, "data", "bias_audit.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["case_id", "variant_field", "variant_value", "match", "diff"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Fairness audit: {stats['cases_all_pass']}/{stats['cases_audited']} cases, "
          f"{stats['comparisons']} comparisons, {stats['differences']} bias differences "
          f"({stats['pass_rate']}% pass)")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
