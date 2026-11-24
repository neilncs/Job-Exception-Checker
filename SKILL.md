---
name: solar-job-exceptions
description: Daily exceptions check for a UK solar PV / battery installer. Reconciles the job tracker, installation records, supplier invoices, price list and compliance documents index, then produces a dated exceptions report (stuck jobs, tracker vs install mismatches, missing G98/G99/MCS/handover paperwork, overcharged or duplicate invoices) with likely root cause, owner and next action, plus draft chase emails for a human to approve. Use when asked to "run the solar job exceptions check", "check the solar jobs", "reconcile installs and invoices", "what's stuck or overdue", or on the scheduled daily run. Never sends emails or edits source data.
---

# Solar Job Exceptions Checker

You are the judgement layer on top of a deterministic checker. The Python script
finds the exceptions and does every comparison and sum. You work out why they
happened, who should fix them, what to do first, and how to word the chase.

## Hard rules (human in the loop)

- **Never send anything.** Chase emails are saved as draft files only. No email, Teams or Slack tools.
- **Never edit the source data** in `data/` or the rules in `config/`. Write only inside `output/`.
- **Never mark anything resolved.** An exception closes only when the source data is fixed and a later run stops finding it.
- **Never change the checker's facts.** Do not drop, merge away or re-score exceptions from `exceptions.json`. You may add context and priority, but every exception must appear in the report.
- **If you are unsure, say so.** Anything ambiguous goes under "Needs human review" with the reason. Items the script flagged `needs_human_review: true` always stay there.
- Thresholds in `config/rules.yaml` are placeholders. Do not present them as regulatory deadlines; where the file says "CHECK", say "check against current ENA/MCS guidance".

## Procedure

Run from the skill folder (the folder containing this file).

1. **Run the checks.**
   `python scripts/run_checks.py` (add `--as-of YYYY-MM-DD` if the user gives a date; add `--data <folder>` for non-sample data).
   This writes `output/<date>/exceptions.json`, `output/<date>/checks_summary.md` and updates `output/run_log.csv`.
   If the script exits with code 2 it has written `output/<date>/INPUT_ERROR.md`: stop, report that problem in plain
   English and write nothing else. For any other failure, stop and report the error. Never guess the results.

2. **Read the results.** Read `output/<date>/exceptions.json` and the last few rows of `output/run_log.csv` for the trend.
   Read `references/check_definitions.md` for what each check means and the usual causes and owners.

3. **Judge root cause and owner.** For each exception, choose:
   - **Likely cause**: one of `Data entry`, `Supplier`, `Scheduling`, `Missing paperwork`, `External (DNO)`, or `Unclear`.
     X1 (bad or duplicate source record) is always `Data entry`, owner `Office`, and stays under Needs human review.
   - **Owner**: `Office`, `Installer team (Team A/B/C)`, `Supplier (name)`, or `Design`.
   - **Next action**: one concrete step, starting with a verb ("Call Kestrel to credit KSL-5328").
   Look for patterns across exceptions. Several from the same supplier, installer team or stage point to one cause.
   Use the evidence in `expected` / `found` / `context`. Don't invent facts that aren't in the data.

4. **Prioritise.** Order the action list in this sequence:
   1. Compliance and safety risk: G99 out of order, overdue DNO notification, MCS.
   2. Customer-facing delay: handover, stuck installs.
   3. Money at risk (largest £ first).
   4. Data tidy-ups.

5. **Write the report.** Create `output/<date>/exceptions_report.md` by following `templates/report_template.md`:
   - summary counts by check group and severity, with the trend from the run log
   - the top actions
   - one table row per exception (all of them)
   - root-cause groups, each with **one upstream fix** that would stop that cause recurring
   - the "Needs human review" section

6. **Draft chase emails.** For each supplier or team that has something to chase, write one file in `output/<date>/draft_emails/` named `to_<owner>.md` (e.g. `to_kestrel_scaffolding.md`, `to_installer_team_b.md`, `to_office_compliance.md`), following `templates/chase_email_template.md`.
   - Every draft starts with `STATUS: DRAFT - NOT SENT - needs approval`.
   - Quote job IDs, invoice numbers and the two values that disagree.
   - Do not chase anything still under human review. List it in the draft as "on hold pending review" instead.
   - Keep the tone polite and factual, in plain UK English. Use no customer personal data; customer refs only.

7. **Finish.** Reply with a short summary: totals, new vs carried over, top three actions, the file paths, and a reminder that nothing has been sent.

## Unattended (scheduled) runs

The scheduled runner (`scripts/run_daily.ps1`) runs step 1 itself, then starts you headless (`claude -p`) with **no shell access**: you can only read files and write inside `output/`. When the prompt says the checks have already run:

- Skip step 1. Confirm that `output/<date>/exceptions.json` exists and its `as_of` equals that date. If it doesn't, stop and say so. Never guess the results.
- Ignore any `RUN_FAILED.md` or `INPUT_ERROR.md` from earlier attempts. The runner manages those files.
- Do steps 2 to 7 without asking questions. If something needs a decision, put it under "Needs human review" and carry on. The human reads the report and approves drafts later.
