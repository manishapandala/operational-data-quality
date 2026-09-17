import unittest

import pandas as pd

from data_quality import REQUIRED_COLUMNS, clean, generate_records, validate


class DataQualityTests(unittest.TestCase):
    def test_generated_shape(self):
        self.assertEqual(generate_records(50).shape, (50, len(REQUIRED_COLUMNS)))

    def test_generation_is_deterministic(self):
        pd.testing.assert_frame_equal(generate_records(20), generate_records(20))

    def test_invalid_size_is_rejected(self):
        with self.assertRaises(ValueError):
            generate_records(0)

    def test_schema_is_required(self):
        with self.assertRaises(ValueError):
            validate(pd.DataFrame({"record_id": ["1"]}))

    def test_validation_finds_known_issues(self):
        report = validate(generate_records(100))
        self.assertGreater(report["invalid_rows"], 0)
        self.assertIn("email:invalid_format", report["issue_counts"])

    def test_cleaning_removes_validation_issues(self):
        cleaned, _ = clean(generate_records(500))
        report = validate(cleaned)
        self.assertEqual(report["invalid_rows"], 0)
        self.assertEqual(report["quality_score"], 1.0)

    def test_cleaning_records_audit_counts(self):
        _, audit = clean(generate_records(200))
        self.assertEqual(audit["input_rows"], 200)
        self.assertGreater(audit["repairs"]["email"], 0)

    def test_cleaning_is_idempotent(self):
        once, _ = clean(generate_records(300))
        twice, audit = clean(once)
        pd.testing.assert_frame_equal(once, twice)
        self.assertEqual(audit["duplicates_removed"], 0)

    def test_empty_frame_scores_as_valid(self):
        empty = pd.DataFrame(columns=REQUIRED_COLUMNS)
        self.assertEqual(validate(empty)["quality_score"], 1.0)


if __name__ == "__main__":
    unittest.main()
