import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import catalogue_v2 as v2
import capture_resources as capture
import json

class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=v2.connect(Path(self.tmp.name)/"test.sqlite")
        v2.ingest(self.db,json.loads((v2.ROOT/"data/seed.json").read_text()))
    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()
    def test_source_and_proposal_filters_remain_separate(self):
        self.assertEqual(v2.items(self.db,theme="passe",minutes=7,players=8),[])
        proposed=v2.items(self.db,theme="passe",minutes=7,players=8,basis="proposal")
        self.assertEqual({e["id"] for e in proposed},{"rc-piggy","rc-pairs"})
    def test_invalid_numeric_filter_rejected(self):
        with self.assertRaises(ValueError):
            v2.items(self.db,minutes=-1)
    def test_capture_reused_and_text_reprocessed_without_network(self):
        with patch.object(capture,"allowed"),patch.object(capture,"fetch",return_value=(b"<p>Ballon</p><script>secret</script>","https://example.org",200,"text/html")) as fetch:
            first=capture.capture(self.db,"rc-eggs",self.tmp.name)
            self.assertEqual(first["state"],"DONE")
            second=capture.capture(self.db,"rc-eggs",self.tmp.name)
            self.assertEqual(second["state"],"REUSED")
            self.assertEqual(fetch.call_count,1)
        capture.extract_html(self.db,first["capture_id"])
        row=self.db.execute("SELECT raw_text_path FROM captures").fetchone()
        self.assertEqual(Path(row[0]).read_text(),"Ballon")
    def test_blocked_resource_does_not_prevent_next(self):
        with patch.object(capture,"allowed",side_effect=PermissionError("robots")):
            blocked=capture.capture(self.db,"rc-eggs",self.tmp.name)
        self.assertEqual(blocked["state"],"BLOCKED")
        with patch.object(capture,"allowed"),patch.object(capture,"fetch",return_value=(b"ok","https://example.org",200,"text/plain")):
            done=capture.capture(self.db,"rc-netball",self.tmp.name)
        self.assertEqual(done["state"],"DONE")
        self.assertEqual([r[0] for r in self.db.execute("SELECT state FROM ingestion_runs ORDER BY started_at")],["BLOCKED","DONE"])
