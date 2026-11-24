# Solar job exceptions - checks summary (2026-11-24)

Facts only, produced by `run_checks.py`. Root cause, owner and next action are added by Claude in `exceptions_report.md`. Nothing has been sent or changed.

- Jobs checked: 40 | invoice lines checked: 151
- Open exceptions: **23** (new 1, carried over 22, closed since last run 0; previous run: 2026-11-23)
- Needs human review: 4 | money at risk on invoices: £3,889.80

| Check group | High | Medium | Low | Total |
|---|---|---|---|---|
| A Flow | 1 | 3 | 1 | 5 |
| B Mismatch | 0 | 6 | 1 | 7 |
| C Compliance | 6 | 0 | 0 | 6 |
| D Supplier invoices | 1 | 4 | 0 | 5 |
| X Data quality | 0 | 0 | 0 | 0 |

| # | Job | Check | What is wrong | Expected | Found | Severity | Status | Review? |
|---|---|---|---|---|---|---|---|---|
| 1 | SJ-1027 | A3 Dates out of order | installed (14 Nov 2026) is dated before dno_approval (19 Nov 2026) | dno_approval on or before installed | dno_approval: 19 Nov 2026, installed: 14 Nov 2026 | high | carried_over |  |
| 2 | SJ-1002 | C1 Post-commissioning item overdue | G98/G99 notification to DNO not done, 61 days after commissioning (allowed 28) | G98/G99 notification to DNO within 28 days of 24 Sep 2026 | not recorded after 61 days | high | carried_over |  |
| 3 | SJ-1007 | C1 Post-commissioning item overdue | MCS certificate issued not done, 13 days after commissioning (allowed 10) | MCS certificate issued within 10 days of 11 Nov 2026 | not recorded after 13 days | high | carried_over |  |
| 4 | SJ-1011 | C1 Post-commissioning item overdue | Handover pack sent to customer not done, 31 days after commissioning (allowed 14) | Handover pack sent to customer within 14 days of 24 Oct 2026 | not recorded after 31 days | high | carried_over |  |
| 5 | SJ-1039 | C1 Post-commissioning item overdue | MCS certificate issued not done, 11 days after commissioning (allowed 10) | MCS certificate issued within 10 days of 13 Nov 2026 | not recorded after 11 days | high | new |  |
| 6 | SJ-1025 | C2 Complete with documents missing | Job marked complete but the document set is incomplete | all required: MCS certificate, Electrical installation certificate, G98 notification, Panel warranty registration, Inverter warranty registration, Handover pack | missing: Electrical installation certificate | high | carried_over |  |
| 7 | SJ-1036 | C2 Complete with documents missing | Job marked complete but the document set is incomplete | all required: MCS certificate, Electrical installation certificate, G98 notification, Panel warranty registration, Inverter warranty registration, Battery warranty registration, Handover pack | missing: Battery warranty registration | high | carried_over |  |
| 8 | SJ-1008 | D2 Duplicate invoice line | SCAF-COM x1 at £1,450.00 billed again (first on KSL-5324) | billed once on KSL-5324 | billed again on KSL-5328 | high | carried_over |  |
| 9 | SJ-1005 | A1 Stuck in stage | Waiting 21 days for dno_submitted since design_complete on 03 Nov 2026 (allowed 5) | dno_submitted within 5 days | 21 days and counting | medium | carried_over |  |
| 10 | SJ-1012 | A1 Stuck in stage | Waiting 71 days for dno_approval since dno_submitted on 14 Sep 2026 (allowed 45) | dno_approval within 45 days | 71 days and counting | medium | carried_over |  |
| 11 | SJ-1018 | A1 Stuck in stage | Waiting 36 days for installed since scaffold_booked on 19 Oct 2026 (allowed 21) | installed within 21 days | 36 days and counting | medium | carried_over |  |
| 12 | SJ-1003 | B1 Panel count mismatch | Panel count differs between tracker and installation record | tracker: 12 panels | installer: 10 panels | medium | carried_over |  |
| 13 | SJ-1009 | B2 Panel model mismatch | Panel model differs between tracker and installation record | tracker: SP-430M | installer: SP-410B | medium | carried_over | Yes |
| 14 | SJ-1014 | B3 Inverter mismatch | Inverter model differs between tracker and installation record | tracker: INV-3.6S | installer: INV-5.0S | medium | carried_over | Yes |
| 15 | SJ-1023 | B4 Battery mismatch | Battery model differs between tracker and installation record | tracker: BAT-10.4 | installer: BAT-5.2 | medium | carried_over | Yes |
| 16 | SJ-1030 | B5 kWp mismatch | System size in tracker does not match panels installed | tracker: 3.40 kWp | installed: 10 x 430 W = 4.30 kWp | medium | carried_over |  |
| 17 | SJ-1016 | B7 No installation record | Tracker shows the job installed but there is no installation record | installation record for install on 20 Nov 2026 | no record | medium | carried_over |  |
| 18 | SJ-1004 | D1 Price above agreed price | SP-430M charged 8.0% above agreed price (tolerance 2%) | agreed: £104.00 each | invoiced: £112.32 each | medium | carried_over |  |
| 19 | SJ-1019 | D1 Price above agreed price | INV-3.6S charged 5.0% above agreed price (tolerance 2%) | agreed: £620.00 each | invoiced: £651.00 each | medium | carried_over |  |
| 20 | SJ-1140 | D3 Invoice for unknown job | Invoice BFW-24257 is for SJ-1140, which is not in the job tracker | job ID in tracker | SJ-1140 not found | medium | carried_over | Yes |
| 21 | SJ-1031 | D4 Invoiced more than installed | More SP-430M invoiced than the installer recorded fitting | installed: 14 | invoiced: 16 | medium | carried_over |  |
| 22 | SJ-1021 | A2 Missing stage date | Current stage is 'design_complete' but no survey date is recorded | survey date: a date | survey date: blank | low | carried_over |  |
| 23 | SJ-1033 | B6 Date mismatch | Install date differs | tracker: 15 Aug 2026 | installer: 08 Aug 2026 | low | carried_over |  |
