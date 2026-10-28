"""Meaningful invariants for source preservation, temporal joins, and label safety."""
import hashlib
import json
from pathlib import Path
import unittest
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


class DataIntegrity(unittest.TestCase):
    def test_sources_match_recorded_checksums(self):
        for source in json.loads((ROOT / "data/metadata/source_files.json").read_text()):
            self.assertEqual(hashlib.sha256((ROOT / source["local_path"]).read_bytes()).hexdigest(), source["sha256"])

    def test_unknown_labels_not_encoded_as_controls(self):
        lesions = pd.read_csv(ROOT / "data/processed/lesions.csv")
        self.assertEqual(len(lesions), 160)
        self.assertEqual(lesions.patient_id.nunique(), 75)
        self.assertEqual(lesions.rn_time_day.notna().sum(), 32)
        self.assertTrue((lesions.loc[lesions.rn_time_day.isna(), "rn_status"] == "unknown").all())
        self.assertEqual(lesions.final_eligible.sum(), 0)
        self.assertFalse(lesions.duplicated(["patient_id", "lesion_id"]).any())

    def test_baseline_temporal_order(self):
        data = pd.read_csv(ROOT / "data/processed/baseline_matches.csv")
        self.assertTrue(data.baseline_to_srs_days.between(0, 30).all())
        recorded = data[data.rn_time_day.notna()]
        self.assertTrue((recorded.rn_time_day > recorded.first_srs_start_day).all())
        early = data[data.early_day.notna()]
        self.assertTrue((early.early_day-early.first_srs_start_day).between(30, 90).all())

    def test_no_duplicate_series_keys(self):
        data = pd.read_csv(ROOT / "data/processed/image_series.csv")
        self.assertFalse(data.duplicated(["patient_id", "study_date_code", "series_name", "archive_id"]).any())


if __name__ == "__main__":
    unittest.main()
