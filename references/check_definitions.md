# Check definitions

What each check does (deterministic, in `scripts/run_checks.py`) and the usual causes and owners (guidance for
Claude's judgement). Thresholds come from `config/rules.yaml`. Every number there is a placeholder for the business
to confirm. Items marked CHECK must be checked against current ENA (G98/G99) and MCS guidance.

## A. Flow

| Check | Rule | Usual cause | Usual owner |
|---|---|---|---|
| A1 Stuck in stage | Job is waiting for its next stage longer than that stage's `max_days`, counted from the date of its current stage. Applies up to commissioning (paperwork after commissioning is C1). | Scheduling (install backlog, scaffold clash); Office (DNO application not submitted); External (DNO slow to approve) | Office / Ops scheduler; DNO delays: Office chases the DNO |
| A2 Missing stage date | Job's current stage implies a stage was reached but its date is blank. | Data entry | Office |
| A3 Dates out of order | A later stage is dated before an earlier one (see `date_order`). Installed before DNO approval on a G99 job is the serious one: a possible connection without approval. | Either a data-entry error or a real process breach, so always check | Office first, then Ops manager if real |

## B. Mismatch (tracker vs installation record)

| Check | Rule | Usual cause | Usual owner |
|---|---|---|---|
| B1 Panel count | Counts differ. | Design change on site not fed back; installer job sheet error | Installer team + Design |
| B2/B3/B4 Model | Panel / inverter / battery model differs. Flagged *Needs human review*: could be an approved substitution. A larger inverter on a G98 job may also change the DNO route. | Stock substitution not recorded; tracker not updated | Design / Office |
| B5 kWp | Tracker kWp ≠ installed panels × watts (only checked when count and model agree). | Data entry (typo) | Office |
| B6 Dates | Install or commissioning date differs between the two systems. | Job sheet filled in late or from memory | Installer team |
| B7 No record | Tracker says installed but no installation record exists. | Job sheet not submitted | Installer team |

## C. Compliance

| Check | Rule | Usual cause | Usual owner |
|---|---|---|---|
| C1 Overdue after commissioning | G98/G99 notification, MCS certificate or handover pack not recorded within `max_days` of commissioning. CHECK the timings against current ENA/MCS guidance. | Missing paperwork (admin backlog, waiting on installer test results) | Office (compliance admin) |
| C2 Complete but documents missing | Job marked `complete` but the documents index lacks a document required for its job type. | Job closed too early; document not filed | Office |

## D. Supplier invoices

| Check | Rule | Usual cause | Usual owner |
|---|---|---|---|
| D1 Price above agreed | Unit price exceeds the price list by more than `price_over_list_pct`. | Supplier billing at the new list price, not the agreed price; or our price list is out of date | Supplier (Office/purchasing to query) |
| D2 Duplicate line | Same supplier, job, item, quantity and price billed again. Second occurrence flagged. | Supplier re-issued an invoice | Supplier |
| D3 Unknown job | Invoice references a job ID not in the tracker. Always *Needs human review*. | Supplier typo, cancelled job, or job missing from tracker | Office to confirm before paying |
| D4 Invoiced > installed | Panels, inverters or batteries invoiced exceed what the installer recorded fitting (duplicates excluded). | Over-delivery, returns not credited, or job sheet wrong | Supplier or Installer team |
| D5 Not on price list | Item has no agreed price. *Needs human review*. | New product / substitution | Office (purchasing) |

## X. Data quality (input validation)

Before any check runs, every input file is validated.

| Problem | What happens |
|---|---|
| Missing file, missing column, empty tracker, broken `rules.yaml` | **Run stops** (exit code 2) and writes `INPUT_ERROR.md`. The run log is **not** updated, so a broken export can never look like a clean day. |
| X1 Bad or duplicate source record: invalid date, a word where a number belongs, unknown job type/route/stage, negative quantity, duplicate job ID / install record / price-list item | Reported as an X1 exception with file, line and value. Always *Needs human review*. That record is **quarantined**: other checks skip it, so it can't raise knock-on false alarms (e.g. "invoice for unknown job"). |

## Root-cause groups and typical upstream fixes

| Cause | Typical upstream fix |
|---|---|
| Data entry | Make the field mandatory or validated in the tracker (e.g. kWp calculated from panels × watts, not typed) |
| Supplier | Send the agreed price list with each PO and reject invoices that don't match it; one invoice per delivery |
| Scheduling | Weekly look-ahead of jobs near their stage limit; book scaffold only when an install date is confirmed |
| Missing paperwork | Automatic task to submit G98/G99, MCS and handover on the commissioning date, with a due date |
| Installer job sheets | Job sheet completed on a phone at commissioning, before the team leaves site |
| External (DNO) | Track DNO reference and chase at a set interval; escalate at the limit |
