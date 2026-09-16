import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import application_data as app
import catalogue_v2 as v2
import pipeline
import session_plan

class ApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = v2.connect(Path(cls.tmp.name) / "fresh.sqlite")
        cls.manifest = app.read(v2.ROOT / "data/manifest.json")
        cls.out = Path(cls.tmp.name) / "exports"
        with patch.object(pipeline.captures, "fetch", side_effect=AssertionError("Réseau interdit")):
            pipeline.run(cls.db, cls.manifest, v2.ROOT, cls.out)
        cls.payload = app.read(cls.out / "APPLICATION.json")

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.tmp.cleanup()

    def test_full_corpus_classified_without_merging(self):
        self.assertEqual(len(self.payload["exercises"]),150)
        self.assertEqual(len(self.payload["families"]),22)
        self.assertIsNone(self.payload["summary"]["unique_exercises"])
        ids = {e["id"] for e in self.payload["exercises"]}
        self.assertTrue({"imagine-depth-running", "wr-chain-reaction"} <= ids)
        self.assertEqual(self.payload["summary"]["readiness"], {"DOCUMENTED_CORE":122,"PROPOSED_OBJECTIVE":18,"REPORTED_OBSERVATION":1,"INCOMPLETE":9})

    def test_reported_observation_does_not_invent_duration_or_source(self):
        e = next(e for e in self.payload["exercises"] if e["id"] == "ffr-carre2-atelier")
        self.assertEqual(e["fields"]["steps"]["origin"], "USER_REPORTED")
        self.assertNotEqual(e["documentary_fields"]["steps"]["state"], "PRESENT")
        self.assertFalse(e["observation"]["observed_duration"]["is_prescribed_duration"])
        self.assertEqual(e["fields"]["duration_min"], e["documentary_fields"]["duration_min"])
        self.assertFalse(e["quality"]["coach_validated"])

    def test_objectives_remain_proposals(self):
        rows=[e for e in self.payload["exercises"] if e["quality"]["state"]=="PROPOSED_OBJECTIVE"]
        for e in rows:
            self.assertEqual(e["fields"]["objectives"]["origin"], "AI_INFERRED")
            if e["id"] != "scot-break-walls":
                self.assertNotEqual(e["documentary_fields"]["objectives"]["state"], "PRESENT")

    def test_rebuild_is_stable_including_fiche_supplements(self):
        before=(self.out / "APPLICATION.json").read_bytes()
        fiche=(self.out / "fiches/ffr-carre2-atelier.md").read_bytes()
        with patch.object(pipeline.captures, "fetch", side_effect=AssertionError("Réseau interdit")):
            pipeline.run(self.db, self.manifest, v2.ROOT, self.out)
        self.assertEqual(before,(self.out / "APPLICATION.json").read_bytes())
        self.assertEqual(fiche,(self.out / "fiches/ffr-carre2-atelier.md").read_bytes())

    def test_missing_classification_rejected(self):
        real_read=app.read
        def changed(path):
            data=real_read(path)
            if str(path).endswith("classification-audit.json"):
                data["assignments"].pop()
            return data
        with patch.object(app,"read",side_effect=changed), self.assertRaises(ValueError):
            app.build(self.db,v2.ROOT,self.manifest["application"])

    def test_rotation_time_counted_once_not_per_group(self):
        plan=app.read(v2.ROOT / "data/session-draft.example.json")
        self.assertEqual(session_plan.validate(plan,self.payload), [])
        bad=copy.deepcopy(plan)
        bad["blocks"][3]["duration_min"]=72
        self.assertIn("Durée totale différente de la somme des blocs",session_plan.validate(bad,self.payload))
        bad=copy.deepcopy(plan)
        bad["blocks"][3]["rounds"][0]["assignments"][0]["variant_id"]="ffr-plaquage-atelier"
        self.assertIn("Exercice trop incomplet : ffr-plaquage-atelier",session_plan.validate(bad,self.payload))
        bad=copy.deepcopy(plan)
        bad["blocks"][3]["rounds"][0]["assignments"][0]["group_id"]="B"
        self.assertIn("Chaque groupe doit être affecté une fois par rotation",session_plan.validate(bad,self.payload))
