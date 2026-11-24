"""Solar Job Exceptions Checker - deterministic checks.

Reads the five source files (read-only), applies the rules in config/rules.yaml
and writes:

    output/YYYY-MM-DD/exceptions.json    every exception, with evidence (for Claude)
    output/YYYY-MM-DD/checks_summary.md  facts-only summary (readable without Claude)
    output/run_log.csv                   one row per run date, for trend tracking

This script does the arithmetic and the comparisons. It does NOT decide root
causes, owners or wording - that is Claude's job (see SKILL.md). It never
edits the source data and never sends anything.

Usage:
    python scripts/run_checks.py                          # as of today, data/sample
    python scripts/run_checks.py --as-of 2026-11-23
    python scripts/run_checks.py --data data/live --out output
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import difflib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

GROUPS = {"A": "Flow", "B": "Mismatch", "C": "Compliance", "D": "Supplier invoices", "X": "Data quality"}
CHECK_NAMES = {
    "X1": "Bad or duplicate source record",
    "A1": "Stuck in stage", "A2": "Missing stage date", "A3": "Dates out of order",
    "B1": "Panel count mismatch", "B2": "Panel model mismatch", "B3": "Inverter mismatch",
    "B4": "Battery mismatch", "B5": "kWp mismatch", "B6": "Date mismatch",
    "B7": "No installation record",
    "C1": "Post-commissioning item overdue", "C2": "Complete with documents missing",
    "D1": "Price above agreed price", "D2": "Duplicate invoice line",
    "D3": "Invoice for unknown job", "D4": "Invoiced more than installed",
    "D5": "Item not on price list",
}
DOC_LABELS = {
    "mcs_certificate": "MCS certificate", "electrical_installation_certificate": "Electrical installation certificate",
    "g98_notification": "G98 notification", "g99_notification": "G99 notification",
    "panel_warranty": "Panel warranty registration", "inverter_warranty": "Inverter warranty registration",
    "battery_warranty": "Battery warranty registration", "handover_pack": "Handover pack",
}


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def d(value: str):
    return dt.date.fromisoformat(value) if value else None


def fmt(date) -> str:
    return date.strftime("%d %b %Y") if date else "blank"


def money(x: float) -> str:
    return f"£{x:,.2f}"


# ----------------------------------------------------------------------------
# Input validation
# Fatal problems (missing file / column, broken rules file) stop the run with a
# clear message - a failed run must never be logged as a clean day.
# Row-level problems (bad date, non-number, unknown code, duplicate ID) become
# X1 exceptions; that record is quarantined so it cannot cause false alarms.
# ----------------------------------------------------------------------------
class InputError(Exception):
    pass


KIND_TEXT = {"id": "a non-blank ID", "date": "a date as YYYY-MM-DD (or blank)", "date_req": "a date as YYYY-MM-DD",
             "int": "a whole number", "num": "a number", "num_opt": "a number (or blank)",
             "pos": "a number above zero", "yn": "Y, N or blank"}


def _valid(value: str, kind) -> bool:
    if isinstance(kind, tuple):  # ("enum", allowed)
        return value in kind[1]
    if kind == "id":
        return bool(value)
    if kind in ("date", "date_req"):
        if not value:
            return kind == "date"
        try:
            dt.date.fromisoformat(value)
            return len(value) == 10
        except ValueError:
            return False
    if kind == "yn":
        return value.upper() in ("", "Y", "N")
    if kind == "num_opt" and not value:
        return True
    try:
        x = int(value) if kind == "int" else float(value)
    except ValueError:
        return False
    return x > 0 if kind == "pos" else x >= 0


def validate_rules(rules) -> None:
    if not isinstance(rules, dict):
        raise InputError("config/rules.yaml is empty or not valid YAML")
    for key in ("stages", "post_commissioning", "date_order", "required_documents", "tolerances", "severity"):
        if key not in rules:
            raise InputError(f"config/rules.yaml is missing the '{key}' section")
    for s in rules["stages"]:
        if "max_days" in s and not (isinstance(s["max_days"], int) and s["max_days"] >= 0):
            raise InputError(f"config/rules.yaml: stage '{s.get('name')}' max_days must be a whole number >= 0")
    for k, v in rules["post_commissioning"].items():
        if not (isinstance(v.get("max_days"), int) and v["max_days"] >= 0):
            raise InputError(f"config/rules.yaml: post_commissioning '{k}' max_days must be a whole number >= 0")
    for k in ("price_over_list_pct", "kwp_difference"):
        if not isinstance(rules["tolerances"].get(k), (int, float)):
            raise InputError(f"config/rules.yaml: tolerances.{k} must be a number")


def file_specs(rules) -> dict:
    stages = [s["name"] for s in rules["stages"]]
    dates = [f"date_{s}" for s in stages] + [f"date_{k}" for k in rules["post_commissioning"]]
    return {
        "job_tracker.csv": ("job_id", [("job_id", "id"), ("job_type", ("enum", set(rules["required_documents"]))),
                                       ("dno_route", ("enum", {"G98", "G99"})),
                                       ("current_stage", ("enum", set(stages) | {"complete"})),
                                       *[(c, "date") for c in dates], ("system_kwp", "num"),
                                       ("panel_model", "id"), ("panel_count", "int"),
                                       ("inverter_model", "id"), ("battery_model", None)]),
        "installation_records.csv": ("job_id", [("job_id", "id"), ("installer_team", None),
                                                ("install_date", "date"), ("panel_count", "int"),
                                                ("panel_model", "id"), ("inverter_model", "id"),
                                                ("battery_model", None), ("commissioning_date", "date")]),
        "supplier_invoices.csv": (None, [("invoice_no", "id"), ("supplier", "id"), ("job_id", "id"), ("item", "id"),
                                         ("quantity", "pos"), ("unit_price_gbp", "num"),
                                         ("invoice_date", "date_req")]),
        "price_list.csv": ("item", [("supplier", "id"), ("item", "id"), ("category", "id"),
                                    ("agreed_unit_price_gbp", "num"), ("watts", "num_opt")]),
        "documents_index.csv": ("job_id", [("job_id", "id"), *[(d, "yn") for d in DOC_LABELS]]),
    }


class Checker:
    def __init__(self, data_dir: Path, rules: dict, as_of: dt.date):
        validate_rules(rules)
        self.rules = rules
        self.as_of = as_of
        self.issues: list[dict] = []
        # quarantined records: excluded from other checks so a bad row can't raise false alarms
        self.q = {"jobs": set(), "records": set(), "docs": set(), "items": set()}
        specs = file_specs(rules)
        self.jobs = self._load(data_dir, "job_tracker.csv", specs, "jobs")
        self.records = self._load(data_dir, "installation_records.csv", specs, "records")
        self.invoices = self._load(data_dir, "supplier_invoices.csv", specs, None)
        self.prices = self._load(data_dir, "price_list.csv", specs, "items")
        self.docs = self._load(data_dir, "documents_index.csv", specs, "docs")
        if not self.jobs and not self.q["jobs"]:
            raise InputError("job_tracker.csv has no jobs in it")
        self.stage_rules = rules["stages"]
        self.limits = {s["name"]: s.get("max_days") for s in self.stage_rules}
        self.exceptions: list[dict] = []

    def _load(self, data_dir: Path, name: str, specs: dict, qkey):
        path = data_dir / name
        if not path.exists():
            raise InputError(f"Missing input file: {path}")
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                header = reader.fieldnames or []
                rows = [{k: (v or "").strip() for k, v in r.items() if k is not None} for r in reader]
        except UnicodeDecodeError:
            raise InputError(f"{name} is not UTF-8 text - re-export it as CSV (UTF-8)")
        unique_by, spec = specs[name]
        missing = [c for c, _ in spec if c not in header]
        if missing:
            raise InputError(f"{name} is missing column(s): {', '.join(missing)}")

        good = []
        for line, row in enumerate(rows, start=2):  # line 1 is the header
            bad = [(c, k) for c, k in spec if k is not None and not _valid(row.get(c, ""), k)]
            if not bad:
                good.append(row)
                continue
            for c, k in bad:
                expected = f"one of {', '.join(sorted(k[1]))}" if isinstance(k, tuple) else KIND_TEXT[k]
                self._issue(name, line, row, c, row.get(c, ""), f"{c} should be {expected}")
            if qkey:
                self.q[qkey].add(row.get(unique_by) or f"line {line}")

        if unique_by is None:
            return good
        counts = Counter(r[unique_by] for r in good)
        for r in good:
            if counts[r[unique_by]] > 1 and r[unique_by] not in self.q[qkey]:
                lines = [i for i, x in enumerate(rows, start=2) if x.get(unique_by) == r[unique_by]]
                self._issue(name, lines[0], r, unique_by, r[unique_by],
                            f"duplicate {unique_by} on lines {', '.join(map(str, lines))}")
                self.q[qkey].add(r[unique_by])
        return {r[unique_by]: r for r in good if r[unique_by] not in self.q[qkey]}

    def _issue(self, name, line, row, field, value, problem):
        if name == "supplier_invoices.csv":
            ref = f"{row.get('invoice_no', '')}:{row.get('item', '')}:"
        elif name == "price_list.csv":
            ref = f"{row.get('item', '')}:"
        else:
            ref = ""
        self.issues.append({"file": name, "line": line, "job_id": row.get("job_id") or "(price list)",
                            "detail": f"{name}:{ref}{field}", "field": field, "value": value, "problem": problem})

    def add_issues(self):
        for i in self.issues:
            self.add(i["job_id"], "X1", i["detail"], f"{i['file']} line {i['line']}: {i['problem']}",
                     i["problem"].split(" should be ")[-1] if " should be " in i["problem"] else "unique ID",
                     f"'{i['value']}'" if i["value"] else "blank",
                     review="Fix the record in the source system. Other checks for this record were skipped "
                            "until it is fixed, so they can't raise false alarms.",
                     source_file=i["file"], source_line=i["line"])

    # -- recording -------------------------------------------------------------
    def add(self, job_id, check, detail, what, expected, found, review=None, **context):
        self.exceptions.append({
            "key": f"{job_id}|{check}|{detail}",
            "job_id": job_id,
            "check": check,
            "check_name": CHECK_NAMES[check],
            "group": f"{check[0]} {GROUPS[check[0]]}",
            "detail": detail,
            "what_is_wrong": what,
            "expected": expected,
            "found": found,
            "severity": self.rules["severity"].get(check, "medium"),
            "needs_human_review": review is not None,
            "review_reason": review or "",
            "context": {k: v for k, v in context.items() if v not in (None, "")},
        })

    def route_seq(self, job) -> list[str]:
        return [s["name"] for s in self.stage_rules
                if not (s.get("g99_only") and job["dno_route"] != "G99")]

    def job_ctx(self, job):
        rec = self.records.get(job["job_id"], {})
        return {"job_type": job["job_type"], "dno_route": job["dno_route"],
                "current_stage": job["current_stage"], "installer_team": rec.get("installer_team")}

    # -- A: flow -----------------------------------------------------------------
    def check_flow(self):
        for job_id, job in self.jobs.items():
            seq = self.route_seq(job)
            stage = job["current_stage"]
            ctx = self.job_ctx(job)
            reached = seq if stage == "complete" else seq[: seq.index(stage) + 1] if stage in seq else []

            # A2 missing dates for every stage the job has reached
            for s in reached:
                if not job.get(f"date_{s}"):
                    self.add(job_id, "A2", s, f"Current stage is '{stage}' but no {s} date is recorded",
                             f"{s} date: a date", f"{s} date: blank", **ctx)

            # A1 stuck waiting for the next pre-commissioning stage
            if stage in seq and stage != "commissioned":
                nxt = seq[seq.index(stage) + 1]
                since = d(job.get(f"date_{stage}"))
                limit = self.limits[nxt]
                if since and limit is not None:
                    waited = (self.as_of - since).days
                    if waited > limit:
                        self.add(job_id, "A1", nxt,
                                 f"Waiting {waited} days for {nxt} since {stage} on {fmt(since)} (allowed {limit})",
                                 f"{nxt} within {limit} days", f"{waited} days and counting",
                                 days_over=waited - limit, **ctx)

            # A3 dates out of order
            for earlier, later in self.rules["date_order"]:
                e, l = d(job.get(f"date_{earlier}")), d(job.get(f"date_{later}"))
                if e and l and l < e:
                    self.add(job_id, "A3", f"{earlier}>{later}",
                             f"{later} ({fmt(l)}) is dated before {earlier} ({fmt(e)})",
                             f"{earlier} on or before {later}",
                             f"{earlier}: {fmt(e)}, {later}: {fmt(l)}", days_over=(e - l).days, **ctx)

    # -- B: tracker vs installation record ---------------------------------------
    def check_mismatch(self):
        tol = float(self.rules["tolerances"]["kwp_difference"])
        for job_id, job in self.jobs.items():
            if not job.get("date_installed"):
                continue
            if job_id in self.q["records"]:
                continue  # installation record quarantined (X1) - can't compare against it
            ctx = self.job_ctx(job)
            rec = self.records.get(job_id)
            if rec is None:
                self.add(job_id, "B7", "install_record",
                         "Tracker shows the job installed but there is no installation record",
                         f"installation record for install on {fmt(d(job['date_installed']))}",
                         "no record", **ctx)
                continue
            count_ok = model_ok = True
            if int(job["panel_count"]) != int(rec["panel_count"]):
                count_ok = False
                self.add(job_id, "B1", "panel_count", "Panel count differs between tracker and installation record",
                         f"tracker: {job['panel_count']} panels", f"installer: {rec['panel_count']} panels", **ctx)
            subst = ("Could be an approved on-site substitution. Confirm which record is right "
                     "before changing either, and check design/DNO paperwork still matches.")
            for check, field, label in (("B2", "panel_model", "Panel model"),
                                        ("B3", "inverter_model", "Inverter model"),
                                        ("B4", "battery_model", "Battery model")):
                if job[field] != rec[field]:
                    if field == "panel_model":
                        model_ok = False
                    self.add(job_id, check, field, f"{label} differs between tracker and installation record",
                             f"tracker: {job[field] or 'none'}", f"installer: {rec[field] or 'none'}",
                             review=subst, **ctx)
            # kWp only when count and model agree (otherwise B1/B2 already explain it)
            watts = self.prices.get(rec["panel_model"], {}).get("watts")
            if count_ok and model_ok and watts:
                installed_kwp = int(rec["panel_count"]) * float(watts) / 1000
                if abs(installed_kwp - float(job["system_kwp"])) > tol:
                    self.add(job_id, "B5", "kwp", "System size in tracker does not match panels installed",
                             f"tracker: {float(job['system_kwp']):.2f} kWp",
                             f"installed: {rec['panel_count']} x {watts} W = {installed_kwp:.2f} kWp", **ctx)
            for field, rfield in (("install_date", "date_installed"), ("commissioning_date", "date_commissioned")):
                if rec[field] and job.get(rfield) and rec[field] != job[rfield]:
                    self.add(job_id, "B6", field, f"{field.replace('_', ' ').capitalize()} differs",
                             f"tracker: {fmt(d(job[rfield]))}", f"installer: {fmt(d(rec[field]))}", **ctx)

    # -- C: compliance -----------------------------------------------------------
    def check_compliance(self):
        post = self.rules["post_commissioning"]
        for job_id, job in self.jobs.items():
            ctx = self.job_ctx(job)
            comm = d(job.get("date_commissioned"))
            if comm:
                age = (self.as_of - comm).days
                for item, cfg in post.items():
                    if not job.get(f"date_{item}") and age > cfg["max_days"]:
                        self.add(job_id, "C1", item,
                                 f"{cfg['label']} not done, {age} days after commissioning (allowed {cfg['max_days']})",
                                 f"{cfg['label']} within {cfg['max_days']} days of {fmt(comm)}",
                                 f"not recorded after {age} days", days_over=age - cfg["max_days"], **ctx)
            if job["current_stage"] == "complete" and job_id not in self.q["docs"]:
                required = self.rules["required_documents"].get(job["job_type"], [])
                dno_form = "g99_notification" if job["dno_route"] == "G99" else "g98_notification"
                required = [dno_form if r == "dno_form" else r for r in required]
                have = self.docs.get(job_id, {})
                missing = [r for r in required if have.get(r, "N").upper() != "Y"]
                if missing:
                    self.add(job_id, "C2", "documents", "Job marked complete but the document set is incomplete",
                             "all required: " + ", ".join(DOC_LABELS[r] for r in required),
                             "missing: " + ", ".join(DOC_LABELS[r] for r in missing), missing=missing, **ctx)

    # -- D: supplier invoices ----------------------------------------------------
    def check_invoices(self):
        tol = float(self.rules["tolerances"]["price_over_list_pct"])
        seen = {}
        counted = defaultdict(float)  # (job, item) -> qty, excluding duplicate lines
        unknown_reported = set()
        for line in self.invoices:
            job_id, item, no = line["job_id"], line["item"], line["invoice_no"]
            qty, unit = float(line["quantity"]), float(line["unit_price_gbp"])
            ctx = {"supplier": line["supplier"], "invoice_no": no, "invoice_date": line["invoice_date"]}

            if job_id not in self.jobs and job_id not in self.q["jobs"] and no not in unknown_reported:
                unknown_reported.add(no)
                close = difflib.get_close_matches(job_id, self.jobs.keys(), n=2, cutoff=0.7)
                total = sum(float(l["quantity"]) * float(l["unit_price_gbp"])
                            for l in self.invoices if l["invoice_no"] == no)
                self.add(job_id, "D3", no, f"Invoice {no} is for {job_id}, which is not in the job tracker",
                         "job ID in tracker", f"{job_id} not found",
                         review=("Could be a supplier typo" + (f" (closest: {', '.join(close)})" if close else "")
                                 + ", a cancelled job, or a job missing from the tracker. Do not pay until confirmed."),
                         value_at_risk_gbp=round(total, 2), **ctx)

            sig = (line["supplier"], job_id, item, line["quantity"], line["unit_price_gbp"])
            if sig in seen:
                self.add(job_id, "D2", f"{no}:{item}",
                         f"{item} x{line['quantity']} at {money(unit)} billed again (first on {seen[sig]})",
                         f"billed once on {seen[sig]}", f"billed again on {no}",
                         value_at_risk_gbp=round(qty * unit, 2), first_invoice=seen[sig], **ctx)
                continue  # don't count the duplicate in quantity checks
            seen[sig] = no
            counted[(job_id, item)] += qty

            if item in self.q["items"]:
                continue  # price list entry quarantined (X1) - can't price-check against it
            agreed = self.prices.get(item)
            if agreed is None:
                self.add(job_id, "D5", f"{no}:{item}", f"{item} is not on the agreed price list",
                         "item on price list", f"{item} at {money(unit)}",
                         review="New or substitute item. Agree a price before paying.", **ctx)
                continue
            list_price = float(agreed["agreed_unit_price_gbp"])
            over_pct = (unit - list_price) / list_price * 100
            if over_pct > tol + 1e-9:
                self.add(job_id, "D1", f"{no}:{item}",
                         f"{item} charged {over_pct:.1f}% above agreed price (tolerance {tol:g}%)",
                         f"agreed: {money(list_price)} each", f"invoiced: {money(unit)} each",
                         value_at_risk_gbp=round((unit - list_price) * qty, 2), over_pct=round(over_pct, 1), **ctx)

        # D4 quantity invoiced vs installed (panels, inverters, batteries)
        for (job_id, item), qty in counted.items():
            rec = self.records.get(job_id)
            cat = self.prices.get(item, {}).get("category")
            if rec is None or job_id in self.q["jobs"] or cat not in ("panel", "inverter", "battery"):
                continue
            field = {"panel": "panel_model", "inverter": "inverter_model", "battery": "battery_model"}[cat]
            installed = (int(rec["panel_count"]) if cat == "panel" else 1) if rec[field] == item else 0
            if qty > installed:
                price = float(self.prices[item]["agreed_unit_price_gbp"])
                suppliers = sorted({l["supplier"] for l in self.invoices if l["job_id"] == job_id and l["item"] == item})
                self.add(job_id, "D4", item, f"More {item} invoiced than the installer recorded fitting",
                         f"installed: {installed}", f"invoiced: {qty:g}",
                         value_at_risk_gbp=round((qty - installed) * price, 2),
                         supplier=", ".join(suppliers), installer_team=rec.get("installer_team"))

    def run(self):
        self.add_issues()
        self.check_flow()
        self.check_mismatch()
        self.check_compliance()
        self.check_invoices()
        order = {"high": 0, "medium": 1, "low": 2}
        self.exceptions.sort(key=lambda e: (order[e["severity"]], e["check"], e["job_id"]))
        return self.exceptions


# ----------------------------------------------------------------------------
# Outputs
# ----------------------------------------------------------------------------
def previous_run(out_root: Path, run_date: str):
    dated = sorted(p for p in out_root.glob("????-??-??") if p.name < run_date and (p / "exceptions.json").exists())
    if not dated:
        return None, {}
    data = json.loads((dated[-1] / "exceptions.json").read_text(encoding="utf-8"))
    return dated[-1].name, {e["key"]: e for e in data["exceptions"]}


def write_summary(path: Path, payload: dict):
    s = payload["summary"]
    lines = [
        f"# Solar job exceptions - checks summary ({payload['as_of']})",
        "",
        "Facts only, produced by `run_checks.py`. Root cause, owner and next action are added by Claude "
        "in `exceptions_report.md`. Nothing has been sent or changed.",
        "",
        f"- Jobs checked: {payload['jobs_checked']} | invoice lines checked: {payload['invoice_lines_checked']}",
        f"- Open exceptions: **{s['total']}** (new {s['new']}, carried over {s['carried_over']}, "
        f"closed since last run {s['closed_since_last_run']}; previous run: {payload['previous_run'] or 'none'})",
        f"- Needs human review: {s['needs_review']} | money at risk on invoices: {money(s['value_at_risk_gbp'])}",
        "",
        "| Check group | High | Medium | Low | Total |",
        "|---|---|---|---|---|",
    ]
    for g in GROUPS:
        row = s["by_group_severity"].get(g, {})
        lines.append(f"| {g} {GROUPS[g]} | {row.get('high', 0)} | {row.get('medium', 0)} | {row.get('low', 0)} | "
                     f"{sum(row.values())} |")
    lines += ["", "| # | Job | Check | What is wrong | Expected | Found | Severity | Status | Review? |",
              "|---|---|---|---|---|---|---|---|---|"]
    for i, e in enumerate(payload["exceptions"], 1):
        lines.append(f"| {i} | {e['job_id']} | {e['check']} {e['check_name']} | {e['what_is_wrong']} | "
                     f"{e['expected']} | {e['found']} | {e['severity']} | {e['status']} | "
                     f"{'Yes' if e['needs_human_review'] else ''} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


LOG_FIELDS = ["run_date", "jobs_checked", "total_open", "A_flow", "B_mismatch", "C_compliance", "D_invoices",
              "X_data_quality", "high", "medium", "low", "needs_review", "new", "carried_over",
              "closed_since_last_run", "value_at_risk_gbp"]


def update_log(log_path: Path, payload: dict):
    s = payload["summary"]
    row = {"run_date": payload["as_of"], "jobs_checked": payload["jobs_checked"], "total_open": s["total"],
           "A_flow": s["by_group"].get("A", 0), "B_mismatch": s["by_group"].get("B", 0),
           "C_compliance": s["by_group"].get("C", 0), "D_invoices": s["by_group"].get("D", 0),
           "X_data_quality": s["by_group"].get("X", 0),
           "high": s["by_severity"].get("high", 0), "medium": s["by_severity"].get("medium", 0),
           "low": s["by_severity"].get("low", 0), "needs_review": s["needs_review"], "new": s["new"],
           "carried_over": s["carried_over"], "closed_since_last_run": s["closed_since_last_run"],
           "value_at_risk_gbp": f"{s['value_at_risk_gbp']:.2f}"}
    rows = read_csv(log_path) if log_path.exists() else []
    rows = [r for r in rows if r["run_date"] != row["run_date"]]  # a re-run on the same day replaces that day
    rows.append(row)
    rows.sort(key=lambda r: r["run_date"])
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--as-of", default=dt.date.today().isoformat(), help="check date, YYYY-MM-DD (default today)")
    ap.add_argument("--data", default=str(ROOT / "data" / "sample"))
    ap.add_argument("--rules", default=str(ROOT / "config" / "rules.yaml"))
    ap.add_argument("--out", default=str(ROOT / "output"))
    args = ap.parse_args()

    as_of = dt.date.fromisoformat(args.as_of)
    out_root = Path(args.out)
    run_dir = out_root / as_of.isoformat()
    (run_dir / "draft_emails").mkdir(parents=True, exist_ok=True)
    error_note = run_dir / "INPUT_ERROR.md"
    try:
        try:
            rules = yaml.safe_load(Path(args.rules).read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as e:
            raise InputError(f"Could not read {args.rules}: {e}")
        checker = Checker(Path(args.data), rules, as_of)
        exceptions = checker.run()
    except InputError as e:
        # Stop clearly. Nothing is written to the run log, so a broken input can never look like a clean day.
        error_note.write_text(
            f"# Input error - {as_of}\n\nThe checks did not run, so there are no results for today.\n\n"
            f"**Problem:** {e}\n\nFix the input file (or `config/rules.yaml`) and run again. "
            f"The run log has not been updated.\n", encoding="utf-8")
        print(f"INPUT ERROR: {e}", file=sys.stderr)
        return 2
    if error_note.exists():
        error_note.unlink()

    prev_date, prev = previous_run(out_root, as_of.isoformat())
    for e in exceptions:
        if e["key"] in prev:
            e["status"] = "carried_over"
            e["first_seen"] = prev[e["key"]].get("first_seen", prev_date)
        else:
            e["status"] = "new"
            e["first_seen"] = as_of.isoformat()
    keys = {e["key"] for e in exceptions}

    by_gs = defaultdict(Counter)
    for e in exceptions:
        by_gs[e["check"][0]][e["severity"]] += 1
    summary = {
        "total": len(exceptions),
        "by_group": {g: sum(c.values()) for g, c in by_gs.items()},
        "by_severity": dict(Counter(e["severity"] for e in exceptions)),
        "by_check": dict(Counter(e["check"] for e in exceptions)),
        "by_group_severity": {g: dict(c) for g, c in by_gs.items()},
        "needs_review": sum(e["needs_human_review"] for e in exceptions),
        "new": sum(e["status"] == "new" for e in exceptions),
        "carried_over": sum(e["status"] == "carried_over" for e in exceptions),
        "closed_since_last_run": len([k for k in prev if k not in keys]),
        "value_at_risk_gbp": round(sum(e["context"].get("value_at_risk_gbp", 0) for e in exceptions), 2),
    }
    payload = {
        "as_of": as_of.isoformat(),
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "data_dir": str(Path(args.data)),
        "rules_file": str(Path(args.rules)),
        "previous_run": prev_date,
        "closed_since_last_run": sorted(k for k in prev if k not in keys),
        "jobs_checked": len(checker.jobs),
        "invoice_lines_checked": len(checker.invoices),
        "summary": summary,
        "exceptions": exceptions,
    }
    (run_dir / "exceptions.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_summary(run_dir / "checks_summary.md", payload)
    update_log(out_root / "run_log.csv", payload)

    print(f"Checked {len(checker.jobs)} jobs as of {as_of}: {summary['total']} open exceptions "
          f"({summary['new']} new, {summary['carried_over']} carried over, "
          f"{summary['closed_since_last_run']} closed since last run).")
    print("By check: " + ", ".join(f"{k} {v}" for k, v in sorted(summary["by_check"].items())))
    print(f"Needs human review: {summary['needs_review']}. Output: {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
