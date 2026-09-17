import copy
import json
import unittest
from pathlib import Path
import exercise_tags as tags

ROOT = Path(__file__).resolve().parents[1]

class TagTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads((ROOT / "exports/APPLICATION.json").read_text())
        self.taxonomy = json.loads((ROOT / "data/exercise-tags.json").read_text())
        tags.attach(self.payload, self.taxonomy)

    def test_all_records_covered_without_duplicate_variants(self):
        self.assertEqual(len(self.payload["exercises"]), 158)
        self.assertEqual(len({e["id"] for e in self.payload["exercises"]}), 158)
        self.assertTrue(all(e["tag_ids"] for e in self.payload["exercises"]))

    def test_cross_category_filters_return_unique_results(self):
        both = tags.select(self.payload, ["skill:passe", "format:surnombre"])
        either = tags.select(self.payload, ["skill:passe", "format:surnombre"], "any")
        self.assertIn("rc-two-one", {e["id"] for e in both})
        self.assertGreater(len(either), len(both))
        self.assertEqual(len(either), len({e["id"] for e in either}))

    def test_tackle_word_is_not_a_plaquage_tag(self):
        e = next(e for e in self.payload["exercises"] if e["id"] == "au-pop-race")
        self.assertNotIn("skill:plaquage", e["tag_ids"])
        self.assertEqual(tags.select(self.payload, ["skill:plaquage"]), [])
        rows = tags.select(self.payload, ["skill:plaquage"], include_incomplete=True)
        self.assertEqual([e["id"] for e in rows], ["ffr-plaquage-atelier"])
        self.assertEqual(rows[0]["tagging"]["status"], "PROVISIONAL")

    def test_missing_unknown_and_duplicate_assignments_fail(self):
        for mode in ("missing", "unknown", "duplicate"):
            data = copy.deepcopy(self.taxonomy)
            if mode == "missing": data["assignments"].pop()
            if mode == "unknown": data["assignments"][0]["tag_ids"].append("skill:invented")
            if mode == "duplicate": data["assignments"].append(data["assignments"][0])
            with self.assertRaises(ValueError): tags.attach(self.payload, data)
        with self.assertRaises(ValueError): tags.select(self.payload, ["typo"])
