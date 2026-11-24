# Presenting this project

How to run it, where to look, and how to show it in an interview, all **without typing anything into Claude**.

## Who sees what

Claude is the engine, not the interface. In real use nobody chats with it.

| Person | What they use | What they never see |
|---|---|---|
| Office / ops manager (the "customer") | **The dashboard** (`output/dashboard.html`): the morning's status, priorities, every exception, draft emails ready to copy | Claude, Python, the terminal |
| Whoever owns the process (you) | The dashboard, plus `config/rules.yaml` for thresholds and the logs if a run fails | Nothing hidden |
| Claude | Runs headless inside the 06:30 scheduled job, with permission to read, run the checker and write to `output/` only | Email, the source data, the rules |

This is the usual pattern for AI-powered operations tools. The model does its work in the background, and people see
a report, a queue or a set of drafts to approve.

## Running it without Claude

| Way | How | When to use it |
|---|---|---|
| **Automatic** | The scheduled task runs at 06:30 every day (see README, "Scheduling it daily") | Normal use |
| **One click** | Double-click **`Run check now.cmd`** in the project folder. It takes about 3 minutes and then opens the dashboard | To refresh it on demand |
| **Task Scheduler** | Start menu, then *Task Scheduler*, then *Task Scheduler Library*, then **Solar Job Exceptions**, then **Run** | To show the real scheduled job in action |
| **Just look** | Double-click **`Open dashboard.cmd`** | To show this morning's results without running anything |

## Where to look

| What | Where | Opens with |
|---|---|---|
| Everything in one place | `output/dashboard.html` | Any browser. It works offline and needs no login |
| Claude's report | `output/YYYY-MM-DD/exceptions_report.md` (also the dashboard's *Report* tab) | Browser tab, VS Code or GitHub |
| Draft emails (never sent) | `output/YYYY-MM-DD/draft_emails/` (also the *Draft emails* tab, with a *Copy text* button) | Same |
| Facts only, no Claude | `output/YYYY-MM-DD/checks_summary.md`, `exceptions.json` | Same |
| Trend over time | `output/run_log.csv` (also the chart and the *Run history* tab) | Excel |
| What happened during the run | `output/logs/YYYY-MM-DD.log`: each step and attempt, with times | Notepad, or the *Logs* tab |
| Did the scheduled task run? | Task Scheduler, **Solar Job Exceptions**: *Last Run Result* `0x0` means success, and the *History* tab lists past runs | Task Scheduler |
| A failed day | `output/YYYY-MM-DD/RUN_FAILED.md` or `INPUT_ERROR.md`, also shown as a red or amber banner on the dashboard | Same |
| Proof it's correct | `output/test_results.md`. Re-run with `python scripts/test_against_answer_key.py` and `python scripts/test_bad_input.py` | Same |

## The interview: what to have ready

| Material | Needs your laptop? | Use it for |
|---|---|---|
| **GitHub repo link** | No | Send it beforehand. They can browse the README, code, a real report and the run history whenever they like |
| **Interactive walkthrough page** (claude.ai link) | No | The best single link: workflow diagram, real report, drafts, error handling, test results |
| **Slide deck** (PDF/PPTX) | No | The first 60 seconds: problem, approach, results. Works on their screen in person |
| **Live dashboard** | Yes | The "it's real" moment on a video call |
| **Recorded video** (optional) | Only to record it | Backup if anything fails on the day |

### Video interview (screen share), about 2 minutes

1. **Slides, 30 s:** the problem, and the split between Python and Claude.
2. **Dashboard, 60 s:** double-click `Open dashboard.cmd`. Show the green banner, the numbers, the trend, then *Report*,
   then *Draft emails* ("not sent"), then one *Needs human review* item.
3. **Proof, 20 s:** Task Scheduler showing the 06:30 task, *Last Run Result* `0x0`, and `test_results.md` showing
   22 of 22 caught.
4. **Close, 10 s:** the e-commerce mapping slide.

Don't start a fresh run live, because it takes about 3 minutes. Show this morning's run. If they ask to see it run,
double-click `Run check now.cmd` at the start and come back to it at the end.

### In person, without your laptop

Open the **walkthrough page link** or the **GitHub repo** on their screen. Neither needs a login. The slide deck as a
PDF covers the rest. **Don't log into your own accounts on their computer.**

## The day before: checklist

- [ ] `claude auth status` shows `"loggedIn": true`. A sign-in can expire, and the scheduled run then fails at 06:30.
- [ ] This morning's run is green on the dashboard. If not, double-click `Run check now.cmd`.
- [ ] `python scripts/test_against_answer_key.py` and `python scripts/test_bad_input.py` both say PASS.
- [ ] Windows notifications are off (Focus) and other windows are closed.
- [ ] The links are in your notes: repo, walkthrough page, deck.

## Recording the backup video (optional)

- **Windows:** use Snipping Tool's **Record** button (`Win + Shift + R`), or Clipchamp to add your voice afterwards.
- **Script:** follow `DEMO.md`. Keep it under 2½ minutes.
- **Hosting:** upload it as an unlisted YouTube video or a Loom link, and put the link in the repo README.

## Likely questions

| Question | Short answer |
|---|---|
| Why not let Claude do the checks? | Arithmetic must be repeatable and testable. The same data always gives the same answer, and that's what the 22/22 test proves. Claude is used where judgement adds value. |
| What if Claude gets a root cause wrong? | It's a suggestion with the evidence next to it. A person reviews it before anything is sent, and the facts never depend on Claude. |
| What stops it emailing a supplier by mistake? | It has no permission to. In the scheduled run, anything outside reading, running the checker and writing to `output/` is refused automatically. |
| What if the export is broken? | Missing file or column: the run stops, says why, and the day isn't logged as clean. Bad rows: reported and quarantined, so they cause no false alarms. |
| What if the laptop is asleep or offline? | It wakes at 06:30, keeps itself awake, waits for the network, and stops and retries a stuck attempt. If every attempt fails, the dashboard says so in red. The cloud version runs with the PC off. |
| How would this scale? | Point `--data` at nightly exports from the job system, CRM and accounts, or run it as a scheduled cloud agent. The thresholds stay in one file the business owns. |
| What's next? | Read the exports straight from the systems' APIs. Track how long each exception stays open. A weekly summary of which upstream fixes reduced exceptions. |
