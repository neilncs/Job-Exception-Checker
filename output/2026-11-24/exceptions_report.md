# Daily exceptions report: 24 Nov 2026

**Status:** 23 open exceptions (1 new, 22 carried over, 0 closed since 23 Nov 2026).
8 high severity, 0 past their response target, 7 need a decision.
£3,889.80 at risk on supplier invoices (2.7% of £143,180.60 checked).

Today, establish whether SJ-1027 was connected before its G99 approval on 19 Nov 2026, and submit the G98 notification for SJ-1002, now 61 days after commissioning (allowed 28). Post-commissioning paperwork is the largest cause at 6 of 23, and none of yesterday's 22 exceptions has closed; 7 are due today.

## 1. Decisions needed today

| Ref | Job | Question to answer | Why it matters | Decided by |
|---|---|---|---|---|
| 1 | SJ-1027 | Was the system connected before G99 approval on 19 Nov 2026, or is the 14 Nov 2026 install date wrong? | A possible connection without DNO approval on a commercial G99 job | Operations manager |
| 3 | SJ-1014 | Was the INV-5.0S an approved substitution for the INV-3.6S, and does it keep the job within G98? | A larger inverter may need a G99 application instead of G98 (check against current ENA guidance) | Design |
| 9 | SJ-1023 | Was the BAT-5.2 an approved substitution for the BAT-10.4 in the tracker? | Fitted battery is half the tracker capacity; certificates and warranty must name the fitted model | Design |
| 10 | SJ-1009 | Was the SP-410B an approved substitution for the SP-430M in the tracker? | MCS certificate and design must match the panels fitted | Design |
| 14 | SJ-1140 | Is BFW-24257 for SJ-1040, SJ-1014, a cancelled job, or a job missing from the tracker? | £1,868.00 could be paid against the wrong job or no job | Office (accounts) |
| 17 | SJ-1031 | Were the 2 extra SP-430M over-delivered, returned without credit, or fitted and left off the job sheet? | £208.00 query goes to the wrong party if the job sheet is wrong | Office (purchasing) |
| 20 | SJ-1003 | Were 12 panels (tracker) or 10 panels (installer) fitted, and if 10, was the change approved? | System size, MCS certificate and invoicing depend on the fitted count | Design |

## 2. Priority actions

| Priority | Job | Action | Owner | Due |
|---|---|---|---|---|
| 1 | SJ-1027 | Check the DNO approval letter and commissioning record to establish whether the system was connected before G99 approval on 19 Nov 2026 | Operations manager | 24 Nov |
| 2 | SJ-1002 | Submit the G98 notification to the DNO: commissioned 24 Sep 2026, 61 days ago (allowed 28) | Office (compliance) | 24 Nov |
| 3 | SJ-1014 | Confirm whether the INV-5.0S was an approved substitution and whether the job still fits G98 | Design | 26 Nov |
| 4 | SJ-1025 | Send the signed Electrical installation certificate to Office (compliance) for filing | Installer Team C | 24 Nov |
| 5 | SJ-1011 | Send the handover pack to the customer: 31 days after commissioning (allowed 14) | Office (compliance) | 24 Nov |
| 6 | SJ-1007 | Issue the MCS certificate: 13 days after commissioning (allowed 10) | Office (compliance) | 24 Nov |
| 7 | SJ-1039 | Issue the MCS certificate: 11 days after commissioning (allowed 10) | Office (compliance) | 25 Nov |
| 8 | SJ-1036 | Register the battery warranty and file the registration | Office (compliance) | 24 Nov |

(Top eight by priority. Every action is in the register in section 5.)

## 3. Position

| Check group | High | Medium | Low | Total | Change vs last run |
|---|---|---|---|---|---|
| A Flow | 1 | 3 | 1 | 5 | 0 |
| B Tracker vs install | 0 | 6 | 1 | 7 | 0 |
| C Compliance | 6 | 0 | 0 | 6 | +1 |
| D Supplier invoices | 1 | 4 | 0 | 5 | 0 |
| X Data quality | 0 | 0 | 0 | 0 | not recorded last run |
| **Total** | **8** | **13** | **2** | **23** | **+1** |

Trend (last five runs, open exceptions): 22 → 23. Ageing: 23 open 0–1 days, 0 2–7 days, 0 over 7 days.

## 4. Root causes and upstream fixes

Largest cause first.

### Missing paperwork: 6 exceptions (SJ-1002, SJ-1025, SJ-1011, SJ-1007, SJ-1039, SJ-1036)
- **Pattern:** Six domestic jobs past commissioning with a notification, certificate, handover pack or warranty registration not done or not filed. Installer Team B's jobs hold both overdue MCS certificates (SJ-1007, SJ-1039). Installer Team C's jobs are both closed as complete with a document missing (SJ-1025, SJ-1036).
- **Upstream fix:** Create the G98/G99 notification, MCS certificate, handover pack and warranty registration tasks automatically on the commissioning date, each with a due date, and block the complete status until the document set is filed.

### Unclear: 4 exceptions, £2,076.00 (SJ-1027, SJ-1140, SJ-1031, SJ-1003)
- **Pattern:** Two explanations fit the evidence in each case: a wrong date or a real connection before G99 approval (SJ-1027), a supplier typo or a missing job (SJ-1140), and panel quantities that differ between tracker, delivery and job sheet (SJ-1031, SJ-1003).
- **Upstream fix:** Add a commissioning sign-off where Office checks the job sheet against the DNO approval letter, the design and the delivery notes before the job moves on, and reject supplier invoices that do not quote a valid job ID.

### Data entry: 4 exceptions (SJ-1016, SJ-1030, SJ-1033, SJ-1021)
- **Pattern:** A value typed wrongly or left blank: no job sheet for a job installed on 20 Nov 2026 (SJ-1016), tracker 3.40 kWp against 4.30 kWp fitted (SJ-1030), install dates a week apart between systems (SJ-1033) and a blank survey date (SJ-1021).
- **Upstream fix:** Make stage dates and the job sheet mandatory before a job can move stage, with the job sheet completed on a phone before the team leaves site and kWp calculated from panels x watts.

### Supplier: 3 exceptions, £1,813.80 (SJ-1008, SJ-1004, SJ-1019)
- **Pattern:** Three invoice lines dated Jun to Sep 2026: one Kestrel Scaffolding Ltd line billed twice (£1,450.00) and two Brightfield Wholesale Ltd lines above agreed price (£332.80 and £31.00).
- **Upstream fix:** Match every invoice line against the agreed price list and earlier invoices for the same job before approving it for payment, and send the agreed price list with each purchase order.

### Substitution: 3 exceptions (SJ-1014, SJ-1023, SJ-1009)
- **Pattern:** Three completed G98 domestic jobs where the inverter, battery or panel recorded as fitted differs from the tracker, with no approval recorded. Two are Installer Team A jobs (SJ-1009, SJ-1023), one Installer Team C (SJ-1014).
- **Upstream fix:** Require Design sign-off, recorded in the tracker with a DNO route check, before any substituted panel, inverter or battery is fitted.

### Scheduling: 2 exceptions (SJ-1005, SJ-1018)
- **Pattern:** A G99 application not submitted 21 days after design complete (SJ-1005) and an install not done 36 days after the scaffold was booked (SJ-1018).
- **Upstream fix:** Run a weekly look-ahead of jobs approaching their stage limit, and book scaffold only once an install date is confirmed.

### External (DNO): 1 exception (SJ-1012)
- **Pattern:** One commercial G99 application waiting 71 days for DNO approval (allowed 45).
- **Upstream fix:** Record the DNO reference on every application, chase at a fixed interval and escalate to the DNO when the stage limit is reached.

## 5. Exception register

| Ref | Job | Issue | Evidence | Sev. | Cause | Owner | Next action | Due |
|---|---|---|---|---|---|---|---|---|
| 1 | SJ-1027 | Dates out of order: installed before DNO approval on a G99 job | DNO approval 19 Nov 2026 / installed 14 Nov 2026 | H | Unclear | Operations manager | Check the DNO approval letter and commissioning record; decision needed | 24 Nov |
| 2 | SJ-1002 | G98 notification to DNO not done | 61 days after commissioning on 24 Sep 2026 (allowed 28) | H | Missing paperwork | Office (compliance) | Submit the G98 notification to the DNO | 24 Nov |
| 3 | SJ-1014 | Inverter model differs | tracker INV-3.6S / installer INV-5.0S | M | Substitution | Design | Confirm substitution approval and G98 route; decision needed | 26 Nov |
| 4 | SJ-1025 | Complete with document missing | Electrical installation certificate not filed | H | Missing paperwork | Installer Team C | Send the signed EIC to Office (compliance) | 24 Nov |
| 5 | SJ-1011 | Handover pack not sent to customer | 31 days after commissioning on 24 Oct 2026 (allowed 14) | H | Missing paperwork | Office (compliance) | Send the handover pack to the customer | 24 Nov |
| 6 | SJ-1007 | MCS certificate not issued | 13 days after commissioning on 11 Nov 2026 (allowed 10) | H | Missing paperwork | Office (compliance) | Issue the MCS certificate | 24 Nov |
| 7 | SJ-1039 | MCS certificate not issued (new today) | 11 days after commissioning on 13 Nov 2026 (allowed 10) | H | Missing paperwork | Office (compliance) | Issue the MCS certificate | 25 Nov |
| 8 | SJ-1036 | Complete with document missing | Battery warranty registration not filed | H | Missing paperwork | Office (compliance) | Register the battery warranty and file it | 24 Nov |
| 9 | SJ-1023 | Battery model differs | tracker BAT-10.4 / installer BAT-5.2 | M | Substitution | Design | Confirm which model is correct from the design file and order; decision needed | 26 Nov |
| 10 | SJ-1009 | Panel model differs | tracker SP-430M / installer SP-410B | M | Substitution | Design | Confirm which model is correct from the design file; decision needed | 26 Nov |
| 11 | SJ-1012 | Waiting for DNO approval | submitted 14 Sep 2026, 71 days (allowed 45) | M | External (DNO) | Office (operations) | Chase the DNO for a G99 decision | 26 Nov |
| 12 | SJ-1005 | Waiting for DNO submission | design complete 03 Nov 2026, 21 days (allowed 5) | M | Scheduling | Office (operations) | Submit the G99 application | 26 Nov |
| 13 | SJ-1018 | Waiting for install | scaffold booked 19 Oct 2026, 36 days (allowed 21) | M | Scheduling | Office (operations) | Book a confirmed install date | 26 Nov |
| 14 | SJ-1140 | Invoice BFW-24257 for a job not in the tracker | £1,868.00; closest job IDs SJ-1040, SJ-1014 | M | Unclear | Office (accounts) | Hold payment of BFW-24257 until the job is confirmed; decision needed | 26 Nov |
| 15 | SJ-1008 | Duplicate invoice line | SCAF-COM x1 £1,450.00 on KSL-5324 / again on KSL-5328 | H | Supplier | Kestrel Scaffolding Ltd | Request a credit note for £1,450.00 against KSL-5328 | 24 Nov |
| 16 | SJ-1004 | Price above agreed | SP-430M agreed £104.00 / invoiced £112.32 (+8.0%) on BFW-24115 | M | Supplier | Brightfield Wholesale Ltd | Request a credit note for £332.80 against BFW-24115 | 26 Nov |
| 17 | SJ-1031 | More panels invoiced than fitted | SP-430M installed 14 / invoiced 16 (£208.00) | M | Unclear | Office (purchasing) | Confirm delivered and fitted quantities with Installer Team A; decision needed | 26 Nov |
| 18 | SJ-1019 | Price above agreed | INV-3.6S agreed £620.00 / invoiced £651.00 (+5.0%) on BFW-24164 | M | Supplier | Brightfield Wholesale Ltd | Request a credit note for £31.00 against BFW-24164 | 26 Nov |
| 19 | SJ-1016 | Installed with no installation record | tracker installed 20 Nov 2026 / no record | M | Data entry | Office (operations) | Obtain the installation record from the team that fitted it | 26 Nov |
| 20 | SJ-1003 | Panel count differs | tracker 12 panels / installer 10 panels | M | Unclear | Design | Confirm the fitted count with Installer Team B; decision needed | 26 Nov |
| 21 | SJ-1030 | System size does not match panels fitted | tracker 3.40 kWp / installed 10 x 430 W = 4.30 kWp | M | Data entry | Office (operations) | Correct the tracker to 4.30 kWp | 26 Nov |
| 22 | SJ-1033 | Install date differs | tracker 15 Aug 2026 / installer 08 Aug 2026 | L | Data entry | Installer Team B | Confirm the actual install date | 30 Nov |
| 23 | SJ-1021 | Survey date missing | stage design complete / survey date blank | L | Data entry | Office (operations) | Enter the survey date from the survey record | 30 Nov |

## 6. Draft communications (not sent)

| File | To | Covers | Held pending decision |
|---|---|---|---|
| `draft_emails/to_office_compliance.md` | Office (compliance) | SJ-1002, SJ-1011, SJ-1007, SJ-1039, SJ-1036 | None |
| `draft_emails/to_office_operations.md` | Office (operations) | SJ-1012, SJ-1005, SJ-1018, SJ-1016, SJ-1030, SJ-1021 | None |
| `draft_emails/to_kestrel_scaffolding.md` | Kestrel Scaffolding Ltd | SJ-1008 | None |
| `draft_emails/to_brightfield_wholesale.md` | Brightfield Wholesale Ltd | SJ-1004, SJ-1019 | SJ-1140, SJ-1031 |
| `draft_emails/to_installer_team_b.md` | Installer Team B | SJ-1033 | SJ-1027, SJ-1003 |
| `draft_emails/to_installer_team_c.md` | Installer Team C | SJ-1025 | SJ-1014 |

No draft for Design, Office (accounts), Office (purchasing) or the Operations manager: every item they own is a decision in section 1. No draft for Installer Team A: its items (SJ-1009, SJ-1023, SJ-1031) are all held pending decision.

---
*Facts from `run_checks.py`; classification and wording by the review step and validated against the facts.
Thresholds are business settings in `config/rules.yaml`; regulatory timings to be checked against current ENA/MCS
guidance. Nothing has been sent or changed.*
