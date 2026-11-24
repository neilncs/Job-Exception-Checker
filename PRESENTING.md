# Running and presenting

How to run the checker, where everything is, and how to present it. None of it involves typing into Claude.

## Who uses what

| Person | Uses | Never needs |
|---|---|---|
| Office or operations manager | The dashboard (`output/dashboard.html`): status, decisions, priority actions, analytics, drafts to copy | Claude, Python, a terminal |
| Process owner | The dashboard, `config/rules.yaml` for thresholds, the logs if a run fails | Anything hidden |
| Claude | Runs headless inside the 06:30 job; reads files and writes to `output/` only, with no shell access | Email, source data, rules |

This is the usual shape of an AI-assisted operations tool: the model works in the background, and people see a
queue of decisions and drafts to approve.

## Running it

| To | Do |
|---|---|
| See this morning's results | Double-click **`Open dashboard.cmd`** |
| Refresh now (about 2 minutes) | Double-click **`Run check now.cmd`** |
| Show the scheduled job | Task Scheduler › Task Scheduler Library › **Solar Job Exceptions** (*Last Run Result* `0x0` = success; *History* tab for past runs) |
| Register or remove the schedule | `scripts\register_task.ps1 -RunNow` / `-Remove` |

## Where everything is

| What | Where |
|---|---|
| Everything in one place | `output/dashboard.html` (any browser, works offline) |
| The day's report | `output/YYYY-MM-DD/exceptions_report.md` (dashboard: *Full report*) |
| Classification (cause, owner, priority) | `output/YYYY-MM-DD/actions.json`, validated by `scripts/validate_actions.py` |
| Draft emails, never sent | `output/YYYY-MM-DD/draft_emails/` (dashboard: *Draft emails*, with *Copy text*) |
| Facts only | `output/YYYY-MM-DD/exceptions.json`, `checks_summary.md` |
| Trend | `output/run_log.csv` (dashboard: chart and *Run history*) |
| What happened during a run | `output/logs/YYYY-MM-DD.log` (dashboard: *Logs*) |
| A failed day | `RUN_FAILED.md` or `INPUT_ERROR.md` in that day's folder; amber or red banner |
| Test evidence | `output/test_results.md`; rerun the three `scripts/test_*.py` scripts |

## Presenting

| Material | Needs your laptop? | Use |
|---|---|---|
| GitHub repository | No | Send beforehand; the README is the full write-up |
| Interactive walkthrough page | No | One link covering workflow, controls, evidence and real output |
| Slide deck (PDF or PPTX) | No | Frame the first minute; leave behind afterwards |
| Live dashboard | Yes | The proof that it runs |
| Recorded video (optional) | Only to record | Backup if anything fails on the day |

**Video interview:** slides 2 to 4 (30 s), dashboard (60 s), Task Scheduler and test results (20 s), the
e-commerce slide (10 s). The script is in `DEMO.md`. Show this morning's run rather than starting one live.

**In person without your laptop:** open the walkthrough page or the repository on their screen. Neither needs a
login. Don't sign into your own accounts on someone else's computer.

## The day before

- [ ] `claude auth status` shows `"loggedIn": true` (an expired sign-in stops the 06:30 run)
- [ ] This morning's run is green; if not, double-click `Run check now.cmd`
- [ ] The three test scripts pass
- [ ] Repository public, deck and walkthrough shared
- [ ] Notifications off; other windows closed

## Likely questions

| Question | Answer |
|---|---|
| Why not let Claude do the checks? | Arithmetic has to be repeatable and testable. The same data always gives the same exceptions, which is what the 22-of-22 test proves. The model is used for judgement, and its output is validated. |
| How do you know Claude's classification is complete? | It writes structured JSON that code checks: every exception exactly once, causes and owners from fixed lists, every flagged item marked as a decision. If it fails, the run retries and then shows amber. |
| What stops it emailing a supplier? | It has no permission to. In the scheduled run it can read files and write to the output folder, nothing else. It doesn't even have a shell. |
| What if an export is broken? | Missing file or column: the run stops, says which, and the day isn't logged. Bad rows: reported and quarantined so they cause no false alarms. |
| What if the PC is asleep or offline? | It wakes at 06:30 on mains power, stays awake, waits for the network and retries a stalled step. Anything that fails shows amber or red. A cloud-scheduled version would remove the PC dependency. |
| What difference would it make? | On a 40-job operation, roughly 80% less time spent reconciling, every invoice line checked instead of a sample, and missed deadlines found the next day instead of at month end. The assumptions are in the README. |
| What would you do next? | Read directly from the systems' APIs; report time-to-close by owner; track which upstream fixes actually reduced exceptions. |
