"""Test that bad input is caught, not crashed on, and never reported as a clean day.

Copies the sample data to a throwaway folder, breaks it on purpose, and checks:

  1. Row-level problems -> reported as X1 "bad or duplicate source record", the
     run still completes, and the broken records don't trigger false alarms.
  2. Fatal problems (missing column, missing file, broken rules) -> the run
     stops with exit code 2, writes INPUT_ERROR.md and does NOT update the run log.

Usage:
    python scripts/test_bad_input.py
"""
from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "data" / "sample"
AS_OF = "2026-11-23"


def run(data, out, rules=None):
    cmd = [sys.executable, str(ROOT / "scripts" / "run_checks.py"), "--as-of", AS_OF, "--data", str(data), "--out", str(out)]
    if rules:
        cmd += ["--rules", str(rules)]
    return subprocess.run(cmd, capture_output=True, text=True)


def edit_csv(path, fn):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    fields, rows = fn(fields, rows)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    results = []

    def check(name, ok, detail=""):
        results.append((name, ok, detail))

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # ---- 1. Row-level problems ------------------------------------------------
        data = tmp / "rows"
        shutil.copytree(SAMPLE, data)

        def tracker(fields, rows):
            for r in rows:
                if r["job_id"] == "SJ-1001":
                    r["date_survey"] = "31/02/2026"          # UK-style, invalid date
                if r["job_id"] == "SJ-1022":
                    r["panel_count"] = "twelve"              # not a number
            rows.append(dict(next(r for r in rows if r["job_id"] == "SJ-1040")))  # duplicate job ID
            return fields, rows

        def invoices(fields, rows):
            for r in rows:
                if r["job_id"] == "SJ-1001" and r["item"] == "MK-ROOF":
                    r["quantity"] = "-3"                     # negative quantity
            return fields, rows

        def records(fields, rows):
            rows.append(dict(next(r for r in rows if r["job_id"] == "SJ-1035")))  # duplicate install record
            return fields, rows

        edit_csv(data / "job_tracker.csv", tracker)
        edit_csv(data / "supplier_invoices.csv", invoices)
        edit_csv(data / "installation_records.csv", records)

        out = tmp / "out_rows"
        p = run(data, out)
        check("Row-level problems: run completes (exit 0, no crash)", p.returncode == 0, p.stderr.strip()[-200:])
        if p.returncode == 0:
            ex = json.loads((out / AS_OF / "exceptions.json").read_text(encoding="utf-8"))["exceptions"]
            x1 = {(e["job_id"], e["context"].get("source_file")) for e in ex if e["check"] == "X1"}
            for job, file, label in [("SJ-1001", "job_tracker.csv", "invalid date 31/02/2026"),
                                     ("SJ-1022", "job_tracker.csv", "non-numeric panel count"),
                                     ("SJ-1040", "job_tracker.csv", "duplicate job ID"),
                                     ("SJ-1001", "supplier_invoices.csv", "negative invoice quantity"),
                                     ("SJ-1035", "installation_records.csv", "duplicate installation record")]:
                check(f"Caught: {label} ({job})", (job, file) in x1)
            # Quarantined records must not cause knock-on false alarms
            knock_on = [e["key"] for e in ex if e["job_id"] in ("SJ-1001", "SJ-1022", "SJ-1040", "SJ-1035")
                        and e["check"] != "X1"]
            check("No false alarms from quarantined records (e.g. 'invoice for unknown job')", not knock_on,
                  ", ".join(knock_on))
            planted = {r["key"] for r in csv.DictReader(open(SAMPLE / "answer_key.csv", encoding="utf-8"))}
            still = planted <= {e["key"] for e in ex}
            check("All 22 planted problems still caught alongside the bad rows", still)

        # ---- 2. Fatal problems --------------------------------------------------------
        def missing_column(fields, rows):
            return [f for f in fields if f != "unit_price_gbp"], rows

        fatal_cases = []
        d = tmp / "nocol"; shutil.copytree(SAMPLE, d)
        edit_csv(d / "supplier_invoices.csv", missing_column)
        fatal_cases.append(("Missing column (unit_price_gbp)", d, None))
        d = tmp / "nofile"; shutil.copytree(SAMPLE, d); (d / "documents_index.csv").unlink()
        fatal_cases.append(("Missing file (documents_index.csv)", d, None))
        bad_rules = tmp / "rules_bad.yaml"
        bad_rules.write_text((ROOT / "config" / "rules.yaml").read_text(encoding="utf-8")
                             .replace("price_over_list_pct: 2.0", "price_over_list_pct: two"), encoding="utf-8")
        fatal_cases.append(("Broken rules file (tolerance 'two')", SAMPLE, bad_rules))

        for label, data_dir, rules in fatal_cases:
            out = tmp / ("out_" + data_dir.name + ("_rules" if rules else ""))
            p = run(data_dir, out, rules)
            note = out / AS_OF / "INPUT_ERROR.md"
            ok = p.returncode == 2 and note.exists() and not (out / "run_log.csv").exists() \
                and "Traceback" not in p.stderr
            check(f"Fatal: {label} -> stops cleanly, explains why, run log untouched", ok,
                  p.stderr.strip().splitlines()[-1] if p.stderr.strip() else "")

    width = max(len(n) for n, _, _ in results)
    print("Bad-input tests\n")
    for name, ok, detail in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {detail if (detail and not ok) or name.startswith('Fatal') else ''}")
    passed = all(ok for _, ok, _ in results)
    print(f"\nResult: {'PASS' if passed else 'FAIL'} ({sum(ok for _, ok, _ in results)}/{len(results)})")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
