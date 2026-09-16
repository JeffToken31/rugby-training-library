import json
import re
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class UnifiedTests(unittest.TestCase):
    def test_all_cards_and_internal_links(self):
        text=(ROOT/"exports/CATALOGUE.md").read_text()
        payload=json.loads((ROOT/"exports/APPLICATION.json").read_text())
        anchors=re.findall(r'<a id="([^"]+)"',text)
        self.assertEqual(len(anchors),len(set(anchors)))
        self.assertTrue({e["id"] for e in payload["exercises"]} <= set(anchors))
        self.assertTrue(set(re.findall(r'\]\(#([^)]*)\)',text)) <= set(anchors))
        for label in ("Durée pour préparer", "Repères coach proposés", "Contradictions documentaires", "Doublon probable", "Relecture des manques"):
            self.assertIn(label,text)
    def test_old_views_redirect_and_new_evidence_present(self):
        for name in ("DUREES.md","CATEGORIES.md","COMPARAISONS.md"):
            self.assertIn("CATALOGUE.md#",(ROOT/"exports"/name).read_text())
        payload=json.loads((ROOT/"exports/APPLICATION.json").read_text())
        self.assertEqual(payload["consolidation_review"]["pairs_checked"],11175)
        self.assertEqual(len(payload["consolidation_review"]["pair_reviews"]),16)
        e=next(e for e in payload["exercises"] if e["id"]=="nz-memory")
        self.assertEqual(e["fields"]["coach_points"]["origin"],"SOURCE")
        self.assertIn("capture_sha256",e["fields"]["coach_points"]["provenance"])
