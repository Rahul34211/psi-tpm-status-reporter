# PSI TPM Weekly Status Reporter (Task 7)

A small command-line tool for a Technical Program Manager. It reads the Task 5 tracker
(Excel, or two CSV files) and writes the weekly status reports in about one second:

|Output|Reader|What it contains|
|-|-|-|
|`<date>\_<client>\_<project>\_status.md` (one per client)|Client executive|RAG status, next milestone, summary, client-visible items in plain language, next dates|
|`<date>\_INTERNAL\_group\_cto\_digest.md`|Group CTO|All items ranked by score, overdue / due in 3 days, owner load, tracker problems|

**Why it is useful in the Monday-morning scenario:** the Ledger Friday report was missed. With this tool the
report is a 1-second job from the tracker the TPM already keeps. It also protects against the opposite mistake: sending
internal facts (AI cost overrun, a person on leave, another client's work) to a client.

## Run it

Needs Python 3.9+ and one package (`openpyxl`). Nothing else.

```bash
pip install openpyxl
python generate\_status.py --input sample\_tracker.xlsx --out reports --as-of 2026-11-09
# CSV instead of Excel:
python generate\_status.py --summary-csv summary.csv --risks-csv risks.csv --out reports
# Tests (stdlib only):
python -m unittest discover -s tests
```

`--as-of` sets the report date for the "overdue" flags (default: today). `--prepared-by` sets the sender name.
Ready-made output for the sample data is in `sample\_reports/`.

## Tracker format (sheet names matter)

* **Summary** tab: `Project, Client, Client Contact, Status, Next Milestone, Milestone Date, Date Note, Main Problem (internal), Client Summary (plain language)`
* **Risks and Issues** tab: `Project, ID, Type, Description (internal), Client Summary (plain language), Probability, Impact, Score, Owner, Action / Mitigation, Due Date, Status, Visibility`
* The tool finds the header row by name, so title rows above the table are fine. Column order does not matter.

## Design rules (what I decided, not the AI)

1. **RAG is never calculated.** The TPM sets Red/Amber/Green in the Summary tab. A wrong value stops the run (exit code 2).
2. **`Visibility = Internal` items never reach a client report.** The internal `Action` column is never printed in a client report either.
3. **No plain-language text = not sent.** If a client-visible item has no `Client Summary`, it is left out and listed as a warning. Reusing the internal wording could leak.
4. **Score = Probability (1-3) x Impact (1-4)**, computed in Python (see error 1 below).
5. Missing owner, missing action, a due date that is not a date, or an unknown project are shown as warnings. The tool does not fill gaps.

## Limits

Markdown output only (paste into email or convert with any Markdown tool). Dates are plain calendar dates; free text such as "Tuesday" is shown but cannot be checked for overdue. No Jira/ClickUp connection.

## AI use (disclosure)

Built with **Claude (Claude Code style session)**. I wrote the design rules above and the tracker content; Claude wrote the first code and tests.
I ran the tests and the sample, then checked the outputs by reading the reports line by line.

### Prompts I used (main ones, in order)

1. *"Act as an experienced technical project manager. Read the assignment, the JD and my Task 1-6 files. Build a small tool that reads the Task 5 tracker and makes a weekly status report for each client. Create code and files for Task 7. Then review Tasks 1-8 and tell me what needs to change."*
2. *"Read the tracker with Python. The report must be client-safe: use plain language, and never show internal items (AI cost, staff leave, other projects) to a client."* (design rule 2 and 3)
3. *"Add a Group CTO digest with overdue items and owner load."*
4. *"Write tests for: status is not inferred from risk count, internal items never leak, overdue logic, CSV dates."*
5. *"Fix the CSV date bug."* (error 2)

> \*\*Replace or extend this list with your own real prompts before you submit.\*\* The assignment asks for the prompts you actually used.

### Errors the AI made and how they were corrected

**Error 1: Score column read as empty.** The tracker has a `Score` formula (`=MATCH(...)\*MATCH(...)`). The AI planned to read that column
with `openpyxl(data\_only=True)`. I checked a real read and it returned `None`: a file written by a script has no cached formula values until
Excel opens and saves it. A report ranked by `None` would silently put every item at 0.
*Fix:* the tool ignores the `Score` cell and computes `PROB\[p] \* IMPACT\[i]` itself. Test: `test\_score\_computed\_when\_excel\_formula\_cell\_is\_empty`.

**Error 2: CSV dates not recognised.** The first date parser accepted `2026-11-10` but not `2026-11-10 00:00:00`, which is how Excel exports dates to CSV. Every due date became "missing" in a CSV run, with 11 warnings, while the Excel run looked fine.
I found it only because I tested the CSV path separately. *Fix:* added that format; test `test\_csv\_style\_date\_strings\_parse`.

**Error 3 (design, caught in review): internal action text in the client report.** The first client table included the `Action` column, which says things like "Meera hands the finding to Arjun before leave" and "amount is read from the lending system, not generated by the model". Fix: the client table uses only the plain-language text, owner and date; test asserts "leave" is absent.

## Files

```
generate\_status.py        the tool (one file, \~250 lines)
sample\_tracker.xlsx       Task 5 tracker (Summary + Risks and Issues)
build\_sample\_tracker.py   script that created the sample tracker
tests/                    11 unit tests
sample\_reports/           output for 2026-11-09
```

