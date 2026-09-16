import copy
import json
from pathlib import Path
import unittest
import timing
ROOT=Path(__file__).resolve().parents[1]
class TimingTests(unittest.TestCase):
    def test_totals_and_source_separation(self):
        payload=json.loads((ROOT/"exports/APPLICATION.json").read_text())
        for e in payload["exercises"]:
            t=e["planning_duration"]
            self.assertEqual(e["fields"]["duration_min"],e["documentary_fields"]["duration_min"])
            if t.get("profile"):
                self.assertEqual(t["min_seconds"],timing.total(t["profile"],t["profile"]["rounds_min"]))
                self.assertEqual(t["max_seconds"],timing.total(t["profile"],t["profile"]["rounds_max"]))
                self.assertFalse(t["includes_group_transition"])
            if e["quality"]["state"]=="INCOMPLETE":
                self.assertEqual(t["status"],"INSUFFICIENT_DESCRIPTION")
        e=next(e for e in payload["exercises"] if e["id"]=="ffr-carre2-atelier")
        self.assertEqual(e["planning_duration"]["origin"],"AI_INFERRED")
        self.assertFalse(e["observation"]["observed_duration"]["is_prescribed_duration"])
        e=next(e for e in payload["exercises"] if e["id"]=="ffr-espaces2023")
        self.assertEqual(e["planning_duration"]["status"],"KNOWN_ROUND_DURATION")
        self.assertEqual(e["bout_seconds"],8)
    def test_rounds_have_no_extra_final_pause(self):
        p=dict(intro_seconds=60,round_seconds=60,between_seconds=30,outro_seconds=60)
        self.assertEqual(timing.total(p,3),360)
        self.assertEqual(timing.total(p,4),450)
