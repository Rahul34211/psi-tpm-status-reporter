#!/usr/bin/env python3
"""PSI TPM weekly status generator.

Reads the Task 5 tracker (Excel with two tabs, or two CSV files) and writes:
  * one client-facing Markdown report per client (client-visible items only, plain language)
  * one internal digest for the Group CTO (all items, ranked, overdue flags, owner load)

Rules the tool follows (on purpose):
  1. RAG status is read from the Summary tab. It is never calculated or guessed.
  2. Items marked Visibility = Internal never appear in a client report, and the internal
     "Action" column is never printed in a client report.
  3. A client-visible item without a plain-language "Client Summary" is NOT sent to the client
     (the internal wording could leak). It is listed as a warning instead.
  4. Missing or invalid data is reported as a warning. Bad RAG values stop the run.

Usage:
  python generate_status.py --input sample_tracker.xlsx --out reports --as-of 2026-11-09
  python generate_status.py --summary-csv s.csv --risks-csv r.csv --out reports
"""
import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

PROB = {"low": 1, "medium": 2, "high": 3}
IMPACT = {"low": 1, "medium": 2, "high": 3, "critical": 4}
RAG = {"red": "🔴 RED", "amber": "🟠 AMBER", "green": "🟢 GREEN"}
SUMMARY_REQUIRED = ["project", "client", "status", "next milestone", "milestone date"]
RISK_REQUIRED = ["project", "id", "description", "probability", "impact", "owner", "action / mitigation", "due date", "status"]


class TrackerError(Exception):
    pass


# ---------- loading ----------
def norm(h):
    """Normalise a header: 'Description (internal)' -> 'description'."""
    return re.sub(r"\s*\(.*?\)", "", str(h or "")).strip().lower()


def to_date(v):
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%d-%b-%Y", "%a %d %b %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None  # free text such as "Thursday (conditional)" is kept as text by the caller


def rows_to_dicts(rows, required, label):
    """Find the header row (first row containing all required columns), return list of dicts."""
    for idx, row in enumerate(rows):
        headers = [norm(c) for c in row]
        if all(r in headers for r in required):
            out = []
            for r in rows[idx + 1:]:
                if not any(c not in (None, "") for c in r):
                    continue
                out.append({h: r[i] if i < len(r) else None for i, h in enumerate(headers) if h})
            return out
    raise TrackerError(f"{label}: could not find a header row with columns {required}")


def load_xlsx(path):
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise TrackerError("openpyxl is required for .xlsx files: pip install openpyxl")
    wb = load_workbook(path, data_only=True)
    names = {n.lower(): n for n in wb.sheetnames}
    for need in ("summary", "risks and issues"):
        if need not in names:
            raise TrackerError(f"Tab '{need}' not found. Tabs present: {wb.sheetnames}")
    grab = lambda n: [list(r) for r in wb[names[n]].iter_rows(values_only=True)]
    return (rows_to_dicts(grab("summary"), SUMMARY_REQUIRED, "Summary tab"),
            rows_to_dicts(grab("risks and issues"), RISK_REQUIRED, "Risks and Issues tab"))


def load_csv(summary_path, risks_path):
    read = lambda p: list(csv.reader(open(p, newline="", encoding="utf-8-sig")))
    return (rows_to_dicts(read(summary_path), SUMMARY_REQUIRED, "Summary CSV"),
            rows_to_dicts(read(risks_path), RISK_REQUIRED, "Risks CSV"))


# ---------- model ----------
def prepare(summary_rows, risk_rows, as_of):
    warnings, projects = [], {}
    for r in summary_rows:
        name = str(r["project"]).strip()
        status = str(r["status"] or "").strip().lower()
        if status not in RAG:
            raise TrackerError(f"Project '{name}': Status '{r['status']}' must be Red, Amber or Green. "
                               "The tool does not guess a status.")
        md = to_date(r["milestone date"])
        projects[name] = {
            "name": name, "client": str(r["client"]).strip(), "contact": str(r.get("client contact") or "").strip(),
            "status": status, "milestone": r["next milestone"], "m_date": md,
            "m_text": None if md else r["milestone date"], "date_note": r.get("date note") or "",
            "problem": r.get("main problem") or "", "client_summary": r.get("client summary") or "", "items": []}
        if not projects[name]["client_summary"]:
            warnings.append(f"{name}: Summary has no 'Client Summary' text; the client report will say so.")
    for r in risk_rows:
        proj = str(r["project"]).strip()
        rid = str(r["id"] or "?").strip()
        if proj not in projects:
            warnings.append(f"{rid}: project '{proj}' is not in the Summary tab; item skipped.")
            continue
        p, i = str(r["probability"] or "").strip().lower(), str(r["impact"] or "").strip().lower()
        if p not in PROB or i not in IMPACT:
            warnings.append(f"{rid}: probability '{r['probability']}' / impact '{r['impact']}' not recognised; score set to 0.")
        due = to_date(r["due date"])
        item = {
            "project": proj, "id": rid, "type": str(r.get("type") or "").strip(), "desc": r["description"] or "",
            "client_text": str(r.get("client summary") or "").strip(),
            "prob": str(r["probability"] or "").strip(), "impact": str(r["impact"] or "").strip(),
            # Score is computed here. The Excel formula cell has no cached value when the file was written by a script.
            "score": PROB.get(p, 0) * IMPACT.get(i, 0),
            "owner": str(r["owner"] or "").strip(), "action": r["action / mitigation"] or "",
            "due": due, "due_text": None if due else r["due date"],
            "status": str(r["status"] or "Open").strip(),
            "visibility": str(r.get("visibility") or "Internal").strip().capitalize()}
        item["closed"] = item["status"].lower() == "closed"
        item["overdue"] = bool(due and not item["closed"] and due < as_of)
        for field, label in (("owner", "owner"), ("action", "action")):
            if not item[field]:
                warnings.append(f"{rid}: no {label}.")
        if not due:
            warnings.append(f"{rid}: due date missing or not a date ('{r['due date']}').")
        if item["visibility"] not in ("Client", "Internal"):
            warnings.append(f"{rid}: Visibility '{item['visibility']}' not Client/Internal; treated as Internal.")
            item["visibility"] = "Internal"
        projects[proj]["items"].append(item)
    for p in projects.values():
        p["items"].sort(key=lambda x: (x["closed"], -x["score"], x["due"] or date.max))
    return projects, warnings


# ---------- rendering ----------
def fmt(d, text=None):
    return d.strftime("%a %d %b %Y") if d else (str(text) if text else "not set")


def cell(s):
    return str(s).replace("|", "/").replace("\n", " ").strip()


def client_report(p, as_of, prepared_by):
    shown = [i for i in p["items"] if i["visibility"] == "Client" and not i["closed"]]
    sendable = [i for i in shown if i["client_text"]]
    held_back = [i for i in shown if not i["client_text"]]
    closed = [i for i in p["items"] if i["visibility"] == "Client" and i["closed"] and i["client_text"]]
    lines = [f"# Weekly Status Report: {p['client']}",
             f"**Project:** {p['name']}  |  **Week of:** {fmt(as_of - timedelta(days=as_of.weekday()))}  |  "
             f"**Prepared by:** {prepared_by}", "",
             f"**Overall status: {RAG[p['status']]}**", "",
             f"**Next milestone:** {p['milestone']}: {fmt(p['m_date'], p['m_text'])}"]
    if p["date_note"]:
        lines.append(f"  \n*{p['date_note']}*")
    lines += ["", "## Summary", p["client_summary"] or "_No client summary was provided in the tracker._", ""]
    if sendable:
        lines += ["## What we are working on", "", "| Ref | What is happening and what we are doing | Who | Date |", "|---|---|---|---|"]
        for i in sendable:
            flag = " ⚠ overdue" if i["overdue"] else ""
            # Internal 'Action' text is never shown to clients; it can name people on leave, designs, other clients.
            lines.append(f"| {i['id']} | {cell(i['client_text'])} | {cell(i['owner'])} | {fmt(i['due'], i['due_text'])}{flag} |")
        lines.append("")
        lines += ["## Next dates"]
        for i in sorted(sendable, key=lambda x: x["due"] or date.max):
            lines.append(f"- {fmt(i['due'], i['due_text'])}: {i['id']} ({cell(i['owner'])})")
        lines.append("")
    if closed:
        lines += ["## Completed", *[f"- {i['id']}: {cell(i['client_text'])}" for i in closed], ""]
    lines += ["---", f"_Questions? Reply to this email or contact the PSI Technical Program Manager. Next report: Friday 17:00._"]
    return "\n".join(lines) + "\n", held_back


def internal_digest(projects, warnings, held, as_of):
    L = [f"# Internal Digest for Group CTO: {fmt(as_of)}", "*Internal only. Do not forward to clients.*", "",
         "## Portfolio", "", "| Project | Client | RAG | Next milestone | Date | Open items | Overdue |", "|---|---|---|---|---|---|---|"]
    for p in projects.values():
        openi = [i for i in p["items"] if not i["closed"]]
        L.append(f"| {p['name']} | {p['client']} | {RAG[p['status']]} | {cell(p['milestone'])} | "
                 f"{fmt(p['m_date'], p['m_text'])} | {len(openi)} | {sum(i['overdue'] for i in openi)} |")
    L.append("")
    for p in projects.values():
        L += [f"## {p['name']}: {RAG[p['status']]}", f"**Main problem:** {cell(p['problem'])}"]
        if p["date_note"]:
            L.append(f"**Date note:** {cell(p['date_note'])}")
        L += ["", "| ID | Type | Description | P x I | Score | Owner | Due | Visibility |", "|---|---|---|---|---|---|---|---|"]
        for i in p["items"]:
            if i["closed"]:
                continue
            flag = " ⚠ OVERDUE" if i["overdue"] else (" ⏰ ≤3 days" if i["due"] and 0 <= (i["due"] - as_of).days <= 3 else "")
            L.append(f"| {i['id']} | {i['type']} | {cell(i['desc'])} | {i['prob']} x {i['impact']} | {i['score']} | {i['owner']} | "
                     f"{fmt(i['due'], i['due_text'])}{flag} | {i['visibility']} |")
        L.append("")
    load = Counter(i["owner"] for p in projects.values() for i in p["items"] if not i["closed"] and i["owner"])
    L += ["## Owner load (open items)", *[f"- {o}: {n}" + ("  ← check capacity" if n >= 4 else "") for o, n in load.most_common()], ""]
    due_soon = sorted((i for p in projects.values() for i in p["items"] if not i["closed"] and i["due"] and i["due"] <= as_of + timedelta(days=3)),
                      key=lambda x: (x["due"], -x["score"]))
    L += ["## Due in the next 3 days (or overdue)", *[f"- {fmt(i['due'])}: {i['id']} {cell(i['desc'])[:80]} ({i['owner']})" for i in due_soon], ""]
    if held or warnings:
        L += ["## Tracker problems to fix before sending", *[f"- {w}" for w in warnings],
              *[f"- {i['id']}: client-visible but no Client Summary, so it was NOT included in the client report." for i in held], ""]
    return "\n".join(L) + "\n"


def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


def run(args):
    as_of = to_date(args.as_of) if args.as_of else date.today()
    if as_of is None:
        raise TrackerError(f"--as-of '{args.as_of}' is not a date (use YYYY-MM-DD).")
    if args.input:
        summary_rows, risk_rows = load_xlsx(args.input)
    elif args.summary_csv and args.risks_csv:
        summary_rows, risk_rows = load_csv(args.summary_csv, args.risks_csv)
    else:
        raise TrackerError("Give --input tracker.xlsx, or both --summary-csv and --risks-csv.")
    projects, warnings = prepare(summary_rows, risk_rows, as_of)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    written, held_all = [], []
    clients = defaultdict(list)
    for p in projects.values():
        clients[p["client"]].append(p)
    for client, plist in clients.items():
        for p in plist:
            text, held = client_report(p, as_of, args.prepared_by)
            held_all += held
            f = out / f"{as_of.isoformat()}_{slug(client)}_{slug(p['name'])}_status.md"
            f.write_text(text, encoding="utf-8")
            written.append(f)
    f = out / f"{as_of.isoformat()}_INTERNAL_group_cto_digest.md"
    f.write_text(internal_digest(projects, warnings, held_all, as_of), encoding="utf-8")
    written.append(f)
    return written, warnings, held_all


def main(argv=None):
    ap = argparse.ArgumentParser(description="Make weekly client status reports from the TPM tracker.")
    ap.add_argument("--input", help="Excel tracker with tabs 'Summary' and 'Risks and Issues'")
    ap.add_argument("--summary-csv")
    ap.add_argument("--risks-csv")
    ap.add_argument("--out", default="reports")
    ap.add_argument("--as-of", help="Report date YYYY-MM-DD (default: today). Used for overdue flags.")
    ap.add_argument("--prepared-by", default="PSI Technical Program Manager")
    args = ap.parse_args(argv)
    try:
        written, warnings, held = run(args)
    except (TrackerError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    for f in written:
        print("wrote", f)
    for w in warnings + [f"{i['id']}: client-visible but no Client Summary; not included in client report." for i in held]:
        print("WARNING:", w, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
