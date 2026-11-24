"""Build output/dashboard.html - the page people actually look at.

One self-contained HTML file (no server, no internet, no Claude needed to view it)
showing every run in output/: status, headline numbers, trend, Claude's report,
the full exceptions table with filters, the draft emails, run history and logs.

Run automatically at the end of scripts/run_daily.ps1, or by hand:
    python scripts/build_dashboard.py
"""
from __future__ import annotations

import csv
import datetime as dt
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"


# ----------------------------------------------------------------------------
# Minimal Markdown -> HTML (headings, tables, lists, quotes, code, bold/italic)
# ----------------------------------------------------------------------------
def _inline(t: str) -> str:
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)([^*\n]+?)\*(?![\w*])", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', t)
    t = t.replace("[ ]", "&#9744;").replace("[x]", "&#9745;")
    return t


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
            stack, html_parts = [], []
            while i < len(lines) and (LIST_RE.match(lines[i]) or (lines[i].startswith("   ") and lines[i].strip() and stack)):
                m = LIST_RE.match(lines[i])
                if not m:  # continuation of previous item
                    html_parts[-1] = html_parts[-1][:-5] + " " + _inline(lines[i].strip()) + "</li>"
                    i += 1; continue
                level = min(len(m.group(1).replace("\t", "  ")) // 2, 3)
                tag = "ol" if m.group(2)[0].isdigit() else "ul"
                while len(stack) > level + 1 or (stack and len(stack) == level + 1 and stack[-1] != tag):
                    html_parts.append(f"</{stack.pop()}>")
                while len(stack) < level + 1:
                    stack.append(tag); html_parts.append(f"<{tag}>")
                html_parts.append(f"<li>{_inline(m.group(3))}</li>")
                i += 1
            while stack:
                html_parts.append(f"</{stack.pop()}>")
            out.append("".join(html_parts))
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
            status, note = "checks_only", "The deterministic checks ran, but Claude's report has not been written yet."
        else:
            continue
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
        logs = []
        for f in sorted((OUT / "logs").glob(f"{d.name}*.log")):
            logs.append({"file": f.name, "text": read_text(f)[-20000:]})
        runs.append({
            "date": d.name, "status": status, "note_html": md_to_html(note) if note else "",
            "generated_at": data["generated_at"] if data else "",
            "report_time": dt.datetime.fromtimestamp(report.stat().st_mtime).isoformat(timespec="minutes") if report.exists() else "",
            "summary": data["summary"] if data else None, "previous_run": data.get("previous_run") if data else None,
            "closed": data.get("closed_since_last_run", []) if data else [],
            "jobs_checked": data.get("jobs_checked") if data else None,
            "exceptions": data["exceptions"] if data else [],
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
:root{--bg:#f6f7f9;--panel:#fff;--ink:#1c2430;--muted:#5d6878;--line:#e2e6ec;--accent:#0b6bcb;
--high:#c0392b;--high-bg:#fdecea;--med:#a76200;--med-bg:#fff4e0;--low:#4a6179;--low-bg:#eaf0f6;
--ok:#1e7f4f;--ok-bg:#e6f5ec;--warn:#9a5b00;--warn-bg:#fff4e0;--err:#b3261e;--err-bg:#fdecea;--code:#eef1f5}
@media (prefers-color-scheme:dark){:root{--bg:#12161c;--panel:#1b2129;--ink:#e6ebf1;--muted:#9aa6b4;--line:#2c3440;
--accent:#5aa9ff;--high:#ff8a80;--high-bg:#3a1f1d;--med:#ffc061;--med-bg:#3a2c12;--low:#a9bdd1;--low-bg:#1f2a36;
--ok:#6fd39c;--ok-bg:#16301f;--warn:#ffc061;--warn-bg:#3a2c12;--err:#ff8a80;--err-bg:#3a1f1d;--code:#242c36}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{background:var(--panel);border-bottom:1px solid var(--line);padding:14px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header h1{font-size:18px;margin:0;flex:1;min-width:200px}header .sub{color:var(--muted);font-size:13px;font-weight:400;display:block}
select,input{font:inherit;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:6px 8px}
main{max-width:1200px;margin:0 auto;padding:16px 20px 40px}
.banner{border-radius:8px;padding:12px 16px;margin-bottom:16px;border:1px solid var(--line)}
.banner.complete{background:var(--ok-bg);color:var(--ok)}.banner.incomplete,.banner.checks_only{background:var(--warn-bg);color:var(--warn)}
.banner.input_error{background:var(--err-bg);color:var(--err)}.banner p,.banner h1{margin:4px 0}.banner h1{font-size:15px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:16px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 14px}
.kpi .v{font-size:26px;font-weight:650;line-height:1.2}.kpi .l{color:var(--muted);font-size:13px}.kpi .d{font-size:12px;color:var(--muted)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px;margin-bottom:16px}
.card h2{font-size:15px;margin:0 0 8px}
nav.tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);margin-bottom:16px;overflow-x:auto}
nav.tabs button{font:inherit;background:none;border:0;border-bottom:2px solid transparent;padding:8px 12px;color:var(--muted);cursor:pointer;white-space:nowrap}
nav.tabs button.on{color:var(--ink);border-bottom-color:var(--accent);font-weight:600}
.tab{display:none}.tab.on{display:block}
.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted);font-weight:600;background:var(--panel);position:sticky;top:0}
.sev{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;font-weight:600}
.sev.high{color:var(--high);background:var(--high-bg)}.sev.medium{color:var(--med);background:var(--med-bg)}.sev.low{color:var(--low);background:var(--low-bg)}
.tag{display:inline-block;padding:1px 6px;border-radius:4px;font-size:12px;background:var(--code);color:var(--muted)}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.md h1{font-size:20px}.md h2{font-size:17px;margin-top:22px}.md h3{font-size:15px}
.md blockquote{margin:8px 0;padding:6px 12px;border-left:3px solid var(--line);color:var(--muted)}
code{background:var(--code);padding:1px 4px;border-radius:4px;font-size:.92em}pre{background:var(--code);padding:10px;border-radius:6px;overflow:auto;font-size:12.5px;white-space:pre-wrap}
.drafts{display:grid;grid-template-columns:260px 1fr;gap:16px}.drafts ul{list-style:none;margin:0;padding:0}
.drafts li button{width:100%;text-align:left;font:inherit;background:none;border:1px solid transparent;border-radius:6px;padding:8px;cursor:pointer;color:var(--ink)}
.drafts li button.on{border-color:var(--accent);background:var(--code)}.drafts li small{color:var(--muted);display:block}
.notsent{display:inline-block;background:var(--warn-bg);color:var(--warn);font-weight:700;font-size:12px;padding:2px 8px;border-radius:4px;margin-bottom:8px}
button.act{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:6px;padding:5px 10px;cursor:pointer}
.hdr{font-size:13.5px;border-bottom:1px solid var(--line);padding:8px 0;margin:8px 0}.hdr strong{display:inline-block;min-width:80px;color:var(--muted)}
.muted{color:var(--muted)}svg text{fill:var(--muted);font-size:11px}
@media (max-width:760px){.drafts{grid-template-columns:1fr}main{padding:12px 16px}}
</style></head><body>
<header><h1>Solar Job Exceptions<span class="sub">Daily reconciliation of jobs, installs, invoices and compliance documents. Synthetic sample data.</span></h1>
<label class="muted">Run <select id="run"></select></label></header>
<main>
<div id="banner" class="banner"></div>
<div class="kpis" id="kpis"></div>
<div class="card"><h2>Open exceptions over time</h2><div id="trend"></div><div class="muted" style="font-size:12px">Target: trending towards zero. Each point is one daily run (from output/run_log.csv).</div></div>
<nav class="tabs" id="tabs"></nav>
<section class="tab md" id="t-report"></section>
<section class="tab" id="t-exc"><div class="filters">
<input id="q" placeholder="Search job, supplier, invoice..." style="flex:1;min-width:180px">
<select id="fg"><option value="">All groups</option></select><select id="fs"><option value="">All severities</option><option>high</option><option>medium</option><option>low</option></select>
<select id="fst"><option value="">New + carried over</option><option value="new">New only</option><option value="carried_over">Carried over only</option></select>
<select id="fr"><option value="">Any</option><option value="1">Needs human review</option></select></div>
<div class="muted" id="count" style="font-size:13px;margin-bottom:6px"></div><div class="tw"><table id="exc"></table></div></section>
<section class="tab" id="t-drafts"></section>
<section class="tab" id="t-hist"></section>
<section class="tab" id="t-logs"></section>
<section class="tab md" id="t-how">
<h2>How this works</h2>
<ol><li><strong>06:30 - Windows Task Scheduler</strong> wakes the PC and starts <code>scripts/run_daily.ps1</code>.</li>
<li><strong>Deterministic checks (Python)</strong> validate every input file (data-quality check X1), then run 17 business checks across flow, tracker vs install, compliance and supplier invoices. Same data in, same answer out.</li>
<li><strong>Claude (headless)</strong> reads the evidence, groups exceptions by root cause, names an owner, sets priority, writes the report and drafts chase emails. Its permissions only allow reading files and writing to <code>output/</code>, with no shell access: the runner runs the checks itself.</li>
<li><strong>This dashboard</strong> is rebuilt. A person reviews it, decides the <em>Needs human review</em> items and sends the drafts they approve.</li></ol>
<h3>What it never does</h3><ul><li>Send an email or message</li><li>Edit the source data or the rules</li><li>Mark anything resolved: an exception closes only when the data is fixed and the next run stops finding it</li></ul>
<h3>When something goes wrong</h3><ul><li><strong>Broken input</strong> (missing file/column, bad rules): run stops, says why, run log untouched.</li>
<li><strong>Bad rows</strong> (invalid date, duplicate ID): reported as data-quality exceptions and quarantined so they can't cause false alarms.</li>
<li><strong>Claude step fails or stalls</strong>: each attempt is stopped after 15 minutes and retried up to 3 times; if all fail, the facts are still here and the banner says so.</li></ul>
</section>
</main>
<script>
const RUNS = __RUNS__, LOG = __LOG__;
const $ = s => document.querySelector(s), esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const money = v => "£" + Number(v || 0).toLocaleString("en-GB", {minimumFractionDigits: 2, maximumFractionDigits: 2});
const TABS = [["report","Report"],["exc","All exceptions"],["drafts","Draft emails"],["hist","Run history"],["logs","Logs"],["how","How it works"]];
let cur = 0;
$("#run").innerHTML = RUNS.map((r, i) => `<option value="${i}">${r.date}${i === 0 ? " (latest)" : ""}</option>`).join("");
$("#run").onchange = e => { cur = +e.target.value; render(); };
$("#tabs").innerHTML = TABS.map(([k, l]) => `<button data-k="${k}">${l}</button>`).join("");
function tab(k){ document.querySelectorAll("#tabs button").forEach(b => b.classList.toggle("on", b.dataset.k === k));
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("on", t.id === "t-" + k)); try{localStorage.setItem("tab",k)}catch(e){} }
document.querySelectorAll("#tabs button").forEach(b => b.onclick = () => tab(b.dataset.k));
let start = "report"; try{ start = localStorage.getItem("tab") || "report" }catch(e){}
["q","fg","fs","fst","fr"].forEach(id => $("#" + id).oninput = drawTable);

function render(){
  const r = RUNS[cur]; if (!r) { $("#banner").textContent = "No runs yet - run scripts/run_daily.ps1"; return; }
  const B = {complete:["complete", `Report ready - written ${r.report_time.replace("T"," ")}. Review the Needs human review items, then approve and send the drafts you agree with.`],
    incomplete:["incomplete","Run failed or incomplete - read the note below before using anything on this page"], checks_only:["checks_only","Checks complete - Claude's report not written yet"],
    input_error:["input_error","Input error - the checks did not run"]}[r.status];
  $("#banner").className = "banner " + B[0];
  $("#banner").innerHTML = `<strong>${esc(B[1])}</strong>` + (r.note_html ? `<div>${r.note_html}</div>` : "");
  const s = r.summary;
  if (s) {
    const prev = LOG[LOG.findIndex(l => l.run_date === r.date) - 1];
    const delta = prev ? s.total - prev.total_open : null;
    const k = [[s.total,"Open exceptions", delta === null ? "first run" : (delta > 0 ? "+" : "") + delta + " vs previous run"],
      [s.by_severity.high || 0,"High severity","compliance and money first"],[s.needs_review,"Needs human review","decided by a person"],
      [money(s.value_at_risk_gbp),"Money at risk","on supplier invoices"],
      [`${s.new} / ${s.carried_over} / ${s.closed_since_last_run}`,"New / carried / closed","vs " + (r.previous_run || "no previous run")]];
    $("#kpis").innerHTML = k.map(([v,l,d]) => `<div class="kpi"><div class="v">${esc(v)}</div><div class="l">${esc(l)}</div><div class="d">${esc(d)}</div></div>`).join("");
  } else $("#kpis").innerHTML = "";
  $("#t-report").innerHTML = r.report_html || `<p class="muted">No report for this run. ${r.summary ? "The facts are in the All exceptions tab." : ""}</p>`;
  const groups = [...new Set(r.exceptions.map(e => e.group))].sort();
  $("#fg").innerHTML = `<option value="">All groups</option>` + groups.map(g => `<option>${esc(g)}</option>`).join("");
  drawTable(); drawDrafts(r); drawHist(); drawLogs(r); drawTrend();
}
function drawTable(){
  const r = RUNS[cur], q = $("#q").value.toLowerCase(), g = $("#fg").value, sv = $("#fs").value, st = $("#fst").value, rv = $("#fr").value;
  const rows = r.exceptions.filter(e => (!g || e.group === g) && (!sv || e.severity === sv) && (!st || e.status === st) && (!rv || e.needs_human_review)
    && (!q || JSON.stringify(e).toLowerCase().includes(q)));
  $("#count").textContent = `${rows.length} of ${r.exceptions.length} exceptions`;
  $("#exc").innerHTML = `<thead><tr><th>Job</th><th>Check</th><th>What is wrong</th><th>Expected</th><th>Found</th><th>Severity</th><th>Status</th><th>First seen</th><th>Review</th></tr></thead><tbody>` +
    rows.map(e => `<tr><td><strong>${esc(e.job_id)}</strong></td><td><span class="tag">${esc(e.check)}</span> ${esc(e.check_name)}</td><td>${esc(e.what_is_wrong)}</td>
    <td>${esc(e.expected)}</td><td>${esc(e.found)}</td><td><span class="sev ${e.severity}">${e.severity}</span></td><td>${e.status === "new" ? "New" : "Carried over"}</td>
    <td>${esc(e.first_seen)}</td><td title="${esc(e.review_reason)}">${e.needs_human_review ? "Yes" : ""}</td></tr>`).join("") + "</tbody>";
}
function drawDrafts(r){
  if (!r.drafts.length) { $("#t-drafts").innerHTML = `<p class="muted">No draft emails for this run.</p>`; return; }
  $("#t-drafts").innerHTML = `<p class="muted">Drafts only. Nothing has been sent. Copy a draft into your email client once you've checked it.</p>
  <div class="drafts"><ul>${r.drafts.map((d, i) => `<li><button data-i="${i}">${esc(d.to || d.file)}<small>${esc(d.subject)}</small></button></li>`).join("")}</ul><div class="card md" id="dview"></div></div>`;
  const show = i => { const d = r.drafts[i]; document.querySelectorAll(".drafts li button").forEach(b => b.classList.toggle("on", +b.dataset.i === i));
    $("#dview").innerHTML = `<span class="notsent">DRAFT - NOT SENT</span> <button class="act" id="cp">Copy text</button> <span class="muted" style="font-size:12px">${esc(d.file)}</span>` + d.html;
    $("#cp").onclick = () => navigator.clipboard.writeText(d.raw).then(() => $("#cp").textContent = "Copied"); };
  document.querySelectorAll(".drafts li button").forEach(b => b.onclick = () => show(+b.dataset.i)); show(0);
}
function drawHist(){
  const cols = ["run_date","total_open","high","medium","low","needs_review","new","carried_over","closed_since_last_run","value_at_risk_gbp"];
  const names = {run_date:"Date",total_open:"Open",high:"High",medium:"Medium",low:"Low",needs_review:"Review",new:"New",carried_over:"Carried",closed_since_last_run:"Closed",value_at_risk_gbp:"£ at risk"};
  $("#t-hist").innerHTML = `<div class="tw"><table><thead><tr>${cols.map(c => `<th>${names[c]}</th>`).join("")}</tr></thead><tbody>` +
    [...LOG].reverse().map(l => `<tr>${cols.map(c => `<td>${c === "value_at_risk_gbp" ? money(l[c]) : esc(l[c])}</td>`).join("")}</tr>`).join("") +
    `</tbody></table></div><p class="muted" style="font-size:13px">Source: output/run_log.csv. A run that fails on bad input is not logged, so it can never look like a clean day.</p>`;
}
function drawLogs(r){
  $("#t-logs").innerHTML = r.logs.length ? r.logs.map(l => `<div class="card"><h2>${esc(l.file)}</h2><pre>${esc(l.text) || "(empty)"}</pre></div>`).join("")
    : `<p class="muted">No log files for this run (logs are written by the scheduled runner, scripts/run_daily.ps1).</p>`;
}
function drawTrend(){
  const pts = LOG.map(l => ({d: l.run_date, v: +l.total_open, h: +l.high}));
  if (!pts.length) { $("#trend").innerHTML = `<p class="muted">No runs logged yet.</p>`; return; }
  const W = 900, H = 160, P = 30, max = Math.max(...pts.map(p => p.v), 1);
  const x = i => pts.length === 1 ? W / 2 : P + i * (W - 2 * P) / (pts.length - 1), y = v => H - P - v * (H - 2 * P) / max;
  const line = k => pts.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p[k])}`).join(" ");
  $("#trend").innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Open exceptions per run">
   <line x1="${P}" x2="${W-P}" y1="${H-P}" y2="${H-P}" stroke="var(--line)"/>
   <path d="${line("v")}" fill="none" stroke="var(--accent)" stroke-width="2.5"/><path d="${line("h")}" fill="none" stroke="var(--high)" stroke-width="1.5" stroke-dasharray="4 3"/>
   ${pts.map((p, i) => `<circle cx="${x(i)}" cy="${y(p.v)}" r="4" fill="var(--accent)"><title>${p.d}: ${p.v} open, ${p.h} high</title></circle>
   <text x="${x(i)}" y="${y(p.v) - 9}" text-anchor="middle">${p.v}</text><text x="${x(i)}" y="${H - 10}" text-anchor="middle">${p.d}</text>`).join("")}
   <text x="${W-P}" y="14" text-anchor="end">— open   - - high</text></svg>`;
}
render(); tab(TABS.some(t => t[0] === start) ? start : "report");
</script></body></html>
"""


def main():
    runs, log = collect()
    payload = PAGE.replace("__RUNS__", json.dumps(runs).replace("</", "<\\/")).replace("__LOG__", json.dumps(log).replace("</", "<\\/"))
    OUT.mkdir(exist_ok=True)
    (OUT / "dashboard.html").write_text(payload, encoding="utf-8")
    latest = runs[0]["date"] + " (" + runs[0]["status"] + ")" if runs else "none"
    print(f"Dashboard written: {OUT / 'dashboard.html'} - {len(runs)} run(s), latest {latest}")


if __name__ == "__main__":
    main()
