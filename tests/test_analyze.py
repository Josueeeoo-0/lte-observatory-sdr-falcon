import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analyze


def row(t, sfn=1, sf=0, rnti=10, direction=1, mcs=4, prb=5, tbs=100):
    # Exactly the documented 20-column decoded record schema.
    return f"{t} {sfn} {sf} {rnti} {direction} {mcs} {prb} {tbs} 100 0 1 0 0 0 0 2 1 0 24 deadbeef"


class AnalyzeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.input = self.root / "synthetic.log"

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, text):
        self.input.write_text(text, encoding="utf-8")

    def test_invalid_rows_counted_and_bad_schema_does_not_abort_valid_data(self):
        self.write("# capture\n\n" + row("1.25") + "\n" + "1 2 3\n" +
                   row("nan") + "\n" + row("2.25", sf=10) + "\n")
        records, counts = analyze.parse_records(self.input)
        self.assertEqual(len(records), 1)
        self.assertEqual(counts["valid_rows"], 1)
        self.assertEqual(counts["invalid_rows"], 3)
        self.assertEqual(counts["schema_errors"], 1)
        self.assertEqual(counts["comment_lines"], 1)
        self.assertEqual(counts["blank_lines"], 1)

    def test_activity_aggregates_directions_rnti_filter_and_preserves_gap(self):
        self.write("\n".join([row("100", direction=0, prb=7, rnti=12),
                               row("100.4", direction=1, prb=3, rnti=65523),
                               row("102", direction=1, prb=9, rnti=65524),
                               row("103", direction=0, prb=1, rnti=0)]) + "\n")
        result = analyze.analyze(self.input, "pilot A", 1970, 1, self.root / "out")
        folder = self.root / "out" / "data" / "processed" / "pilot-A"
        with (folder / "activity.csv").open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual([int(r["dci_records"]) for r in rows], [2, 1, 1])
        self.assertEqual(int(rows[0]["ul_prb_assignments"]), 7)
        self.assertEqual(int(rows[0]["dl_prb_assignments"]), 3)
        self.assertEqual(int(rows[1]["observed_nonreserved_rnti_count"]), 0)
        self.assertEqual([float(r["window_start_s"]) for r in rows], [0.0, 2.0, 3.0])
        self.assertEqual(result["observed_nonreserved_rnti_count"], 2)
        self.assertTrue((self.root / "out" / "figures" / "pilot-A" / "activity.svg").exists())
        self.assertTrue((self.root / "out" / "docs" / "results" / "pilot-A.md").exists())
        # Gaps do not become fabricated rows or zero-valued observations.
        self.assertNotIn(1.0, [float(r["window_start_s"]) for r in rows])

    def test_loss_experiment_is_deterministic_and_documented_as_synthetic(self):
        self.write("\n".join(row(str(i), prb=(i % 8) + 1) for i in range(80)) + "\n")
        out = self.root / "out"
        analyze.analyze(self.input, "trial", 1970, 1, out)
        path = out / "data" / "processed" / "trial" / "synthetic_record_removal.csv"
        first = path.read_text(encoding="utf-8")
        analyze.analyze(self.input, "trial", 1970, 1, out)
        self.assertEqual(first, path.read_text(encoding="utf-8"))
        with path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual([int(r["synthetic_record_removal_percent"]) for r in rows], [0, 10, 30, 50])
        self.assertEqual(int(rows[0]["change_from_baseline_prb_assignments"]), 0)
        report = (out / "docs" / "results" / "trial.md").read_text(encoding="utf-8")
        self.assertIn("not real subframes", report)
        self.assertNotIn("deadbeef", report)

    def test_no_valid_records_is_error_and_console_zero_is_accepted(self):
        self.write("wrong schema\n")
        with self.assertRaisesRegex(ValueError, "no valid records"):
            analyze.analyze(self.input, "x", 1970, 1, self.root / "out")
        self.assertEqual(analyze._parse_console("Skipped subframes: 0"), 0)

    def test_mcs_validation_extended_sfn_and_distribution_outputs(self):
        self.write(row("10", sfn=1054, direction=0, mcs=31) + "\n" +
                   row("10.5", sfn=1055, direction=1, mcs=7) + "\n" +
                   row("11", mcs=32) + "\n")
        out = self.root / "out"
        result = analyze.analyze(self.input, "mcs", 1970, 1, out,
                                 "Skipped subframes: 0 (0.0%)")
        self.assertEqual(result["valid_rows"], 2)
        self.assertEqual(result["invalid_rows"], 1)
        self.assertEqual(result["console_skipped_subframes_run_level"], 0)
        self.assertEqual(result["console_skipped_subframe_percent_run_level"], 0.0)
        self.assertIn("SFN", result["sfn_note"])
        dist = out / "data" / "processed" / "mcs" / "mcs_distribution.csv"
        with dist.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[31]["ul_dci_records"], "1")
        self.assertEqual(rows[7]["dl_dci_records"], "1")
        self.assertTrue((out / "figures" / "mcs" / "mcs.svg").exists())
        summary_file = json.loads((out / "data" / "processed" / "mcs" / "summary.json").read_text())
        self.assertEqual(summary_file["console_skipped_subframes_run_level"], 0)

    def test_rejects_timestamp_span_that_would_create_excessive_windows(self):
        self.write(row("0") + "\n" + row("200001") + "\n")
        with self.assertRaisesRegex(ValueError, "200000 activity windows"):
            analyze.analyze(self.input, "long", 1970, 1, self.root / "out")

    def test_label_is_safely_slugged_inside_output_tree(self):
        self.write(row("1") + "\n")
        result = analyze.analyze(self.input, "../outside", 1970, 1, self.root / "out")
        self.assertEqual(result["session_slug"], "outside")
        self.assertTrue((self.root / "out" / "data" / "processed" / "outside" / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()
