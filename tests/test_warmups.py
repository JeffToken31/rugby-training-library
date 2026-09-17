import json
import unittest
from pathlib import Path
import exercise_tags
ROOT=Path(__file__).resolve().parents[1]
class WarmupTests(unittest.TestCase):
    def test_sourced_usage_and_complete_descriptions(self):
        payload=json.loads((ROOT/"exports/APPLICATION.json").read_text())
        rows=exercise_tags.select(payload,session_use="WARMUP")
        self.assertEqual(len(rows),8)
        self.assertEqual({e["warmup_usage"]["stage"] for e in rows},{"general","mobility","specific"})
        for e in rows:
            self.assertEqual(e["warmup_usage"]["usage_origin"],"SOURCE")
            self.assertEqual(e["fields"]["objectives"]["origin"],"AI_INFERRED")
            self.assertTrue(all(e["fields"][f]["state"]=="PRESENT" for f in ["organisation","steps","instructions"]))
            self.assertFalse(e["quality"]["coach_validated"])
        passing=exercise_tags.select(payload,["skill:passe"],session_use="WARMUP")
        self.assertEqual([e["id"] for e in passing],["warm-any-direction-tag"])
        self.assertIn('id="echauffements"',(ROOT/"exports/CATALOGUE.md").read_text())
