# 2-minute demo script

**Set up before the call.** Open the slide deck. Double-click `Open dashboard.cmd`, so the dashboard is open in a
browser tab. Open Task Scheduler at **Solar Job Exceptions**. Have `output/test_results.md` open in a tab. You don't
need to type anything into Claude.

---

### 0:00–0:20 · The problem (slide 1–2)
> "I ran delivery for 100-plus solar and battery jobs. The data lived in five places: the job tracker, the installers'
> job sheets, supplier invoices, the price list and the compliance folder. They drift apart, and the problems you find
> late are the expensive ones: a missed MCS certificate, a G99 job connected before DNO approval, a scaffold hire
> paid twice. So I built this to check them against each other every morning."

### 0:20–0:35 · The split (slide 3)
> "There are two layers. Python does every comparison and every pound, so the same data always gives the same answer.
> Claude does the judgement: likely cause, owner, priority and the wording of the chase emails. All the thresholds are
> in one file the business owns."

### 0:35–1:20 · What the ops manager sees (dashboard)
Switch to the dashboard.
> "This is what the office sees at 8 o'clock. Nobody talks to Claude. It ran at half six on its own."

- **Green banner and numbers:** "23 open, 8 high, £3,900 at risk, 4 for a human to decide."
- **Trend chart:** "Every run is logged, so you can see whether we're getting on top of it."
- **Report tab, Top actions:** "First is a G99 job that shows installed before DNO approval. It could be a typo or a
  real breach, so it goes to a human."
- **Root causes:** "Every pricing problem comes from one supplier, and the two 'complete' jobs with missing paperwork
  mean the status is being set too early. For each cause it suggests one upstream fix."
- **Draft emails tab:** "It drafts the chase. Draft, not sent. I check it, copy it, send it."

### 1:20–1:45 · Where the human stays in the loop, and what happens when things break
> "It never sends, never edits the source data and never marks anything resolved. A problem only closes when the data
> is fixed and the next run stops finding it. If an export is broken, the run stops and says why, rather than
> pretending it was a clean day. If the laptop's asleep or the connection drops, it retries and the banner turns red."

Optionally switch to Task Scheduler: "Here's the real job: *Last Run Result* 0x0."

### 1:45–2:00 · How I know it works, and why it transfers
Show `test_results.md`.
> "The sample data has 22 problems planted on purpose, plus near misses that must not be flagged. It catches all 22
> with zero false alarms. And swap jobs for orders, job sheets for the WMS and the price list for a carrier rate card:
> it's the same exceptions loop for e-commerce fulfilment."

---

**If asked "why not let Claude do the checks too?"**
> "Because arithmetic should be repeatable and testable. I use Claude where judgement adds value, not where a
> `>` sign will do."

More questions and answers are in `PRESENTING.md`.
