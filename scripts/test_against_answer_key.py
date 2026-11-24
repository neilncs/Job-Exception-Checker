"""Test the checker against the planted-problem answer key.

Runs run_checks.py on data/sample into a throwaway folder (so the real run log
is not touched), then compares every exception key with answer_key.csv.

Pass = every planted problem caught AND no exception on anything not planted.

Usage:
    python scripts/test_against_answer_key.py            # as of 2026-11-23 (the sample date)
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default="2026-11-23")
    ap.add_argument("--data", default=str(ROOT / "data" / "sample"))
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "run_checks.py"), "--as-of", args.as_of,
                        "--data", args.data, "--out", tmp], check=True, capture_output=True, text=True)
        found = json.loads((Path(tmp) / args.as_of / "exceptions.json").read_text(encoding="utf-8"))

    with open(Path(args.data) / "answer_key.csv", newline="", encoding="utf-8") as f:
        planted = {r["key"]: r for r in csv.DictReader(f)}
    with open(Path(args.data) / "job_tracker.csv", newline="", encoding="utf-8") as f:
        all_jobs = [r["job_id"] for r in csv.DictReader(f)]

    found_keys = {e["key"]: e for e in found["exceptions"]}
    caught = [k for k in planted if k in found_keys]
    missed = [k for k in planted if k not in found_keys]
    false_alarms = [k for k in found_keys if k not in planted]
    planted_jobs = {r["job_id"] for r in planted.values()}
    clean_jobs = [j for j in all_jobs if j not in planted_jobs]
    flagged_clean = sorted({found_keys[k]["job_id"] for k in false_alarms} & set(clean_jobs))

    lines = [f"# Test against answer key (as of {args.as_of})", "",
             f"- Planted problems: {len(planted)}",
             f"- Caught: {len(caught)} / {len(planted)} ({100 * len(caught) / max(len(planted), 1):.0f}%)",
             f"- Missed: {len(missed)}",
             f"- False alarms (exceptions not in answer key): {len(false_alarms)}",
             f"- Clean jobs: {len(clean_jobs)}, of which flagged: {len(flagged_clean)}",
             "", "| Planted problem | Check | Caught? |", "|---|---|---|"]
    for k, r in planted.items():
        lines.append(f"| {r['job_id']}: {r['description']} | {r['check']} | {'yes' if k in found_keys else '**MISSED**'} |")
    if false_alarms:
        lines += ["", "## False alarms", ""]
        lines += [f"- `{k}`: {found_keys[k]['what_is_wrong']}" for k in false_alarms]
    passed = not missed and not false_alarms
    lines += ["", f"**Result: {'PASS' if passed else 'FAIL'}**"]
    report = "\n".join(lines) + "\n"
    (ROOT / "output").mkdir(exist_ok=True)
    (ROOT / "output" / "test_results.md").write_text(report, encoding="utf-8")
    print(report)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
