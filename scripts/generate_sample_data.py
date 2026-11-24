"""Generate SYNTHETIC sample data for the Solar Job Exceptions Checker.

40 fictional jobs (SJ-1001 to SJ-1040) with pseudonymised customer refs, made-up
product codes and fictional suppliers. No real people, addresses or products.

Specific problems are planted on purpose and written to answer_key.csv so the
checker can be tested: it must find every planted problem and nothing else.
A few "near misses" are also planted (e.g. a price 1.5% over list when the
tolerance is 2%) to prove the checker does not raise false alarms.

Usage:
    python scripts/generate_sample_data.py              # writes data/sample/
    python scripts/generate_sample_data.py --as-of 2026-11-23
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import random
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AS_OF = dt.date(2026, 11, 23)

# ----------------------------------------------------------------------------
# Fictional catalogue and agreed prices (the "rate card")
# ----------------------------------------------------------------------------
BFW = "Brightfield Wholesale Ltd"
VCE = "Volt & Co Electrical Supplies"
KSL = "Kestrel Scaffolding Ltd"

PRICE_LIST = [
    # supplier, item, category, unit, agreed_unit_price, watts
    (BFW, "SP-410B", "panel", "each", 98.00, 410),
    (BFW, "SP-430M", "panel", "each", 104.00, 430),
    (BFW, "SP-450M", "panel", "each", 112.00, 450),
    (BFW, "INV-3.6S", "inverter", "each", 620.00, ""),
    (BFW, "INV-5.0S", "inverter", "each", 740.00, ""),
    (BFW, "HYB-3.6S", "inverter", "each", 1150.00, ""),
    (BFW, "HYB-5.0S", "inverter", "each", 1290.00, ""),
    (BFW, "INV-10T", "inverter", "each", 1480.00, ""),
    (BFW, "INV-15T", "inverter", "each", 1890.00, ""),
    (VCE, "BAT-5.2", "battery", "each", 1850.00, ""),
    (VCE, "BAT-10.4", "battery", "each", 3400.00, ""),
    (VCE, "MK-ROOF", "mounting", "per panel", 38.00, ""),
    (VCE, "ELEC-PACK", "sundries", "per job", 145.00, ""),
    (KSL, "SCAF-DOM", "scaffold", "per job", 650.00, ""),
    (KSL, "SCAF-COM", "scaffold", "per job", 1450.00, ""),
]
PRICE = {row[1]: row[4] for row in PRICE_LIST}
WATTS = {row[1]: row[5] for row in PRICE_LIST if row[2] == "panel"}

PRE_STAGES = ["contract_signed", "survey", "design_complete", "dno_submitted",
              "dno_approval", "scaffold_booked", "installed", "commissioned"]
POST = ["notification_sent", "mcs_issued", "handover_sent"]
DOCS = ["mcs_certificate", "electrical_installation_certificate", "g98_notification",
        "g99_notification", "panel_warranty", "inverter_warranty", "battery_warranty",
        "handover_pack"]

# ----------------------------------------------------------------------------
# Job plan: (stage, segment, battery?, route). Planted problems noted.
# ----------------------------------------------------------------------------
PLAN = {
    1001: ("complete", "domestic", False, "G98"),
    1002: ("commissioned", "domestic", False, "G98"),      # C1 notification overdue
    1003: ("complete", "domestic", False, "G98"),          # B1 panel count
    1004: ("complete", "commercial", False, "G99"),        # D1 panel price high
    1005: ("design_complete", "domestic", True, "G99"),    # A1 stuck before DNO submission
    1006: ("survey", "domestic", False, "G98"),
    1007: ("commissioned", "domestic", False, "G98"),      # C1 MCS overdue
    1008: ("complete", "commercial", False, "G99"),        # D2 duplicate scaffold line
    1009: ("complete", "domestic", False, "G98"),          # B2 panel model
    1010: ("contract_signed", "domestic", False, "G98"),
    1011: ("commissioned", "domestic", True, "G98"),       # C1 handover overdue
    1012: ("dno_submitted", "commercial", False, "G99"),   # A1 stuck awaiting DNO approval
    1013: ("scaffold_booked", "domestic", False, "G98"),
    1014: ("complete", "domestic", False, "G98"),          # B3 inverter
    1015: ("installed", "domestic", False, "G98"),
    1016: ("commissioned", "domestic", False, "G98"),      # B7 no installation record
    1017: ("dno_approval", "commercial", False, "G99"),
    1018: ("scaffold_booked", "domestic", False, "G98"),   # A1 stuck awaiting install
    1019: ("complete", "domestic", False, "G98"),          # D1 inverter price high
    1020: ("design_complete", "commercial", False, "G99"),
    1021: ("design_complete", "domestic", False, "G98"),   # A2 missing survey date
    1022: ("complete", "domestic", True, "G98"),
    1023: ("complete", "domestic", True, "G98"),           # B4 battery
    1024: ("commissioned", "domestic", False, "G98"),
    1025: ("complete", "domestic", False, "G98"),          # C2 missing EIC
    1026: ("survey", "domestic", False, "G98"),
    1027: ("commissioned", "commercial", False, "G99"),    # A3 installed before DNO approval
    1028: ("complete", "commercial", True, "G99"),
    1029: ("installed", "domestic", False, "G98"),
    1030: ("complete", "domestic", False, "G98"),          # B5 kWp typo
    1031: ("complete", "domestic", True, "G98"),           # D4 panels over-invoiced
    1032: ("contract_signed", "domestic", False, "G98"),
    1033: ("complete", "domestic", False, "G98"),          # B6 install date
    1034: ("dno_submitted", "commercial", False, "G99"),
    1035: ("complete", "domestic", True, "G98"),
    1036: ("complete", "domestic", True, "G98"),           # C2 missing battery warranty
    1037: ("commissioned", "domestic", True, "G98"),
    1038: ("complete", "domestic", False, "G98"),          # near miss: price +1.5% (clean)
    1039: ("commissioned", "domestic", False, "G98"),      # near miss: MCS at exactly 10 days (clean)
    1040: ("complete", "commercial", False, "G99"),
}
# Fix "days ago" for the current stage on some jobs (planted or near-miss)
AGO_OVERRIDE = {1002: 60, 1005: 20, 1007: 12, 1011: 30, 1012: 70, 1018: 35,
                1021: 5, 1027: 8, 1039: 10}
TEAM_OVERRIDE = {1003: "Team B", 1033: "Team B", 1009: "Team A", 1014: "Team C",
                 1023: "Team A"}


def load_limits(rules_path: Path):
    rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    limits = {s["name"]: s.get("max_days") for s in rules["stages"]}
    post = {k: v["max_days"] for k, v in rules["post_commissioning"].items()}
    return limits, post


def route_seq(route):
    return [s for s in PRE_STAGES if route == "G99" or s not in ("dno_submitted", "dno_approval")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default=DEFAULT_AS_OF.isoformat())
    ap.add_argument("--out", default=str(ROOT / "data" / "sample"))
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    as_of = dt.date.fromisoformat(args.as_of)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    limits, post_limits = load_limits(ROOT / "config" / "rules.yaml")

    jobs, records, invoices, docs, answers = [], [], [], [], []
    inv_counter = {"BFW": 24100, "VCE": 8800, "KSL": 5300}

    def next_inv(prefix):
        inv_counter[prefix] += rng.randint(1, 9)
        return f"{prefix}-{inv_counter[prefix]}"

    def plant(job_id, check, detail, description):
        answers.append({"key": f"{job_id}|{check}|{detail}", "job_id": job_id,
                        "check": check, "detail": detail, "description": description})

    for n, (stage, segment, battery, route) in PLAN.items():
        job_id = f"SJ-{n}"
        rnd = random.Random(args.seed * 1000 + n)  # per-job stream: stable if plan changes

        # --- Specification -------------------------------------------------
        if segment == "commercial":
            panel_model = rnd.choice(["SP-430M", "SP-450M"])
            panel_count = rnd.randint(24, 40)
            inverter = "INV-15T" if panel_count * WATTS[panel_model] > 13000 else "INV-10T"
            battery_model = "BAT-10.4" if battery else ""
        else:
            panel_model = rnd.choice(["SP-410B", "SP-430M", "SP-450M"])
            panel_count = rnd.randint(8, 16)
            if battery:
                inverter = "HYB-5.0S" if route == "G99" else "HYB-3.6S"
                battery_model = rnd.choice(["BAT-5.2", "BAT-10.4"])
            else:
                inverter = "INV-3.6S"
                battery_model = ""
        if n == 1023:
            battery_model = "BAT-10.4"
        if n == 1030:
            panel_model, panel_count = "SP-430M", 10
        if n == 1031:
            panel_count = 14
        if n == 1003:
            panel_count = 12
        kwp = round(panel_count * WATTS[panel_model] / 1000, 2)
        job_type = f"{segment}_pv" + ("_battery" if battery else "")
        value = (kwp * (1100 if segment == "commercial" else 1350) + 1500
                 + {"": 0, "BAT-5.2": 3200, "BAT-10.4": 5600}[battery_model])
        value = int(round(value, -1))

        # --- Dates -----------------------------------------------------------
        seq = route_seq(route)
        dates = {s: None for s in PRE_STAGES + POST}
        if stage in ("complete", "commissioned"):
            idx = seq.index("commissioned")
            ago = AGO_OVERRIDE.get(n, rnd.randint(30, 200) if stage == "complete" else rnd.randint(1, 9))
        else:
            idx = seq.index(stage)
            nxt = seq[idx + 1]
            ago = AGO_OVERRIDE.get(n, rnd.randint(0, limits[nxt] - 1))
        dates[seq[idx]] = as_of - dt.timedelta(days=ago)
        for k in range(idx, 0, -1):
            lo = 0 if seq[k] == "commissioned" else 1
            gap = rnd.randint(lo, limits[seq[k]])
            dates[seq[k - 1]] = dates[seq[k]] - dt.timedelta(days=gap)
        if dates["commissioned"]:
            for item in POST:
                lim = post_limits[item]
                must = stage == "complete" or ago > lim
                if must or rnd.random() < 0.5:
                    dates[item] = dates["commissioned"] + dt.timedelta(days=rnd.randint(0, min(lim, ago)))

        # --- Planted date problems ------------------------------------------
        if n == 1002:
            dates["notification_sent"] = None
            plant(job_id, "C1", "notification_sent", "Commissioned 60 days ago, no G98 notification sent (limit 28)")
        if n == 1005:
            plant(job_id, "A1", "dno_submitted", "G99 design complete 20 days ago, DNO application not submitted (limit 5)")
        if n == 1007:
            dates["mcs_issued"] = None
            plant(job_id, "C1", "mcs_issued", "Commissioned 12 days ago, no MCS certificate (limit 10)")
        if n == 1011:
            dates["handover_sent"] = None
            plant(job_id, "C1", "handover_sent", "Commissioned 30 days ago, handover pack not sent (limit 14)")
        if n == 1012:
            plant(job_id, "A1", "dno_approval", "G99 application submitted 70 days ago, no DNO approval (limit 45)")
        if n == 1018:
            plant(job_id, "A1", "installed", "Scaffold booked 35 days ago, not installed (limit 21)")
        if n == 1021:
            dates["survey"] = None
            plant(job_id, "A2", "survey", "Design complete but no survey date recorded")
        if n == 1027:
            dates["dno_approval"] = dates["installed"] + dt.timedelta(days=5)
            plant(job_id, "A3", "dno_approval>installed", "G99 job installed 5 days before DNO approval")
        if n == 1039:
            dates["mcs_issued"] = None
            dates["notification_sent"] = dates["commissioned"] + dt.timedelta(days=2)
            dates["handover_sent"] = dates["commissioned"] + dt.timedelta(days=3)

        tracker_kwp = kwp
        if n == 1030:
            tracker_kwp = 3.40  # real 4.30 - digits transposed
            plant(job_id, "B5", "kwp", "Tracker says 3.40 kWp, installed 10 x 430 W = 4.30 kWp")

        jobs.append({
            "job_id": job_id,
            "customer_ref": f"CUST-{rnd.randint(0, 0xFFFFF):05X}",
            "job_type": job_type,
            "dno_route": route,
            "current_stage": stage,
            **{f"date_{s}": (dates[s].isoformat() if dates[s] else "") for s in PRE_STAGES + POST},
            "system_kwp": f"{tracker_kwp:.2f}",
            "panel_model": panel_model,
            "panel_count": panel_count,
            "inverter_model": inverter,
            "battery_model": battery_model,
            "contract_value_gbp": value,
        })

        # --- Installation record -------------------------------------------
        installed = dates["installed"] is not None
        rec = None
        if installed and n == 1016:
            plant(job_id, "B7", "install_record", "Tracker says commissioned, no installation record")
        elif installed:
            rec = {
                "job_id": job_id,
                "installer_team": TEAM_OVERRIDE.get(n, rnd.choice(["Team A", "Team B", "Team C"])),
                "install_date": dates["installed"].isoformat(),
                "panel_count": panel_count,
                "panel_model": panel_model,
                "inverter_model": inverter,
                "battery_model": battery_model,
                "commissioning_date": dates["commissioned"].isoformat() if dates["commissioned"] else "",
            }
            if n == 1003:
                rec["panel_count"] = 10
                plant(job_id, "B1", "panel_count", "Tracker 12 panels, installer recorded 10")
            if n == 1009:
                rec["panel_model"] = "SP-410B" if panel_model != "SP-410B" else "SP-430M"
                plant(job_id, "B2", "panel_model", f"Tracker {panel_model}, installer recorded {rec['panel_model']}")
            if n == 1014:
                rec["inverter_model"] = "INV-5.0S"
                plant(job_id, "B3", "inverter_model", "Tracker INV-3.6S, installer recorded INV-5.0S")
            if n == 1023:
                rec["battery_model"] = "BAT-5.2"
                plant(job_id, "B4", "battery_model", "Tracker BAT-10.4, installer recorded BAT-5.2")
            if n == 1033:
                rec["install_date"] = (dates["installed"] - dt.timedelta(days=7)).isoformat()
                plant(job_id, "B6", "install_date", "Tracker install date and installer record differ by 7 days")
            records.append(rec)

        # --- Supplier invoices (materials bought for every installed job) ----
        if installed:
            src = rec or {"panel_count": panel_count, "panel_model": panel_model,
                          "inverter_model": inverter, "battery_model": battery_model}
            d_mat = dates["installed"] - dt.timedelta(days=rnd.randint(3, 10))
            d_scaf = min(as_of, dates["installed"] + dt.timedelta(days=rnd.randint(1, 7)))
            bfw_no = next_inv("BFW")
            panel_price = PRICE[src["panel_model"]]
            panel_qty = src["panel_count"]
            if n == 1004:
                panel_price = round(panel_price * 1.08, 2)
                plant(job_id, "D1", f"{bfw_no}:{src['panel_model']}", "Panel unit price 8% above agreed price")
            if n == 1038:
                panel_price = round(panel_price * 1.015, 2)  # within 2% tolerance: must NOT be flagged
            if n == 1031:
                panel_qty = 16
                plant(job_id, "D4", src["panel_model"], "16 panels invoiced, 14 installed")
            inv_price = PRICE[src["inverter_model"]]
            if n == 1019:
                inv_price = round(inv_price * 1.05, 2)
                plant(job_id, "D1", f"{bfw_no}:{src['inverter_model']}", "Inverter unit price 5% above agreed price")
            lines = [
                (bfw_no, BFW, src["panel_model"], panel_qty, panel_price, d_mat),
                (bfw_no, BFW, src["inverter_model"], 1, inv_price, d_mat),
            ]
            vce_no = next_inv("VCE")
            if src["battery_model"]:
                lines.append((vce_no, VCE, src["battery_model"], 1, PRICE[src["battery_model"]], d_mat))
            lines.append((vce_no, VCE, "MK-ROOF", src["panel_count"], PRICE["MK-ROOF"], d_mat))
            lines.append((vce_no, VCE, "ELEC-PACK", 1, PRICE["ELEC-PACK"], d_mat))
            scaf = "SCAF-COM" if segment == "commercial" else "SCAF-DOM"
            ksl_no = next_inv("KSL")
            lines.append((ksl_no, KSL, scaf, 1, PRICE[scaf], d_scaf))
            if n == 1008:
                dup_no = next_inv("KSL")
                lines.append((dup_no, KSL, scaf, 1, PRICE[scaf], min(as_of, d_scaf + dt.timedelta(days=14))))
                plant(job_id, "D2", f"{dup_no}:{scaf}", f"Scaffold hire billed twice ({ksl_no} and {dup_no})")
            for (no, sup, item, qty, price, d) in lines:
                invoices.append({"invoice_no": no, "supplier": sup, "job_id": job_id, "item": item,
                                 "quantity": qty, "unit_price_gbp": f"{price:.2f}",
                                 "invoice_date": d.isoformat()})

        # --- Documents index ---------------------------------------------------
        drow = {"job_id": job_id, **{d: "N" for d in DOCS}}
        if dates["commissioned"]:
            drow["electrical_installation_certificate"] = "Y"
            drow["mcs_certificate"] = "Y" if dates["mcs_issued"] else "N"
            drow["g98_notification" if route == "G98" else "g99_notification"] = "Y" if dates["notification_sent"] else "N"
            drow["handover_pack"] = "Y" if dates["handover_sent"] else "N"
            for w in ("panel_warranty", "inverter_warranty"):
                drow[w] = "Y" if (stage == "complete" or rnd.random() < 0.5) else "N"
            if battery:
                drow["battery_warranty"] = "Y" if (stage == "complete" or rnd.random() < 0.5) else "N"
        if n == 1025:
            drow["electrical_installation_certificate"] = "N"
            plant(job_id, "C2", "documents", "Marked complete, electrical installation certificate missing")
        if n == 1036:
            drow["battery_warranty"] = "N"
            plant(job_id, "C2", "documents", "Marked complete, battery warranty registration missing")
        docs.append(drow)

    # --- Invoice for a job that is not in the tracker --------------------------
    ghost_no = next_inv("BFW")
    ghost_date = (as_of - dt.timedelta(days=9)).isoformat()
    for item, qty in (("SP-430M", 12), ("INV-3.6S", 1)):
        invoices.append({"invoice_no": ghost_no, "supplier": BFW, "job_id": "SJ-1140", "item": item,
                         "quantity": qty, "unit_price_gbp": f"{PRICE[item]:.2f}", "invoice_date": ghost_date})
    plant("SJ-1140", "D3", ghost_no, "Invoice for job SJ-1140, which is not in the tracker")

    # --- Write files -----------------------------------------------------------
    def write(name, rows, fields=None):
        fields = fields or list(rows[0].keys())
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

    write("job_tracker.csv", jobs)
    write("installation_records.csv", records)
    write("supplier_invoices.csv", invoices)
    write("price_list.csv", [dict(zip(["supplier", "item", "category", "unit", "agreed_unit_price_gbp", "watts"], r))
                             for r in PRICE_LIST])
    write("documents_index.csv", docs)
    write("answer_key.csv", answers)
    print(f"Wrote {len(jobs)} jobs, {len(records)} installation records, {len(invoices)} invoice lines, "
          f"{len(answers)} planted problems to {out} (as of {as_of})")


if __name__ == "__main__":
    main()
