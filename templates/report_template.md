# Daily exceptions report: {{DD Mon YYYY}}

**Status:** {{TOTAL}} open exceptions ({{NEW}} new, {{CARRIED}} carried over, {{CLOSED}} closed since {{PREVIOUS DATE}}).
{{HIGH}} high severity, {{OVERDUE}} past their response target, {{DECISIONS}} need a decision.
{{£ AT RISK}} at risk on supplier invoices ({{%}} of {{£ CHECKED}} checked).

{{ONE OR TWO SENTENCES: the single most important thing today and the main pattern behind the numbers.}}

## 1. Decisions needed today

| Ref | Job | Question to answer | Why it matters | Decided by |
|---|---|---|---|---|
| {{#}} | {{SJ-xxxx}} | {{The single question}} | {{Consequence of getting it wrong}} | {{Role}} |

## 2. Priority actions

| Priority | Job | Action | Owner | Due |
|---|---|---|---|---|
| 1 | {{SJ-xxxx}} | {{Verb + reference + amount}} | {{Owner}} | {{DD Mon}} |

(Top eight by priority. Every action is in the register in section 5.)

## 3. Position

| Check group | High | Medium | Low | Total | Change vs last run |
|---|---|---|---|---|---|
| A Flow | | | | | |
| B Tracker vs install | | | | | |
| C Compliance | | | | | |
| D Supplier invoices | | | | | |
| X Data quality | | | | | |
| **Total** | | | | | |

Trend (last five runs, open exceptions): {{e.g. 22 → 23}}. Ageing: {{n}} open 0–1 days, {{n}} 2–7 days, {{n}} over 7 days.

## 4. Root causes and upstream fixes

Largest cause first.

### {{Cause}}: {{N}} exceptions, {{£ if any}} ({{job IDs}})
- **Pattern:** {{What links them, from the data only}}
- **Upstream fix:** {{One process or system change}}

## 5. Exception register

| Ref | Job | Issue | Evidence | Sev. | Cause | Owner | Next action | Due |
|---|---|---|---|---|---|---|---|---|
| {{priority}} | {{SJ-xxxx}} | {{Check: what is wrong}} | {{expected / found}} | {{H/M/L}} | {{Cause}} | {{Owner}} | {{Action}} | {{DD Mon (overdue)}} |

## 6. Draft communications (not sent)

| File | To | Covers | Held pending decision |
|---|---|---|---|
| `draft_emails/to_....md` | {{Recipient}} | {{Job IDs}} | {{Job IDs or "None"}} |

---
*Facts from `run_checks.py`; classification and wording by the review step and validated against the facts.
Thresholds are business settings in `config/rules.yaml`; regulatory timings to be checked against current ENA/MCS
guidance. Nothing has been sent or changed.*
