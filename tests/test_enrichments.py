import copy
import json
import tempfile
import unittest
from pathlib import Path
import catalogue_v2 as v2
import enrichments

class EnrichmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=v2.connect(Path(self.tmp.name)/"db.sqlite")
        for name in ("rc-young-games.json","rc-cooperation.json"):
            payload=json.loads((v2.ROOT/"data"/name).read_text())
            payload.pop("duplicate_candidates",None)
            v2.ingest(self.db,payload)
        self.payload=json.loads((v2.ROOT/"data/enrichment-details.json").read_text())
    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()
    def test_idempotent_and_original_unchanged(self):
        before=self.db.execute("SELECT parameters_json FROM variants WHERE id='rc-pass-start'").fetchone()[0]
        enrichments.ingest(self.db,self.payload)
        enrichments.ingest(self.db,self.payload)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM enrichments").fetchone()[0],4)
        self.assertEqual(self.db.execute("SELECT parameters_json FROM variants WHERE id='rc-pass-start'").fetchone()[0],before)
        item=next(e for e in v2.items(self.db) if e["id"]=="rc-pass-start")
        self.assertEqual(item["field_coverage"]["duration_min"]["state"],"NOT_STATED")
        self.assertEqual(item["field_coverage"]["success_criteria"]["origin"],"AI_INFERRED")
        self.assertIn("objectives",item)
    def test_source_mismatch_atomic(self):
        bad=copy.deepcopy(self.payload)
        bad["enrichments"][1]["source_id"]="wrong"
        with self.assertRaises(ValueError):
            enrichments.ingest(self.db,bad)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM enrichments").fetchone()[0],0)
    def test_conflict_cannot_replace_known_value(self):
        bad=copy.deepcopy(self.payload)
        bad["enrichments"][3]["fields"]["players_min"]={"state":"PRESENT","origin":"SOURCE","value":99}
        with self.assertRaises(ValueError):
            enrichments.ingest(self.db,bad)
    def test_inferred_label_visible_and_details_searchable(self):
        enrichments.ingest(self.db,self.payload)
        self.assertTrue(v2.items(self.db,"objectifs") == [])
        self.assertTrue(v2.items(self.db,"réceptionner"))
        v2.export(self.db,self.tmp.name)
        card=(Path(self.tmp.name)/"fiches/rc-pass-start.md").read_text()
        self.assertIn("Critères de réussite — proposition IA",card)
