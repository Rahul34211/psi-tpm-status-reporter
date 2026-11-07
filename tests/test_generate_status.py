import sys, tempfile, unittest
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import generate_status as g

AS_OF = date(2026, 11, 9)
S = [{"project": "K", "client": "Acme", "status": "Red", "next milestone": "UAT", "milestone date": date(2026, 11, 12),
      "client summary": "Fine text", "main problem": "x"}]
def risk(**kw):
    base = {"project": "K", "id": "K-1", "type": "Issue", "description": "internal words", "client summary": "plain words",
            "probability": "High", "impact": "Critical", "owner": "A", "action / mitigation": "do", "due date": date(2026, 11, 10),
            "status": "Open", "visibility": "Client"}
    base.update(kw); return base

class Tests(unittest.TestCase):
    def test_status_comes_from_sheet_not_risk_count(self):
        s = [dict(S[0], status="Green")]
        projects, _ = g.prepare(s, [risk(), risk(id="K-2"), risk(id="K-3")], AS_OF)
        self.assertEqual(projects["K"]["status"], "green")          # 3 critical risks, still Green: TPM decides
    def test_bad_status_stops_run(self):
        with self.assertRaises(g.TrackerError): g.prepare([dict(S[0], status="Purple")], [], AS_OF)
    def test_score_computed_when_excel_formula_cell_is_empty(self):
        projects, _ = g.prepare(S, [risk(score=None)], AS_OF)
        self.assertEqual(projects["K"]["items"][0]["score"], 12)    # High 3 x Critical 4
    def test_internal_items_never_in_client_report(self):
        projects, _ = g.prepare(S, [risk(), risk(id="K-2", visibility="Internal", description="AI cost 40% over")], AS_OF)
        text, _ = g.client_report(projects["K"], AS_OF, "TPM")
        self.assertIn("K-1", text); self.assertNotIn("K-2", text); self.assertNotIn("AI cost", text)
    def test_internal_wording_not_leaked_when_client_summary_missing(self):
        projects, _ = g.prepare(S, [risk(**{"client summary": ""})], AS_OF)
        text, held = g.client_report(projects["K"], AS_OF, "TPM")
        self.assertNotIn("internal words", text); self.assertEqual(len(held), 1)
    def test_overdue_flag(self):
        projects, _ = g.prepare(S, [risk(**{"due date": date(2026, 11, 6)}), risk(id="K-2", status="Closed", **{"due date": date(2026, 11, 6)})], AS_OF)
        by_id = {i["id"]: i for i in projects["K"]["items"]}
        self.assertTrue(by_id["K-1"]["overdue"]); self.assertFalse(by_id["K-2"]["overdue"])
    def test_missing_owner_and_text_due_date_warn(self):
        _, w = g.prepare(S, [risk(owner="", **{"due date": "Tuesday"})], AS_OF)
        self.assertTrue(any("no owner" in x for x in w)); self.assertTrue(any("due date" in x for x in w))
    def test_sorted_by_score(self):
        projects, _ = g.prepare(S, [risk(id="LOW", probability="Low", impact="Low"), risk(id="TOP")], AS_OF)
        self.assertEqual([i["id"] for i in projects["K"]["items"]], ["TOP", "LOW"])
    def test_end_to_end_sample(self):
        with tempfile.TemporaryDirectory() as d:
            rc = g.main(["--input", str(Path(__file__).resolve().parent.parent / "sample_tracker.xlsx"), "--out", d, "--as-of", "2026-11-09"])
            self.assertEqual(rc, 0)
            names = sorted(p.name for p in Path(d).iterdir())
            self.assertEqual(len(names), 3)
            sagar = next(p for p in Path(d).iterdir() if "Sagar" in p.name).read_text()
            nirmal = next(p for p in Path(d).iterdir() if "Nirmal" in p.name).read_text()
            self.assertNotIn("Arjun is double", sagar + nirmal); self.assertNotIn("40%", nirmal)
            self.assertNotIn("leave", nirmal); self.assertNotIn("Claude Code", sagar)   # internal Action text must not leak   # cost overrun is internal
            self.assertIn("AMBER", sagar); self.assertIn("RED", nirmal)
    def test_csv_style_date_strings_parse(self):
        for v in ("2026-11-10", "2026-11-10 00:00:00", "10-Nov-2026", "Tue 10 Nov 2026"):
            self.assertEqual(g.to_date(v), date(2026, 11, 10), v)
        self.assertIsNone(g.to_date("Tuesday"))
    def test_missing_file_gives_clean_error(self):
        self.assertEqual(g.main(["--input", "nope.xlsx"]), 2)

if __name__ == "__main__": unittest.main()
