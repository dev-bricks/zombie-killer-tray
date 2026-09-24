import json
import tempfile
import unittest
from pathlib import Path

import zombie_settings as s


class IntervalChoicesTests(unittest.TestCase):
    def test_default_interval_is_thirty_minutes_and_allowed(self):
        self.assertEqual(s.DEFAULT_INTERVAL_SECONDS, 1800)
        self.assertIn(1800, s.ALLOWED_INTERVAL_SECONDS)

    def test_all_required_presets_present_exactly_once(self):
        expected = {300, 600, 1200, 1800, 3600, 10800, 18000, 36000, 54000, 72000, 86400}
        self.assertEqual(s.ALLOWED_INTERVAL_SECONDS, expected)
        self.assertEqual(len(s.INTERVAL_CHOICES), len(expected))

    def test_choices_are_strictly_ascending(self):
        seconds = [choice.seconds for choice in s.INTERVAL_CHOICES]
        self.assertEqual(seconds, sorted(seconds))

    def test_label_for_known_and_unknown_value(self):
        self.assertEqual(s.label_for(1800), "30 min")
        self.assertEqual(s.label_for(86400), "24 h (taeglich)")
        self.assertEqual(s.label_for(42), "42s")


class LoadSettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "zombie_state.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_file_returns_defaults(self):
        self.assertEqual(
            s.load_settings(self.path),
            {"automatic": s.DEFAULT_AUTOMATIC, "interval_seconds": s.DEFAULT_INTERVAL_SECONDS},
        )

    def test_corrupt_json_returns_defaults(self):
        self.path.write_text("{not valid json", encoding="utf-8")
        self.assertEqual(
            s.load_settings(self.path),
            {"automatic": s.DEFAULT_AUTOMATIC, "interval_seconds": s.DEFAULT_INTERVAL_SECONDS},
        )

    def test_non_object_json_returns_defaults(self):
        self.path.write_text("[1, 2, 3]", encoding="utf-8")
        self.assertEqual(
            s.load_settings(self.path),
            {"automatic": s.DEFAULT_AUTOMATIC, "interval_seconds": s.DEFAULT_INTERVAL_SECONDS},
        )

    def test_valid_file_roundtrips(self):
        self.path.write_text(
            json.dumps({"automatic": True, "interval_seconds": 3600}), encoding="utf-8"
        )
        self.assertEqual(
            s.load_settings(self.path), {"automatic": True, "interval_seconds": 3600}
        )

    def test_out_of_range_interval_falls_back_to_default_without_losing_automatic_flag(self):
        self.path.write_text(
            json.dumps({"automatic": True, "interval_seconds": 42}), encoding="utf-8"
        )
        self.assertEqual(
            s.load_settings(self.path),
            {"automatic": True, "interval_seconds": s.DEFAULT_INTERVAL_SECONDS},
        )

    def test_non_bool_automatic_falls_back_to_default_without_losing_interval(self):
        self.path.write_text(
            json.dumps({"automatic": "yes", "interval_seconds": 600}), encoding="utf-8"
        )
        self.assertEqual(
            s.load_settings(self.path), {"automatic": s.DEFAULT_AUTOMATIC, "interval_seconds": 600}
        )


class SaveSettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "zombie_state.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_then_load_roundtrips(self):
        s.save_settings(True, 300, self.path)
        self.assertEqual(s.load_settings(self.path), {"automatic": True, "interval_seconds": 300})

    def test_save_rejects_interval_outside_preset_list(self):
        with self.assertRaises(ValueError):
            s.save_settings(True, 42, self.path)
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
