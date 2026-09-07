import copy
import json
import tempfile
import unittest
from pathlib import Path
import catalogue_v2 as v2

class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=v2.connect(Path(self.tmp.name)/"v2.sqlite")
        self.seed=json.loads((v2.ROOT/"data/seed.json").read_text())
        self.ffr=json.loads((v2.ROOT/"data/ffr-2026.json").read_text())
    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()
    def test_legacy_roundtrip_and_repeat_import(self):
        v2.ingest(self.db,self.seed)
        v2.ingest(self.db,self.seed)
        for e in self.seed["exercises"]:
            row=self.db.execute("SELECT parameters_json FROM variants WHERE id=?",(e["id"],)).fetchone()
            self.assertEqual(json.loads(row[0]),e)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM variants").fetchone()[0],33)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM import_snapshots").fetchone()[0],1)
    def test_shared_page_variants_sessions_and_unknown_duration(self):
        v2.ingest(self.db,self.ffr)
        self.assertEqual(len(v2.items(self.db,"Speedy")),2)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],4)
        self.assertIsNone(self.db.execute("SELECT duration_seconds FROM session_exercises WHERE id='ffr-session-1-2025-26:0'").fetchone()[0])
        self.assertEqual(self.db.execute("SELECT duration_seconds FROM session_exercises WHERE id='ffr-session-1-2025-26:2'").fetchone()[0],300)
    def test_bad_reference_rolls_back_batch(self):
        bad=copy.deepcopy(self.ffr)
        bad["exercises"][0]["source_id"]="missing"
        with self.assertRaises(Exception):
            v2.ingest(self.db,bad)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM resources").fetchone()[0],0)
    def test_revision_does_not_overwrite(self):
        v2.ingest(self.db,self.ffr)
        changed=copy.deepcopy(self.ffr)
        changed["exercises"][0]["summary"]="changed"
        with self.assertRaises(ValueError):
            v2.ingest(self.db,changed)
        self.assertEqual(json.loads(self.db.execute("SELECT parameters_json FROM variants WHERE id=?",(changed["exercises"][0]["id"],)).fetchone()[0])["summary"],self.ffr["exercises"][0]["summary"])
    def test_all_batches_export_and_references(self):
        v2.ingest(self.db,self.seed)
        v2.ingest(self.db,self.ffr)
        v2.ingest(self.db,json.loads((v2.ROOT/"data/scotland-primary.json").read_text()))
        self.assertEqual(v2.export(self.db,self.tmp.name),52)
        self.assertEqual(self.db.execute("PRAGMA foreign_key_check").fetchall(),[])
        result=v2.items(self.db)
        self.assertEqual(sum(e["model_status"]=="AI_PARSED" for e in result),9)
        self.assertEqual(len(v2.items(self.db,status="REVIEWED")),43)
        self.assertTrue((Path(self.tmp.name)/"SEANCES.md").exists())
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM duplicate_candidates").fetchone()[0],1)
