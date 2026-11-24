"""Build output/dashboard.html: the page the operations team actually uses.

One self-contained HTML file (no server, no internet and no Claude needed to view it) covering every run in output/:
status, headline measures, today's decisions and priority actions, analytics (root causes, workload by owner,
money at risk by supplier, ageing), the full action register, the report, draft emails, run history and logs.

Run automatically at the end of scripts/run_daily.ps1, or by hand:
    python scripts/build_dashboard.py
"""
from __future__ import annotations

import csv
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
sys.path.insert(0, str(ROOT / "scripts"))
from validate_actions import validate  # noqa: E402


# ----------------------------------------------------------------------------
# Minimal Markdown -> HTML (headings, tables, lists, quotes, code, bold/italic)
# ----------------------------------------------------------------------------
def _inline(t: str) -> str:
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)([^*\n]+?)\*(?![\w*])", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', t)
    return t.replace("[ ]", "&#9744;").replace("[x]", "&#9745;")


LIST_RE = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")


def md_to_html(md: str) -> str:
    lines = md.replace("\r\n", "\n").split("\n")
    out, i = [], 0

    def block_start(s: str) -> bool:
        return (s.startswith(("#", "|", ">", "```")) or re.fullmatch(r"-{3,}", s) is not None
                or LIST_RE.match(s) is not None)

    while i < len(lines):
        raw, s = lines[i], lines[i].strip()
        if not s:
            i += 1
        elif s.startswith("```"):
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            out.append("<pre>" + html.escape("\n".join(buf)) + "</pre>")
        elif m := re.match(r"(#{1,6})\s+(.*)", s):
            n = len(m.group(1))
            out.append(f"<h{n}>{_inline(m.group(2))}</h{n}>"); i += 1
        elif re.fullmatch(r"-{3,}", s):
            out.append("<hr>"); i += 1
        elif s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            head, body = rows[0], [r for r in rows[1:] if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
            t = "<div class='tw'><table><thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
            t += "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in body)
            out.append(t + "</tbody></table></div>")
        elif s.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].lstrip()); i += 1
            out.append("<blockquote>" + md_to_html("\n".join(buf)) + "</blockquote>")
        elif LIST_RE.match(raw):
            stack, parts = [], []
            while i < len(lines) and (LIST_RE.match(lines[i]) or (lines[i].startswith("   ") and lines[i].strip() and stack)):
                m = LIST_RE.match(lines[i])
                if not m:
                    parts[-1] = parts[-1][:-5] + " " + _inline(lines[i].strip()) + "</li>"
                    i += 1; continue
                level = min(len(m.group(1).replace("\t", "  ")) // 2, 3)
                tag = "ol" if m.group(2)[0].isdigit() else "ul"
                while len(stack) > level + 1 or (stack and len(stack) == level + 1 and stack[-1] != tag):
                    parts.append(f"</{stack.pop()}>")
                while len(stack) < level + 1:
                    stack.append(tag); parts.append(f"<{tag}>")
                parts.append(f"<li>{_inline(m.group(3))}</li>")
                i += 1
            while stack:
                parts.append(f"</{stack.pop()}>")
            out.append("".join(parts))
        else:
            buf = []
            while i < len(lines) and lines[i].strip() and not block_start(lines[i].strip()):
                buf.append(lines[i].strip()); i += 1
            out.append("<p>" + _inline(" ".join(buf)) + "</p>")
    return "\n".join(out)


# ----------------------------------------------------------------------------
# Collect runs
# ----------------------------------------------------------------------------
def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def collect():
    runs = []
    for d in sorted(OUT.glob("????-??-??"), reverse=True):
        exc_path = d / "exceptions.json"
        data = json.loads(read_text(exc_path)) if exc_path.exists() else None
        report = d / "exceptions_report.md"
        if (d / "INPUT_ERROR.md").exists():
            status, note = "input_error", read_text(d / "INPUT_ERROR.md")
        elif (d / "RUN_FAILED.md").exists():
            status, note = "incomplete", read_text(d / "RUN_FAILED.md")
        elif report.exists():
            status, note = "complete", ""
        elif data:
            status, note = "checks_only", "The checks have run; the review step has not written its report yet."
        else:
            continue

        actions, validation = None, None
        if data and (d / "actions.json").exists():
            try:
                actions = json.loads(read_text(d / "actions.json"))
                errs = validate(data, actions)
                validation = {"ok": not errs, "errors": errs[:5], "covered": len(actions.get("actions", []))}
                if errs:
                    actions = None  # never show classification that failed validation
            except json.JSONDecodeError as e:
                validation = {"ok": False, "errors": [f"actions.json is not valid JSON ({e})"], "covered": 0}

        drafts = []
        for f in sorted((d / "draft_emails").glob("*.md")):
            text = read_text(f)
            to = next((l[3:].strip() for l in text.splitlines() if l.startswith("To:")), "")
            subj = next((l[8:].strip() for l in text.splitlines() if l.startswith("Subject:")), f.stem)
            head, _, body = text.replace("\r\n", "\n").partition("\n\n")
            head_html = "".join(f"<div><strong>{html.escape(k)}:</strong>{html.escape(v)}</div>"
                                for k, _, v in (l.partition(":") for l in head.splitlines() if ":" in l))
            drafts.append({"file": f.name, "to": to, "subject": subj, "raw": text,
                           "html": f"<div class='hdr'>{head_html}</div>" + md_to_html(body)})
        logs = [{"file": f.name, "text": read_text(f)[-20000:]} for f in sorted((OUT / "logs").glob(f"{d.name}*.log"))]
        runs.append({
            "date": d.name, "status": status, "note_html": md_to_html(note) if note else "",
            "report_time": dt.datetime.fromtimestamp(report.stat().st_mtime).strftime("%d %b %Y %H:%M") if report.exists() else "",
            "summary": data["summary"] if data else None, "previous_run": data.get("previous_run") if data else None,
            "jobs_checked": data.get("jobs_checked") if data else None,
            "invoice_lines": data.get("invoice_lines_checked") if data else None,
            "exceptions": data["exceptions"] if data else [],
            "actions": actions, "validation": validation,
            "report_html": md_to_html(read_text(report)) if report.exists() else "",
            "drafts": drafts, "logs": logs,
        })
    log = []
    if (OUT / "run_log.csv").exists():
        with open(OUT / "run_log.csv", newline="", encoding="utf-8") as f:
            log = list(csv.DictReader(f))
    return runs, log


# ----------------------------------------------------------------------------
# Page
# ----------------------------------------------------------------------------
PAGE = r"""<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Solar Job Exceptions</title>
<style>
:root{--bg:#f3f6f7;--panel:#fff;--ink:#14212b;--muted:#566673;--line:#dce3e7;--soft:#eef2f4;--accent:#173042;--sun:#a35f00;--bar:#3f6e8c;
--high:#b3261e;--high-bg:#fbe9e7;--med:#8a5a00;--med-bg:#fdf1dc;--low:#3f5a70;--low-bg:#e6eef4;
--ok:#1c7a4b;--ok-bg:#e3f4ea;--warn:#8a5a00;--warn-bg:#fdf1dc;--err:#b3261e;--err-bg:#fbe9e7}
@media (prefers-color-scheme:dark){:root{--bg:#0f171d;--panel:#16212a;--ink:#e4ecf1;--muted:#97a8b5;--line:#2a3945;--soft:#1d2a34;--accent:#9cc7e6;--sun:#f0a630;--bar:#6fa3c7;
--high:#ff8f84;--high-bg:#3b1d1a;--med:#f2bf5e;--med-bg:#3a2b10;--low:#a8c0d4;--low-bg:#1d2b38;
--ok:#73d39f;--ok-bg:#15301f;--warn:#f2bf5e;--warn-bg:#3a2b10;--err:#ff8f84;--err-bg:#3b1d1a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14.5px/1.5 "Segoe UI",system-ui,-apple-system,Roboto,sans-serif}
header{background:var(--panel);border-bottom:1px solid var(--line);padding:12px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header h1{font-size:17px;margin:0;flex:1;min-width:220px}header .sub{color:var(--muted);font-size:12.5px;font-weight:400;display:block}
select,input{font:inherit;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:6px 8px}
main{max-width:1240px;margin:0 auto;padding:16px 20px 40px;display:grid;gap:16px}
.banner{border-radius:8px;padding:12px 16px;border:1px solid var(--line);display:flex;gap:12px;flex-wrap:wrap;align-items:baseline}
.banner.complete{background:var(--ok-bg);color:var(--ok)}.banner.incomplete,.banner.checks_only{background:var(--warn-bg);color:var(--warn)}
.banner.input_error{background:var(--err-bg);color:var(--err)}.banner .note{flex-basis:100%;color:var(--ink)}.banner .note h1{font-size:15px;margin:4px 0}.banner .note p{margin:4px 0}
.badge{font-size:12px;padding:2px 8px;border-radius:999px;background:var(--panel);border:1px solid var(--line);color:var(--muted)}
.badge.ok{color:var(--ok)}.badge.bad{color:var(--err)}
.kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 14px;min-width:0}
.kpi .v{font-size:24px;font-weight:650;line-height:1.2;font-variant-numeric:tabular-nums}.kpi .l{font-size:13px}.kpi .d{font-size:12px;color:var(--muted)}
.kpi.alert .v{color:var(--high)}
.grid2{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(0,1fr);gap:16px}
.grid4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px 16px;min-width:0}
.card h2{font-size:14px;margin:0 0 10px;letter-spacing:.02em}.card .hint{color:var(--muted);font-size:12px;margin:8px 0 0}
.pri{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.pri li{display:grid;grid-template-columns:28px minmax(0,1fr) auto;gap:10px;align-items:start;border-bottom:1px solid var(--line);padding-bottom:8px}
.pri li:last-child{border-bottom:0}.pri .n{font-weight:650;color:var(--muted);font-variant-numeric:tabular-nums}
.pri .who{font-size:12px;color:var(--muted)}.pri .due{font-size:12px;white-space:nowrap;text-align:right}
.pri .due.over{color:var(--high);font-weight:600}.pri .dec{color:var(--sun);font-weight:600;font-size:12px}
.bars{display:grid;gap:6px}.bar{display:grid;grid-template-columns:minmax(0,1fr) 44px;gap:8px;align-items:center;font-size:12.5px}
.bar .lab{display:flex;justify-content:space-between;gap:8px}.bar .lab span:last-child{color:var(--muted);white-space:nowrap}
.bar .track{grid-column:1/-1;height:8px;background:var(--soft);border-radius:4px;overflow:hidden}.bar .fill{height:100%;background:var(--bar);border-radius:4px}
.bar .val{text-align:right;font-variant-numeric:tabular-nums;font-weight:600}
nav.tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);overflow-x:auto}
nav.tabs button{font:inherit;background:none;border:0;border-bottom:2px solid transparent;padding:8px 12px;color:var(--muted);cursor:pointer;white-space:nowrap}
nav.tabs button.on{color:var(--ink);border-bottom-color:var(--accent);font-weight:600}
nav.tabs button:focus-visible,.drafts li button:focus-visible{outline:2px solid var(--accent)}
.tab{display:none}.tab.on{display:block}
.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}
th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted);font-weight:600;background:var(--panel);position:sticky;top:0}
td.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.sev{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;font-weight:600}
.sev.high{color:var(--high);background:var(--high-bg)}.sev.medium{color:var(--med);background:var(--med-bg)}.sev.low{color:var(--low);background:var(--low-bg)}
.tag{display:inline-block;padding:1px 6px;border-radius:4px;font-size:12px;background:var(--soft);color:var(--muted)}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 8px}
.md{max-width:1100px}.md h1{font-size:20px}.md h2{font-size:16px;margin-top:22px}.md h3{font-size:14.5px}
.md blockquote{margin:8px 0;padding:6px 12px;border-left:3px solid var(--line);color:var(--muted)}
code{background:var(--soft);padding:1px 4px;border-radius:4px;font-size:.92em}pre{background:var(--soft);padding:10px;border-radius:6px;overflow:auto;font-size:12.5px;white-space:pre-wrap}
.drafts{display:grid;grid-template-columns:270px minmax(0,1fr);gap:16px;margin-top:12px}.drafts ul{list-style:none;margin:0;padding:0;display:grid;gap:4px}
.drafts li button{width:100%;text-align:left;font:inherit;background:none;border:1px solid transparent;border-radius:6px;padding:8px;cursor:pointer;color:var(--ink)}
.drafts li button.on{border-color:var(--accent);background:var(--soft)}.drafts li small{color:var(--muted);display:block}
.notsent{display:inline-block;background:var(--warn-bg);color:var(--warn);font-weight:700;font-size:12px;padding:2px 8px;border-radius:4px}
.hdr{font-size:13px;border-bottom:1px solid var(--line);padding:8px 0;margin:8px 0}.hdr strong{display:inline-block;min-width:80px;color:var(--muted)}
button.act{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:6px;padding:5px 10px;cursor:pointer}
.muted{color:var(--muted)}svg text{fill:var(--muted);font-size:11px}
@media (max-width:1000px){.kpis{grid-template-columns:repeat(3,minmax(0,1fr))}.grid4{grid-template-columns:repeat(2,minmax(0,1fr))}.grid2{grid-template-columns:1fr}}
@media (max-width:620px){.kpis,.grid4{grid-template-columns:1fr 1fr}.drafts{grid-template-columns:1fr}main{padding:12px 16px}}
</style></head><body>
<header><h1>Solar Job Exceptions<span class="sub">Daily reconciliation of jobs, installations, supplier invoices and compliance documents · synthetic sample data</span></h1>
<label class="muted" for="run">Run</label><select id="run"></select></header>
<main>
<div id="banner" class="banner"></div>
<div class="kpis" id="kpis"></div>
<div class="grid2">
  <div class="card"><h2>Today's priorities</h2><ol class="pri" id="pri"></ol><p class="hint" id="prihint"></p></div>
  <div class="card"><h2>Open exceptions by run</h2><div id="trend"></div><p class="hint">Solid line: open exceptions. Dashed: high severity. Target: down to zero.</p></div>
</div>
<div class="grid4">
  <div class="card"><h2>Root causes (Pareto)</h2><div class="bars" id="a-cause"></div><p class="hint">Largest cause first; right-hand figure is the cumulative share.</p></div>
  <div class="card"><h2>Workload by owner</h2><div class="bars" id="a-owner"></div></div>
  <div class="card"><h2>Money at risk by supplier</h2><div class="bars" id="a-money"></div><p class="hint" id="a-money-hint"></p></div>
  <div class="card"><h2>Age of open exceptions</h2><div class="bars" id="a-age"></div><p class="hint" id="a-age-hint"></p></div>
</div>
<div class="card">
<nav class="tabs" id="tabs"></nav>
<section class="tab" id="t-reg"><div class="filters">
<input id="q" placeholder="Search job, supplier, invoice" style="flex:1;min-width:180px" aria-label="Search">
<select id="fo" aria-label="Owner"></select><select id="fc" aria-label="Cause"></select>
<select id="fs" aria-label="Severity"><option value="">All severities</option><option>high</option><option>medium</option><option>low</option></select>
<select id="fd" aria-label="Show"><option value="">All exceptions</option><option value="dec">Decisions needed</option><option value="over">Past response target</option><option value="new">New since last run</option></select></div>
<div class="muted" id="count" style="font-size:12.5px;margin-bottom:6px"></div><div class="tw"><table id="reg"></table></div></section>
<section class="tab md" id="t-report"></section>
<section class="tab" id="t-drafts"></section>
<section class="tab" id="t-hist"></section>
<section class="tab" id="t-logs"></section>
<section class="tab md" id="t-how">
<h2>How a run works</h2>
<ol><li><strong>06:30, Windows Task Scheduler</strong> wakes the PC and starts <code>scripts/run_daily.ps1</code>.</li>
<li><strong>Checks (Python).</strong> Every input file is validated, then 17 business checks run across flow, tracker against installation records, compliance and supplier invoices. The same data always gives the same result.</li>
<li><strong>Review (Claude, headless).</strong> Classifies every exception by cause and owner, sets priority, writes the report and drafts chase emails. It can read files and write to <code>output/</code> only, with no shell access.</li>
<li><strong>Validation (Python).</strong> The classification must cover every exception exactly once, using fixed cause and owner lists, or the run is retried and then marked failed.</li>
<li><strong>Dashboard.</strong> This page is rebuilt. A person decides the open questions and sends the drafts they approve.</li></ol>
<h3>Controls</h3><ul><li>Nothing is sent automatically. Every email is a draft.</li><li>Source data and rules are never changed.</li><li>Nothing is marked resolved. An exception closes when the data is fixed and the next run stops finding it.</li><li>A failed run never shows green: broken input turns the banner red, an incomplete run amber.</li></ul>
</section>
</div>
</main>
<script>
const RUNS = __RUNS__, LOG = __LOG__;
const $ = s => document.querySelector(s), esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const money = v => "£" + Number(v || 0).toLocaleString("en-GB", {minimumFractionDigits: 2, maximumFractionDigits: 2});
const fmtDate = s => s ? new Date(s + "T00:00:00").toLocaleDateString("en-GB", {day: "numeric", month: "short"}) : "";
const TABS = [["reg","Action register"],["report","Full report"],["drafts","Draft emails"],["hist","Run history"],["logs","Logs"],["how","How it works"]];
let cur = 0;
$("#run").innerHTML = RUNS.map((r, i) => `<option value="${i}">${r.date}${i === 0 ? " (latest)" : ""}</option>`).join("");
$("#run").onchange = e => { cur = +e.target.value; render(); };
$("#tabs").innerHTML = TABS.map(([k, l]) => `<button data-k="${k}">${l}</button>`).join("");
function tab(k){ document.querySelectorAll("#tabs button").forEach(b => b.classList.toggle("on", b.dataset.k === k));
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("on", t.id === "t-" + k)); try{localStorage.setItem("sjx-tab",k)}catch(e){} }
document.querySelectorAll("#tabs button").forEach(b => b.onclick = () => tab(b.dataset.k));
["q","fo","fc","fs","fd"].forEach(id => $("#" + id).oninput = drawRegister);

function rows(r){
  const act = {}; (r.actions?.actions || []).forEach(a => act[a.key] = a);
  return r.exceptions.map(e => ({...e, a: act[e.key] || null})).sort((x, y) => (x.a?.priority ?? 999) - (y.a?.priority ?? 999));
}
function bars(el, items, fmt = v => v, extra = () => ""){
  const max = Math.max(1, ...items.map(i => i[1]));
  $(el).innerHTML = items.length ? items.map(([l, v], i) => `<div class="bar"><div class="lab"><span>${esc(l)}</span><span>${extra(i)}</span></div><div class="val">${fmt(v)}</div><div class="track"><div class="fill" style="width:${(v / max * 100).toFixed(1)}%"></div></div></div>`).join("")
    : `<p class="muted" style="margin:0">Not available for this run.</p>`;
}
function render(){
  const r = RUNS[cur]; if (!r) { $("#banner").textContent = "No runs yet. Run scripts/run_daily.ps1."; return; }
  const s = r.summary, all = rows(r), dec = all.filter(x => x.a?.decision_needed || x.needs_human_review);
  const B = {complete:["complete", `Report ready: ${r.report_time}`], incomplete:["incomplete","Run failed or incomplete: read the note before relying on this page"],
    checks_only:["checks_only","Checks complete; review not written yet"], input_error:["input_error","Input error: the checks did not run"]}[r.status];
  const v = r.validation;
  const badge = v ? (v.ok ? `<span class="badge ok">Classification validated: ${v.covered} of ${r.exceptions.length} exceptions</span>` : `<span class="badge bad">Classification failed validation</span>`) : "";
  $("#banner").className = "banner " + B[0];
  $("#banner").innerHTML = `<strong>${esc(B[1])}</strong>${badge}` + (r.note_html ? `<div class="note">${r.note_html}</div>` : "");
  if (s) {
    const prev = LOG[LOG.findIndex(l => l.run_date === r.date) - 1];
    const delta = prev ? s.total - prev.total_open : null;
    const pct = s.invoice_value_checked_gbp ? (s.value_at_risk_gbp / s.invoice_value_checked_gbp * 100).toFixed(1) + "% of " + money(s.invoice_value_checked_gbp) + " checked" : "on supplier invoices";
    const k = [[s.total, "Open exceptions", delta === null ? "first run" : (delta > 0 ? "+" : "") + delta + " vs previous run", false],
      [s.by_severity.high || 0, "High severity", "compliance and money first", false],
      [dec.length, "Decisions needed", "answered by a person", dec.length > 0],
      [s.overdue ?? 0, "Past response target", "high 1, medium 3, low 5 working days", (s.overdue ?? 0) > 0],
      [money(s.value_at_risk_gbp), "Money at risk", pct, false],
      [`${s.new} / ${s.carried_over} / ${s.closed_since_last_run}`, "New / carried / closed", "since " + (r.previous_run || "first run"), false]];
    $("#kpis").innerHTML = k.map(([v, l, d, a]) => `<div class="kpi${a ? " alert" : ""}"><div class="v">${esc(v)}</div><div class="l">${esc(l)}</div><div class="d">${esc(d)}</div></div>`).join("");
  } else $("#kpis").innerHTML = "";

  // Today's priorities: strict priority order, decisions tagged
  const top = all.slice(0, 8).map(x => ({...x, isDec: dec.includes(x)}));
  $("#pri").innerHTML = top.map((x, i) => `<li><span class="n">${x.a?.priority ?? i + 1}</span><div>${x.isDec ? `<span class="dec">Decision · </span>` : ""}<strong>${esc(x.job_id)}</strong> ${esc(x.isDec ? (x.a?.decision || x.review_reason) : (x.a?.next_action || x.what_is_wrong))}<div class="who">${esc(x.a?.owner || "Owner to be assigned")}</div></div><span class="due${x.overdue ? " over" : ""}">${x.overdue ? "Overdue · " : "Due "}${fmtDate(x.due_by)}</span></li>`).join("") || `<li class="muted">No open exceptions.</li>`;
  $("#prihint").textContent = all.length > top.length ? `${all.length - top.length} more in the action register below.` : "";

  // Analytics
  const groups = (r.actions?.root_causes || []).map(g => [g.cause, g.keys.length]).sort((a, b) => b[1] - a[1]);
  const tot = groups.reduce((a, g) => a + g[1], 0); let cum = 0;
  const cumPct = groups.map(g => (cum += g[1], Math.round(cum / tot * 100) + "%"));
  bars("#a-cause", groups, v => v, i => cumPct[i]);
  const own = {}; all.forEach(x => { if (x.a) own[x.a.owner_group] = (own[x.a.owner_group] || 0) + 1; });
  bars("#a-owner", Object.entries(own).sort((a, b) => b[1] - a[1]));
  bars("#a-money", Object.entries(s?.value_at_risk_by_supplier || {}), money);
  $("#a-money-hint").textContent = s ? "Includes invoices held pending review." : "";
  bars("#a-age", Object.entries(s?.ageing || {}));
  $("#a-age-hint").textContent = s ? `${s.overdue ?? 0} past response target.` : "";

  // Register filters
  const owners = [...new Set(all.map(x => x.a?.owner_group).filter(Boolean))].sort(), causes = [...new Set(all.map(x => x.a?.cause).filter(Boolean))].sort();
  $("#fo").innerHTML = `<option value="">All owners</option>` + owners.map(o => `<option>${esc(o)}</option>`).join("");
  $("#fc").innerHTML = `<option value="">All causes</option>` + causes.map(o => `<option>${esc(o)}</option>`).join("");
  drawRegister(); drawTrend();
  $("#t-report").innerHTML = r.report_html || `<p class="muted">No report for this run. The facts are in the action register.</p>`;
  drawDrafts(r); drawHist(); drawLogs(r);
}
function drawRegister(){
  const r = RUNS[cur], q = $("#q").value.toLowerCase(), o = $("#fo").value, c = $("#fc").value, sv = $("#fs").value, f = $("#fd").value;
  const list = rows(r).filter(x => (!o || x.a?.owner_group === o) && (!c || x.a?.cause === c) && (!sv || x.severity === sv)
    && (!f || (f === "dec" && (x.a?.decision_needed || x.needs_human_review)) || (f === "over" && x.overdue) || (f === "new" && x.status === "new"))
    && (!q || JSON.stringify(x).toLowerCase().includes(q)));
  $("#count").textContent = `${list.length} of ${r.exceptions.length} exceptions, in priority order`;
  $("#reg").innerHTML = `<thead><tr><th>#</th><th>Job</th><th>Issue</th><th>Evidence</th><th>Sev.</th><th>Cause</th><th>Owner</th><th>Next action</th><th>Due</th><th>Open</th></tr></thead><tbody>` +
    list.map(x => `<tr><td class="num">${x.a?.priority ?? ""}</td><td><strong>${esc(x.job_id)}</strong></td><td><span class="tag">${esc(x.check)}</span> ${esc(x.what_is_wrong)}</td>
    <td>${esc(x.expected)}<br><span class="muted">${esc(x.found)}</span></td><td><span class="sev ${x.severity}">${x.severity}</span></td><td>${esc(x.a?.cause || "")}</td>
    <td>${esc(x.a?.owner || "")}</td><td>${(x.a?.decision_needed || x.needs_human_review) ? `<strong>Decision:</strong> ${esc(x.a?.decision || x.review_reason)}` : esc(x.a?.next_action || "")}</td>
    <td class="num"${x.overdue ? ' style="color:var(--high);font-weight:600"' : ""}>${fmtDate(x.due_by)}${x.overdue ? " overdue" : ""}</td><td class="num">${x.days_open ?? ""} d</td></tr>`).join("") + "</tbody>";
}
function drawDrafts(r){
  if (!r.drafts.length) { $("#t-drafts").innerHTML = `<p class="muted">No draft emails for this run.</p>`; return; }
  $("#t-drafts").innerHTML = `<p class="muted" style="margin:12px 0 0">Drafts only. Nothing has been sent. Check a draft, then copy it into your email client.</p>
  <div class="drafts"><ul>${r.drafts.map((d, i) => `<li><button data-i="${i}">${esc(d.to || d.file)}<small>${esc(d.subject)}</small></button></li>`).join("")}</ul><div class="md" id="dview"></div></div>`;
  const show = i => { const d = r.drafts[i]; document.querySelectorAll(".drafts li button").forEach(b => b.classList.toggle("on", +b.dataset.i === i));
    $("#dview").innerHTML = `<span class="notsent">DRAFT · NOT SENT</span> <button class="act" id="cp">Copy text</button> <span class="muted" style="font-size:12px">${esc(d.file)}</span>` + d.html;
    $("#cp").onclick = () => navigator.clipboard.writeText(d.raw).then(() => $("#cp").textContent = "Copied", () => $("#cp").textContent = "Copy failed: select the text instead"); };
  document.querySelectorAll(".drafts li button").forEach(b => b.onclick = () => show(+b.dataset.i)); show(0);
}
function drawHist(){
  const cols = ["run_date","total_open","high","medium","low","needs_review","overdue","new","carried_over","closed_since_last_run","value_at_risk_gbp"];
  const names = {run_date:"Date",total_open:"Open",high:"High",medium:"Medium",low:"Low",needs_review:"Review",overdue:"Overdue",new:"New",carried_over:"Carried",closed_since_last_run:"Closed",value_at_risk_gbp:"£ at risk"};
  $("#t-hist").innerHTML = `<div class="tw" style="margin-top:12px"><table><thead><tr>${cols.map(c => `<th>${names[c]}</th>`).join("")}</tr></thead><tbody>` +
    [...LOG].reverse().map(l => `<tr>${cols.map(c => `<td class="num">${c === "value_at_risk_gbp" ? money(l[c]) : esc(l[c] ?? "")}</td>`).join("")}</tr>`).join("") +
    `</tbody></table></div><p class="muted" style="font-size:12.5px">Source: output/run_log.csv. A run stopped by bad input is not logged, so it can never look like a clean day.</p>`;
}
function drawLogs(r){
  $("#t-logs").innerHTML = r.logs.length ? r.logs.map(l => `<h3 style="font-size:13px;margin:14px 0 4px">${esc(l.file)}</h3><pre>${esc(l.text) || "(empty)"}</pre>`).join("")
    : `<p class="muted">No log files for this run. Logs are written by the scheduled runner.</p>`;
}
function drawTrend(){
  const pts = LOG.map(l => ({d: l.run_date, v: +l.total_open, h: +l.high}));
  if (!pts.length) { $("#trend").innerHTML = `<p class="muted">No runs logged yet.</p>`; return; }
  const W = 560, H = 180, L = 34, R = 16, T = 18, Bm = 30, P = 28, max = Math.max(5, ...pts.map(p => p.v)), top = Math.ceil(max / 5) * 5;
  const x = i => pts.length === 1 ? (L + W - R) / 2 : L + P + i * (W - L - R - 2 * P) / (pts.length - 1), y = v => T + (1 - v / top) * (H - T - Bm);
  const line = k => pts.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p[k]).toFixed(1)}`).join(" ");
  $("#trend").innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Open exceptions per run">
   ${[0, top / 2, top].map(t => `<line x1="${L}" x2="${W-R}" y1="${y(t)}" y2="${y(t)}" stroke="var(--line)"/><text x="${L-6}" y="${y(t)+4}" text-anchor="end">${t}</text>`).join("")}
   <path d="${line("v")}" fill="none" stroke="var(--accent)" stroke-width="2.5"/><path d="${line("h")}" fill="none" stroke="var(--high)" stroke-width="1.5" stroke-dasharray="4 3"/>
   ${pts.map((p, i) => `<circle cx="${x(i)}" cy="${y(p.v)}" r="${i === pts.length - 1 ? 4.5 : 3}" fill="var(--accent)"><title>${p.d}: ${p.v} open, ${p.h} high</title></circle>
   <text x="${x(i)}" y="${y(p.v) - 8}" text-anchor="middle">${p.v}</text><text x="${x(i)}" y="${H - 8}" text-anchor="middle">${fmtDate(p.d)}</text>`).join("")}</svg>`;
}
let start = "reg"; try { start = localStorage.getItem("sjx-tab") || "reg" } catch (e) {}
render(); tab(TABS.some(t => t[0] === start) ? start : "reg");
</script></body></html>
"""


def main():
    runs, log = collect()
    payload = PAGE.replace("__RUNS__", json.dumps(runs).replace("</", "<\\/")).replace("__LOG__", json.dumps(log).replace("</", "<\\/"))
    OUT.mkdir(exist_ok=True)
    (OUT / "dashboard.html").write_text(payload, encoding="utf-8")
    latest = f"{runs[0]['date']} ({runs[0]['status']})" if runs else "none"
    print(f"Dashboard written: {OUT / 'dashboard.html'} - {len(runs)} run(s), latest {latest}")


if __name__ == "__main__":
    main()
