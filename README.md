# Solar Job Exceptions Checker

A Claude Skill that checks a UK solar PV and battery installer's records every morning. It lists the jobs that are
stuck, don't match, are missing compliance paperwork or have been overcharged, before a customer, the DNO or an MCS
auditor notices.

Each exception comes with the evidence, a likely root cause, an owner and a next action. The skill also drafts the
chase emails. **It never sends anything, never edits the source data and never marks anything as resolved.** A
person reviews the report and approves the drafts.

All data here is synthetic: fictional jobs, suppliers and product codes, with no real customers or addresses.

**What people actually see** is a dashboard (`output/dashboard.html`). It opens in any browser, works offline and needs
no login, and it's rebuilt after every run: status, trend, Claude's report, every exception with filters, and draft
emails ready to copy. Nobody types into Claude; it runs in the background at 06:30. See
[PRESENTING.md](PRESENTING.md) for how to run, view and demo it.

---

## The problem

On a domestic or small commercial solar job, the delivery information lives in several places that drift apart:

- the **job tracker** (stages and dates)
- the **installers' job sheets** (what was actually fitted)
- **supplier invoices**, and the **agreed price list** they should match
- the **compliance document folder**: MCS certificate, electrical installation certificate, G98/G99 notification,
  warranty registrations, handover pack

Nobody has time to cross-check all of them every day. So problems surface late: a G99 job connected before DNO
approval, an MCS certificate missed, a scaffold hire paid twice, a tracker that says 12 panels when 10 were fitted.
This skill does that cross-check daily and gives the office a short, prioritised list to work through.

## What it checks

| Group | Checks |
|---|---|
| **A. Flow** | A1 job stuck in a stage beyond its allowance · A2 stage reached but date missing · A3 dates out of order (e.g. G99 installed before DNO approval) |
| **B. Mismatch** (tracker vs installation record) | B1 panel count · B2 panel model · B3 inverter · B4 battery · B5 kWp (panels × watts) · B6 install/commissioning date · B7 no installation record |
| **C. Compliance** | C1 G98/G99 notification, MCS certificate or handover pack overdue after commissioning · C2 job marked complete with documents missing for its job type |
| **D. Supplier invoices** | D1 unit price above agreed price beyond tolerance · D2 duplicate invoice line · D3 invoice for a job not in the tracker · D4 more invoiced than installed · D5 item not on the price list |
| **X. Data quality** | Every input is validated first. A missing file or column, or a broken rules file, **stops the run with a clear message** and is never logged as a clean day. Bad rows (invalid date, word in a number field, duplicate ID) become X1 exceptions and are **quarantined**, so they can't cause knock-on false alarms |
| **E. Root cause and action** | Claude groups exceptions by likely cause (data entry, supplier, scheduling, missing paperwork, DNO), names an owner, sets priorities and suggests **one upstream fix per cause** |

Full definitions are in [references/check_definitions.md](references/check_definitions.md). Every threshold is in
**one editable file**, [config/rules.yaml](config/rules.yaml). Each value is marked PLACEHOLDER, and anything with a
regulatory basis is marked "CHECK against current ENA/MCS guidance" rather than stated as fact.

## How the work is split: Python for facts, Claude for judgement

| Deterministic Python (`scripts/run_checks.py`) | Claude (following `SKILL.md`) |
|---|---|
| Reads the five CSVs and the rules | Reads the exceptions and evidence |
| Every comparison, date difference and £ sum | Likely root cause, spotting patterns across jobs (same supplier, same installer team) |
| Assigns severity from `rules.yaml` | Owner and one concrete next action |
| Flags known ambiguities as *Needs human review* | Priority order (compliance, then customer delay, then money, then tidy-up) |
| Tracks new / carried-over / closed exceptions across runs | Plain-English report and chase-email wording |
| Writes `exceptions.json`, `checks_summary.md`, `run_log.csv` | Writes `exceptions_report.md` and `draft_emails/` |

The idea is that **arithmetic shouldn't depend on a language model**. The same data always produces the same
exceptions, and that is what the test checks. Claude adds the part a good operations manager would add: why it
happened, who should fix it, and what to change so it doesn't happen again. If the Claude step ever fails, the
factual `checks_summary.md` is still written.

## What runs on its own, and where I step in

| Runs unattended (daily, 06:30) | Human in the loop |
|---|---|
| Run all checks and update the run log | Read the report, starting with *Top actions* |
| Group causes, assign owners, prioritise | Decide every *Needs human review* item (e.g. was that inverter swap approved?) |
| Draft one chase email per supplier or team | Check, edit and **send** each draft myself |
| Track whether the open count is falling | Fix the source data. An exception only closes when the next run stops finding it |
| | Own the thresholds in `rules.yaml` |

The guardrails are enforced, not just requested. The scheduled run starts Claude Code with
`--permission-mode dontAsk` and an allow-list of: read files, run `run_checks.py`, and edit files under `output/`.
Every other tool call is refused automatically. That includes sending email, editing `data/` or `config/`, and running
any other command.

## Folder structure

```
solar-job-exceptions/
  Run check now.cmd                one-click run (same as the scheduled job), then opens the dashboard
  Open dashboard.cmd               opens the latest results without running anything
  SKILL.md                         skill definition: when to trigger + the procedure Claude follows
  PRESENTING.md                    how to run, where to look, how to demo it
  config/rules.yaml                every threshold, in one place (placeholders)
  scripts/generate_sample_data.py  builds 40 synthetic jobs with planted problems + answer key
  scripts/run_checks.py            input validation + the deterministic checks
  scripts/build_dashboard.py       builds output/dashboard.html from every run
  scripts/test_against_answer_key.py   must catch 22/22 planted problems, 0 false alarms
  scripts/test_bad_input.py        broken files and rows are caught, not crashed on
  scripts/run_daily.ps1 / .sh      unattended runner (Task Scheduler / cron)
  references/check_definitions.md  what each check means, usual causes and owners
  templates/                       report and chase-email templates
  data/sample/                     the synthetic CSVs + answer_key.csv
  output/YYYY-MM-DD/               exceptions.json, checks_summary.md, exceptions_report.md, draft_emails/
  output/run_log.csv               one row per day, so the open count can be tracked over time
  output/dashboard.html            the page people look at
  output/logs/                     what happened in each run, attempt by attempt
```

## How to run it

**Set up (once).** You need Python 3.10+ and [Claude Code](https://claude.com/claude-code).

```powershell
python -m pip install -r requirements.txt
```

```powershell
python scripts/generate_sample_data.py
```

**Day to day, without Claude:** double-click **`Run check now.cmd`**, or let the 06:30 schedule run it. Then open the
dashboard with **`Open dashboard.cmd`**.

**1. On demand, by asking Claude** (for developers). Open Claude Code in this folder, or in a project where the skill is installed
under `.claude/skills/solar-job-exceptions`, and say:

> run the solar job exceptions check

Claude runs the checks, then writes the report and the drafts. To install it for every project, copy this folder to
`%USERPROFILE%\.claude\skills\solar-job-exceptions` (or `~/.claude/skills/` on macOS/Linux).

**2. One-off headless run** (the same thing the schedule does):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_daily.ps1
```

**Just the deterministic checks**, without Claude:

```powershell
python scripts/run_checks.py --as-of 2026-11-23
```

**Tests:**

```powershell
python scripts/test_against_answer_key.py
```

```powershell
python scripts/test_bad_input.py
```

## Scheduling it daily

The goal is a finished report waiting at the start of the working day. The task starts at **06:30**. A normal run
takes about 3 minutes, and the worst case with all three retries is about an hour, so the report is ready well before
08:00.

**Windows Task Scheduler.** Run this once in PowerShell, changing the path to where the folder lives:

```powershell
$action   = New-ScheduledTaskAction -Execute "powershell.exe" -Argument '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\Dev\Skills\Exception checker\Job Exception Checker\scripts\run_daily.ps1"'
$trigger  = New-ScheduledTaskTrigger -Daily -At 6:30am
$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 90)
Register-ScheduledTask -TaskName "Solar Job Exceptions" -Action $action -Trigger $trigger -Settings $settings -Description "Daily solar job exceptions check (Claude Code headless)"
```

What each setting is for:

- **`-WakeToRun`** wakes the PC from sleep at 06:30. Windows only allows this when wake timers are enabled. On this
  laptop they are enabled on mains power and disabled on battery, so **leave it plugged in overnight**.
- **`-StartWhenAvailable`** is the fallback. If the PC was off or couldn't wake, the run starts as soon as you switch
  it on, and the report is ready about 3 minutes later.
- **`-ExecutionTimeLimit 90 min`** is a last-resort stop. The runner already limits each attempt itself.

What the runner does to make an unattended run reliable:

- **Keeps the PC awake while it runs.** In one test the laptop went into Modern Standby a minute in. The Wi-Fi
  dropped and the run froze for 96 minutes until the laptop woke.
- **Waits up to 10 minutes for the network** after waking.
- **Stops any attempt after 15 minutes** and tries again, up to 3 attempts.
- **If every attempt fails,** the deterministic checks still run, and `RUN_FAILED.md` in that day's folder says what
  is missing and how to finish it. You find out at 08:00 rather than discovering a half-finished folder.

Every attempt is timed in `output/logs/YYYY-MM-DD.log`.

Test it straight away, and remove it when you're finished:

```powershell
Start-ScheduledTask -TaskName "Solar Job Exceptions"
```

```powershell
Unregister-ScheduledTask -TaskName "Solar Job Exceptions" -Confirm:$false
```

The task runs while you are logged in (a locked screen is fine), using your Claude Code CLI sign-in. That sign-in is
separate from the desktop app's: check it with `claude auth status`. Remember a sign-in can expire, and the run then
fails with a 401 in the log.

**cron (macOS/Linux):**

```
0 7 * * * /path/to/solar-job-exceptions/scripts/run_daily.sh
```

What the runner executes:

```
claude -p "Run the solar job exceptions check. Follow SKILL.md in this folder exactly. This is an unattended scheduled run: do not ask questions; put anything uncertain under Needs human review." --permission-mode dontAsk --allowedTools "Read" "Glob" "Grep" "Bash(python scripts/run_checks.py:*)" "PowerShell(python scripts/run_checks.py:*)" "Edit(./output/**)"
```

## Test result

The sample data has **22 planted problems** across all four check groups. It also has near misses that must *not*
be flagged: an invoice 1.5% over list when the tolerance is 2%, and an MCS certificate outstanding at exactly 10 days
when the limit is 10.

| | Result |
|---|---|
| Planted problems caught | **22 / 22 (100%)** |
| False alarms | **0** |
| Clean jobs flagged | **0 of 19** |
| Re-generated with three other random seeds | 22 / 22, 0 false alarms each time |
| Tolerance tightened to 1% / MCS limit to 9 days | The two near-miss jobs flagged, as they should be |
| Bad input (`test_bad_input.py`): invalid date, non-number, duplicate IDs, negative quantity, missing column, missing file, broken rules | **11 / 11**. Bad rows reported and quarantined with no knock-on false alarms; broken files stop the run cleanly without touching the run log |
| Forced stall (attempt limited to 1 minute) | Attempt stopped, no stray processes, `RUN_FAILED.md` written, facts still available |
| Unattended run via `run_daily.ps1` (headless, locked-down permissions) | Report covering all 22 exceptions plus 7 drafts, all marked not sent. The 5 data files, the answer key and `rules.yaml` were byte-for-byte unchanged |

The full table is in `output/test_results.md`. Re-run it any time with
`python scripts/test_against_answer_key.py`.

## How this maps to e-commerce fulfilment

The same pattern (reconcile several systems, find exceptions against agreed limits, and route each one to an owner
with a drafted chase) carries straight across:

| Solar installer | E-commerce fulfilment |
|---|---|
| Job | Order |
| Job tracker stages (survey, install, commission, handover) | Order status (paid, picked, packed, shipped, delivered) |
| Installation record (what was actually fitted) | WMS / 3PL record (what was actually picked and shipped) |
| Supplier invoices | Carrier and 3PL invoices |
| Agreed price list | Carrier rate card |
| Stage thresholds (days allowed per stage) | SLAs (dispatch within 24 h, deliver within 3 days) |
| Compliance documents (MCS, G98/G99, handover pack) | Proof of delivery, customs paperwork, returns labels |
| Panel count mismatch | Short shipment / wrong SKU |
| Duplicate scaffold invoice | Carrier double-billing a parcel |
| Invoice for a job not in the tracker | Carrier charge for an order that doesn't exist |

## Limitations

- CSV in, Markdown out, to keep the demo small. In real use the inputs would be exports from the CRM, job management
  and accounting systems, pointed to with `--data`.
- Thresholds are placeholders until confirmed. Regulatory timings must be checked against current ENA and MCS
  guidance.
- Claude's root-cause calls are suggestions with evidence, not conclusions. That's why a human reviews them.
