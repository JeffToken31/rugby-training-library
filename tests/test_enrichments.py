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

    def test_revision_preserves_history_and_field_provenance(self):
        enrichments.ingest(self.db,self.payload)
        old=self.payload["enrichments"][0]
        revision={**old,"id":"revision-2","supersedes":old["id"],"revision_reason":"Précision documentaire","fields":{"common_errors":{"state":"PRESENT","origin":"AI_INFERRED","value":"Exemple à observer"}}}
        enrichments.ingest(self.db,{"enrichments":[revision]})
        enrichments.ingest(self.db,self.payload)
        enrichments.ingest(self.db,{"enrichments":[revision]})
        chain=enrichments.history(self.db,old["variant_id"])
        self.assertEqual([r["id"] for r in chain],[old["id"],"revision-2"])
        item=next(e for e in v2.items(self.db) if e["id"]==old["variant_id"])
        self.assertEqual(item["field_coverage"]["objectives"]["provenance"]["revision_id"],old["id"])
        self.assertEqual(item["common_errors"],"Exemple à observer")
        stale={**revision,"id":"stale"}
        with self.assertRaises(ValueError):
            enrichments.ingest(self.db,{"enrichments":[stale]})

    def test_revision_cannot_replace_source_with_inference(self):
        enrichments.ingest(self.db,self.payload)
        old=self.payload["enrichments"][0]
        revision={**old,"id":"revision-2","supersedes":old["id"],"revision_reason":"Test","fields":{"objectives":{"state":"PRESENT","origin":"AI_INFERRED","value":"Changement"}}}
        with self.assertRaises(ValueError):
            enrichments.ingest(self.db,{"enrichments":[revision]})
        self.assertEqual(len(enrichments.history(self.db,old["variant_id"])),1)

    def test_revision_missing_value_does_not_leave_stale_display(self):
        enrichments.ingest(self.db,self.payload)
        old=self.payload["enrichments"][0]
        revision={**old,"id":"revision-2","supersedes":old["id"],"revision_reason":"Critère proposé retiré pour réexamen","fields":{"success_criteria":{"state":"NOT_EXTRACTED"}}}
        enrichments.ingest(self.db,{"enrichments":[revision]})
        item=next(e for e in v2.items(self.db) if e["id"]==old["variant_id"])
        self.assertIsNone(item["success_criteria"])
        self.assertEqual(len(item["enrichment_history"]),2)

    def test_required_fields_and_origin_are_combined(self):
        enrichments.ingest(self.db,self.payload)
        found=v2.items(self.db,has_fields=("objectives","steps"),field_origin="SOURCE",provider="rugbycoaching")
        self.assertTrue(found)
        self.assertFalse(v2.items(self.db,has_fields=("objectives",),field_origin="SOURCE",provider="absent"))
        inferred=v2.items(self.db,has_fields=("success_criteria",),field_origin="AI_INFERRED")
        self.assertTrue(inferred)
        sourced=v2.items(self.db,has_fields=("success_criteria",),field_origin="SOURCE")
        self.assertNotIn("rc-pass-start",{e["id"] for e in sourced})
        with self.assertRaises(ValueError):
            v2.items(self.db,field_origin="SOURCE")
        with self.assertRaises(ValueError):
            v2.items(self.db,has_fields=("nonexistent",))
