"""One-command pipeline: generate -> clean -> build -> audit.

Run:  python run_pipeline.py
Then: python server.py   and open http://127.0.0.1:8000
"""

from __future__ import annotations

import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    "scripts/generate_synthetic_data.py",
    "scripts/clean_data.py",
    "scripts/build_cases_json.py",
    "scripts/run_bias_audit.py",
]


def main() -> int:
    for step in STEPS:
        print(f"\n=== {step} ===")
        code = subprocess.call([sys.executable, os.path.join(HERE, step)], cwd=HERE)
        if code != 0:
            print(f"FAILED: {step} (exit {code})")
            return code
    print("\nPipeline complete. Start the app with:  python server.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
