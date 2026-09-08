import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import catalogue_v2 as v2
import pipeline

class PipelineTests(unittest.TestCase):
    def test_rebuild_twice_offline_preserves_enrichments(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=v2.connect(Path(tmp)/"db.sqlite")
            manifest=json.loads((v2.ROOT/"data/manifest.json").read_text())
            with patch.object(pipeline.captures,"fetch",side_effect=AssertionError("Réseau inattendu")):
                first=pipeline.run(db,manifest,v2.ROOT,Path(tmp)/"exports")
                second=pipeline.run(db,manifest,v2.ROOT,Path(tmp)/"exports")
            self.assertEqual(first["variants"],second["variants"])
            self.assertGreaterEqual(second["enriched"],16)
            self.assertEqual(second["captured_resources"],0)
            item=next(e for e in v2.items(db) if e["id"]=="rc-pairs")
            self.assertFalse(item["enrichment_provenance"]["capture_verified_locally"])
            self.assertTrue((Path(tmp)/"exports/ETAT_COLLECTE.md").is_file())
            db.close()
    def test_failed_capture_continues_and_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=v2.connect(Path(tmp)/"db.sqlite")
            manifest={"data":["data/seed.json"],"enrichments":[],"capture_resources":["rc-eggs","rc-netball"]}
            with patch.object(pipeline.captures,"capture",side_effect=[{"resource_id":"rc-eggs","state":"FAILED","error":"timeout"},{"resource_id":"rc-netball","state":"FAILED","error":"timeout"}]),patch.object(pipeline.time,"sleep"):
                result=pipeline.run(db,manifest,v2.ROOT,Path(tmp)/"exports",True)
            self.assertEqual(len(result["events"]),2)
            self.assertEqual(result["variants"],33)
            db.close()
