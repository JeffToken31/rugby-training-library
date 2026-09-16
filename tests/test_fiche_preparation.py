import copy
import json
from pathlib import Path
import unittest
import fiche_preparation as prep

ROOT = Path(__file__).resolve().parents[1]

class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads((ROOT / "exports/APPLICATION.json").read_text())

    def test_cues_are_separate_from_documentary_criteria(self):
        rows = [e for e in self.payload["exercises"] if e.get("coach_cues")]
        self.assertEqual(len(rows),20)
        for e in rows:
            self.assertEqual(e["coach_cues"]["origin"], "AI_INFERRED")
            self.assertEqual(e["fields"]["success_criteria"], e["documentary_fields"]["success_criteria"])
        carre = next(e for e in rows if e["id"] == "ffr-carre2-atelier")
        self.assertNotEqual(carre["fields"]["duration_min"]["state"], "PRESENT")
        self.assertIn("duration_min", [p["field"] for p in carre["preparation_questions"]])

    def test_known_parameters_not_requested_and_conflicts_preserved(self):
        e=copy.deepcopy(self.payload["exercises"][0])
        e["fields"]["duration_min"]={"state":"PRESENT", "value":7}
        e["fields"]["players_min"]={"state":"CONFLICTING", "value":None}
        pending=prep.preparation(e)
        self.assertNotIn("duration_min", [p["field"] for p in pending])
        self.assertEqual(next(p for p in pending if p["field"]=="players_min")["state"], "CONFLICTING")
