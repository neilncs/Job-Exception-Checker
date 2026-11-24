# Two-minute demo

**Before the call:** open the slide deck; double-click `Open dashboard.cmd`; open Task Scheduler at
*Solar Job Exceptions*; have `output/test_results.md` in a tab. Nothing is typed into Claude during the demo.

---

### 0:00–0:20 · The problem (slide 2)
> "As Business Manager at a solar installer I ran delivery for over a hundred domestic and small commercial jobs.
> The information sat in five places: the job tracker, the installers' job sheets, supplier invoices, the price list
> and the compliance folder. They drift apart, and the expensive problems are the ones found late: a G99 job energised
> before DNO approval, a missed MCS certificate, scaffold hire paid twice."

### 0:20–0:35 · The approach (slides 3 and 4)
> "This runs at half six every morning. Python establishes the facts: 17 checks, every date and every pound, so the
> same data always gives the same answer. Claude adds the judgement: root cause, owner, priority and the chase emails.
> Its output is validated by code, and it has no permission to send anything or change any data."

### 0:35–1:25 · What the office sees at eight (dashboard)
- **Banner and headline:** "Report ready, classification validated. 23 open, 8 high severity, £3,890 at risk, which
  is 2.7% of invoice value checked."
- **Today's priorities:** "Decisions first. This G99 job shows installed before DNO approval. That's either a typo or
  a breach, so a person checks the approval letter. Then actions in priority order, each with an owner and a due date."
- **Root causes:** "Ranked by size. Missing paperwork and one supplier account for most of it, and each cause has one
  upstream fix, so the same exceptions stop coming back."
- **Draft emails tab:** "Drafted, not sent. I check it, copy it, send it."

### 1:25–1:45 · Controls and reliability
> "Nothing is sent, changed or marked resolved by the system. An exception closes when the data is fixed and the next
> run stops finding it. If an export is broken the run stops and says why; if the review fails, the page turns amber
> rather than showing yesterday's green."

Optionally show Task Scheduler: *Last Run Result 0x0*.

### 1:45–2:00 · Evidence and transfer
Show `test_results.md`.
> "I tested it against synthetic data with 22 planted problems and some near misses: all 22 caught, no false alarms.
> And it transfers directly: orders instead of jobs, the WMS instead of job sheets, a carrier rate card instead of the
> price list, SLAs instead of stage limits."

---

**If asked why Claude doesn't do the checks:** "Arithmetic has to be repeatable and testable. I use the model where
judgement adds value, and I validate what it produces."

More questions and answers are in `PRESENTING.md`.
