import copy
import tempfile
import unittest
from pathlib import Path
import library

class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = library.connect(Path(self.tmp.name)/"test.sqlite")
        self.payload = {"sources":[{"id":"s","title":"Source","url":"https://example.org/a?utm_source=x","publisher":"Test","checked_on":"2026-09-06","access":"texte public"}],
                        "exercises":[{"id":"e","source_id":"s","locator":"page 1","title":"Équilibre et passe","summary":"Réception en mouvement","age_source":"M8","theme":"passe","review":"à valider","duration_min":None,"players_min":None,"players_max":None}]}
    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()
    def test_idempotent_and_accent_search(self):
        library.ingest(self.db,self.payload)
        library.ingest(self.db,self.payload)
        self.assertEqual(len(library.search(self.db,"equilibre reception")),1)
        self.assertEqual(library.search(self.db)[0]["source"]["url"],"https://example.org/a")
    def test_unknown_is_not_compatible(self):
        library.ingest(self.db,self.payload)
        self.assertEqual(library.search(self.db,minutes=10),[])
        self.assertEqual(library.search(self.db,players=8),[])
    def test_numeric_bounds(self):
        self.payload["exercises"][0].update(duration_min=7,players_min=4,players_max=8)
        library.ingest(self.db,self.payload)
        self.assertEqual(len(library.search(self.db,minutes=7,players=8)),1)
        self.assertEqual(library.search(self.db,players=9),[])
    def test_atomic_import(self):
        self.payload["exercises"][0]["source_id"]="absent"
        with self.assertRaises(Exception):
            library.ingest(self.db,self.payload)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM sources").fetchone()[0],0)
    def test_duplicate_locator_rejected(self):
        library.ingest(self.db,self.payload)
        duplicate=copy.deepcopy(self.payload)
        duplicate["exercises"][0]["id"]="other"
        with self.assertRaises(Exception):
            library.ingest(self.db,duplicate)
        self.assertEqual(len(library.search(self.db)),1)
    def test_export_provenance(self):
        library.ingest(self.db,self.payload)
        library.export(self.db,self.tmp.name)
        report=(Path(self.tmp.name)/"CATALOGUE.md").read_text()
        self.assertIn("https://example.org/a",report)
        self.assertIn("page 1",report)
        self.assertIn("Non renseignée",report)

if __name__=="__main__":
    unittest.main()
