---
name: solar-job-exceptions
description: Daily exceptions review for a UK solar PV and battery installer. Reconciles the job tracker, installation records, supplier invoices, agreed price list and compliance documents; classifies every exception by root cause and owner; and produces a prioritised report, a validated actions file and draft chase emails for approval. Use when asked to "run the solar job exceptions check", "check the solar jobs", "reconcile installs and invoices" or "what's stuck or overdue", and for the scheduled daily run. Never sends emails or changes source data.
---

# Solar Job Exceptions Review

The Python checker establishes the facts: every comparison, date difference and sum. Your job is the judgement
an experienced operations manager would add: why each exception happened, who owns it, what to do first, and what
to change upstream so it stops recurring. Then you put it in writing that a busy manager can act on in five minutes.

## Controls

- **Never send anything.** Chase emails are draft files only. Do not use email, Teams or Slack tools.
- **Never change source data** in `data/` or rules in `config/`. Write only inside `output/<date>/`.
- **Never mark anything resolved.** An exception closes only when the source record is fixed and a later run stops finding it.
- **Never alter the facts.** Every exception in `exceptions.json` appears in your output, unchanged. You add judgement; you don't re-score, merge away or drop.
- **Don't guess.** If the evidence doesn't support a conclusion, say what would confirm it and mark the item as a decision. Items the checker flagged `needs_human_review` are always decisions.
- **Thresholds are business settings, not law.** Where `config/rules.yaml` says CHECK, write "check against current ENA/MCS guidance".

## Procedure

Work from the skill folder (the folder containing this file).

1. **Establish the facts.** Run `python scripts/run_checks.py` (add `--as-of YYYY-MM-DD` or `--data <folder>` if given).
   Exit code 2 means an input file is broken and `output/<date>/INPUT_ERROR.md` explains it: report that in one
   paragraph and stop. Any other failure: report it and stop. In scheduled runs this step has already been done; see below.

2. **Read.** `output/<date>/exceptions.json` (facts, `days_open`, `due_by`, `overdue`), the last five rows of
   `output/run_log.csv` (trend), `references/check_definitions.md` (usual causes and owners) and
   `references/writing_standards.md` (how to write).

3. **Classify every exception.** For each one decide:
   - `cause`, exactly one of:
     - `Missing paperwork`: a post-commissioning or closing document not done or not filed
     - `Supplier`: an invoicing or delivery error by a supplier
     - `Data entry`: a typed value or job sheet that's wrong or missing (always the cause for X1)
     - `Substitution`: kit fitted differs from the tracker and may or may not have been approved
     - `Scheduling`: a job waiting on our own planning
     - `External (DNO)`: waiting on the network operator
     - `Unclear`: the evidence supports more than one cause (say which, and what would decide it)
   - `owner_group` (one of `Office`, `Installer team`, `Supplier`, `Design`, `Operations manager`) and `owner`
     (the specific team or company, for example "Installer Team B" or "Kestrel Scaffolding Ltd").
   - `next_action`: one concrete step that starts with a verb and names the reference ("Request a credit note for £1,450.00 against KSL-5328").
   - `priority`: rank all actions 1..n in this order: (1) compliance and safety exposure, (2) customer-facing
     delay, (3) money at risk, largest first, (4) data corrections. Use the checker's `due_by`; don't invent dates.
   - `decision_needed` and `decision`: for anything ambiguous, the single question a person must answer.

4. **Find the root causes.** Group exceptions by cause, largest group first (Pareto). For each group, state the
   pattern in one or two sentences, using only what the data shows (same supplier, same installer team, same
   stage), and **one upstream fix**: a process or system change that would stop the cause recurring.

5. **Write `output/<date>/actions.json`** in exactly this shape:
   ```json
   {"as_of": "YYYY-MM-DD",
    "actions": [{"key": "<exception key>", "cause": "...", "owner_group": "...", "owner": "...", "priority": 1,
                 "next_action": "...", "decision_needed": false, "decision": ""}],
    "root_causes": [{"cause": "...", "keys": ["<exception key>", "..."], "pattern": "...", "upstream_fix": "..."}]}
   ```
   One action per exception and every key in exactly one root-cause group. `scripts/validate_actions.py`
   checks this; output that fails is rejected.

6. **Write `output/<date>/exceptions_report.md`** using `templates/report_template.md`, in its order and headings.
   The register lists every exception, sorted by priority.

7. **Draft chase emails** in `output/<date>/draft_emails/`, one per external supplier or internal team with actions
   to chase, named `to_<owner>.md`, using `templates/chase_email_template.md`.
   - First line exactly: `STATUS: DRAFT - NOT SENT - needs approval`.
   - Quote the job ID, the reference and both values that disagree, and ask for one specific thing by a date
     (the `due_by` date for that item).
   - Leave out anything awaiting a decision. List it as "held pending our review" without detail.
   - Use customer references only, never personal data.

8. **Check your work** before finishing:
   - The register row count equals the number of exceptions.
   - Every figure you quote (counts, £, days) matches `exceptions.json` or `run_log.csv`.
   - There are no claims beyond the evidence, and the writing follows `references/writing_standards.md`.

9. **Finish** with a five-line summary: status, counts (new, carried over, closed), decisions needed, the top three
   actions, and where the files are. State that nothing has been sent.

## Scheduled runs

`scripts/run_daily.ps1` runs step 1 itself, then starts you headless with **no shell access**: you can read files
and write inside `output/` only. When the prompt says the checks have already run:

- Skip step 1. Confirm `output/<date>/exceptions.json` exists with `as_of` equal to that date; if it doesn't, stop and say so.
- Ignore any `RUN_FAILED.md` or `INPUT_ERROR.md` from earlier attempts. The runner manages them.
- Complete steps 2 to 9 without asking questions. Anything that needs a person goes in as a decision.
