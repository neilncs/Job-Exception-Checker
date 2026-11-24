"""Validate Claude's structured output (output/<date>/actions.json) against the checker's facts.

Claude's judgement is only accepted if it is complete and well-formed:
  - every exception the checker found has exactly one action, and no action refers to anything else
  - causes and owner groups come from fixed lists, so they can be counted and charted
  - every action has an owner, a priority and a next action
  - every exception the checker flagged for human review is marked as a decision
  - every exception sits in exactly one root-cause group, and each group has an upstream fix

Usage:
    python scripts/validate_actions.py                 # today's run
    python scripts/validate_actions.py --date 2026-11-24
Exit code 0 = valid, 1 = invalid (errors printed), 2 = file missing.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CAUSES = ["Missing paperwork", "Supplier", "Data entry", "Substitution", "Scheduling", "External (DNO)", "Unclear"]
OWNER_GROUPS = ["Office", "Installer team", "Supplier", "Design", "Operations manager"]


def validate(exceptions: dict, actions: dict) -> list[str]:
    """Return a list of problems; empty means valid."""
    errors = []
    if not isinstance(actions, dict):
        return ["actions.json is not a JSON object"]
    if actions.get("as_of") != exceptions.get("as_of"):
        errors.append(f"as_of is {actions.get('as_of')!r}, expected {exceptions.get('as_of')!r}")

    facts = {e["key"]: e for e in exceptions.get("exceptions", [])}
    acts = actions.get("actions")
    if not isinstance(acts, list):
        return errors + ["'actions' must be a list"]

    counts = Counter(a.get("key") for a in acts if isinstance(a, dict))
    for key in facts:
        if counts[key] == 0:
            errors.append(f"no action for exception {key}")
        elif counts[key] > 1:
            errors.append(f"{counts[key]} actions for exception {key} (expected 1)")
    for key in counts:
        if key not in facts:
            errors.append(f"action refers to unknown exception {key!r}")

    for a in acts:
        if not isinstance(a, dict):
            errors.append("an action is not an object"); continue
        k = a.get("key", "?")
        if a.get("cause") not in CAUSES:
            errors.append(f"{k}: cause {a.get('cause')!r} is not one of {CAUSES}")
        if a.get("owner_group") not in OWNER_GROUPS:
            errors.append(f"{k}: owner_group {a.get('owner_group')!r} is not one of {OWNER_GROUPS}")
        if not str(a.get("owner", "")).strip():
            errors.append(f"{k}: owner is blank")
        if not str(a.get("next_action", "")).strip():
            errors.append(f"{k}: next_action is blank")
        if not (isinstance(a.get("priority"), int) and a["priority"] >= 1):
            errors.append(f"{k}: priority must be a whole number from 1")
        if k in facts and facts[k]["needs_human_review"] and a.get("decision_needed") is not True:
            errors.append(f"{k}: flagged for human review by the checker, so decision_needed must be true")
        if a.get("decision_needed") is True and not str(a.get("decision", "")).strip():
            errors.append(f"{k}: decision_needed is true but no decision question is given")

    groups = actions.get("root_causes")
    if not isinstance(groups, list) or not groups:
        errors.append("'root_causes' must be a non-empty list")
    else:
        grouped = Counter()
        for g in groups:
            if g.get("cause") not in CAUSES:
                errors.append(f"root cause group {g.get('cause')!r} is not one of {CAUSES}")
            if not str(g.get("upstream_fix", "")).strip():
                errors.append(f"root cause group {g.get('cause')!r} has no upstream_fix")
            grouped.update(g.get("keys", []))
        for key in facts:
            if grouped[key] != 1:
                errors.append(f"{key} appears in {grouped[key]} root-cause groups (expected 1)")
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--out", default=str(ROOT / "output"))
    args = ap.parse_args()
    run_dir = Path(args.out) / args.date
    exc_path, act_path = run_dir / "exceptions.json", run_dir / "actions.json"
    if not exc_path.exists() or not act_path.exists():
        print(f"MISSING: {exc_path if not exc_path.exists() else act_path}")
        return 2
    try:
        actions = json.loads(act_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"INVALID: actions.json is not valid JSON ({e})")
        return 1
    errors = validate(json.loads(exc_path.read_text(encoding="utf-8")), actions)
    if errors:
        print(f"INVALID: {len(errors)} problem(s) in actions.json")
        for e in errors[:25]:
            print("  - " + e)
        return 1
    print(f"VALID: actions.json covers all {len(actions['actions'])} exceptions in "
          f"{len(actions['root_causes'])} root-cause groups")
    return 0


if __name__ == "__main__":
    sys.exit(main())
