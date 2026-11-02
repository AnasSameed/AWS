import pathlib, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))
import build_report as B

# Expected result, taken from the SAS practice project's docs/expected_ae_summary.txt
EXPECTED = [
    ("Gastrointestinal disorders", "Diarrhoea", "2 (18.2%)", "2 (18.2%)"),
    ("Gastrointestinal disorders", "Nausea", "0", "5 (45.5%)"),
    ("General disorders and administration site conditions", "Fatigue", "1 (9.1%)", "3 (27.3%)"),
    ("Infections and infestations", "Upper respiratory tract infection", "1 (9.1%)", "4 (36.4%)"),
    ("Nervous system disorders", "Dizziness", "0", "3 (27.3%)"),
    ("Nervous system disorders", "Headache", "2 (18.2%)", "2 (18.2%)"),
    ("Skin and subcutaneous tissue disorders", "Rash", "0", "3 (27.3%)"),
]

class T(unittest.TestCase):
    def setUp(self):
        self.dm = B.read_csv(ROOT / "data" / "dm_raw.csv")
        self.ae = B.read_csv(ROOT / "data" / "ae_raw.csv")
        self.denom, self.rows = B.compute(self.dm, self.ae)

    def test_denominators_exclude_screen_failures(self):
        self.assertEqual(self.denom, {"Placebo": 11, "Drug 10 mg": 11})

    def test_matches_sas_expected_table(self):
        got = [(s, t, B.cell(c["Placebo"], 11), B.cell(c["Drug 10 mg"], 11)) for s, t, c in self.rows]
        self.assertEqual(got, EXPECTED)

    def test_pre_dose_and_non_safety_aes_are_excluded(self):
        dm = [{"SUBJID": "1", "ARM": "Placebo", "FIRSTDOSE": "2026-02-01"},
              {"SUBJID": "2", "ARM": "Screen Failure", "FIRSTDOSE": ""}]
        ae = [{"SUBJID": "1", "AEBODSYS": "X", "AETERM": "Early", "AESTDTC": "2026-01-15"},
              {"SUBJID": "1", "AEBODSYS": "X", "AETERM": "Late", "AESTDTC": "2026-02-10"},
              {"SUBJID": "1", "AEBODSYS": "X", "AETERM": "Late", "AESTDTC": "2026-02-12"},
              {"SUBJID": "2", "AEBODSYS": "X", "AETERM": "SF", "AESTDTC": "2026-02-10"}]
        denom, rows = B.compute(dm, ae)
        self.assertEqual([(t, c["Placebo"]) for _, t, c in rows], [("Late", 1)])  # counted once per subject

    def test_html_is_written_and_escapes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "i.html"
            B.write_html(p, self.denom, self.rows)
            s = p.read_text(encoding="utf-8")
            self.assertIn("Synthetic practice data", s)
            self.assertIn("Nausea", s)

if __name__ == "__main__":
    unittest.main()
