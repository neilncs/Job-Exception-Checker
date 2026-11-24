"""Test the contract between the checker and Claude: validate_actions.py must accept a
complete, well-formed actions.json and reject each kind of incomplete or malformed one.

Usage:
    python scripts/test_actions_validator.py
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from validate_actions import validate  # noqa: E402

AS_OF = "2026-11-23"


def main():
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "run_checks.py"), "--as-of", AS_OF, "--out", tmp],
                       check=True, capture_output=True)
        facts = json.loads((Path(tmp) / AS_OF / "exceptions.json").read_text(encoding="utf-8"))

    keys = [e["key"] for e in facts["exceptions"]]
    good = {
        "as_of": AS_OF,
        "actions": [{"key": e["key"], "cause": "Unclear", "owner_group": "Office", "owner": "Office",
                     "priority": i + 1, "next_action": "Check the record.",
                     "decision_needed": e["needs_human_review"],
                     "decision": "Which record is right?" if e["needs_human_review"] else ""}
                    for i, e in enumerate(facts["exceptions"])],
        "root_causes": [{"cause": "Unclear", "keys": keys, "pattern": "Test.", "upstream_fix": "Test fix."}],
    }
    review_key = next(e["key"] for e in facts["exceptions"] if e["needs_human_review"])

    def broken(fn):
        a = copy.deepcopy(good); fn(a); return a

    cases = [
        ("Complete, well-formed output is accepted", good, True),
        ("An exception with no action is rejected", broken(lambda a: a["actions"].pop()), False),
        ("A duplicated action is rejected", broken(lambda a: a["actions"].append(a["actions"][0])), False),
        ("An action for an exception that doesn't exist is rejected",
         broken(lambda a: a["actions"].append({**a["actions"][0], "key": "SJ-9999|A1|x"})), False),
        ("A cause outside the fixed list is rejected", broken(lambda a: a["actions"][0].update(cause="Bad luck")), False),
        ("A blank next action is rejected", broken(lambda a: a["actions"][0].update(next_action=" ")), False),
        ("A review item not marked as a decision is rejected",
         broken(lambda a: next(x for x in a["actions"] if x["key"] == review_key).update(decision_needed=False)), False),
        ("The wrong date is rejected", broken(lambda a: a.update(as_of="2026-01-01")), False),
        ("An exception missing from the root-cause groups is rejected",
         broken(lambda a: a["root_causes"][0]["keys"].pop()), False),
        ("A root-cause group with no upstream fix is rejected",
         broken(lambda a: a["root_causes"][0].update(upstream_fix="")), False),
    ]
    results = [(name, (not validate(facts, data)) == expect_valid) for name, data, expect_valid in cases]
    print("Actions validator tests\n")
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    passed = all(ok for _, ok in results)
    print(f"\nResult: {'PASS' if passed else 'FAIL'} ({sum(ok for _, ok in results)}/{len(results)})")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
