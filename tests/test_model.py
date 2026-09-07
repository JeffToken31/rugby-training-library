import sqlite3
import unittest
from pathlib import Path

class ModelTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.executescript((Path(__file__).resolve().parents[1]/"schema/v2.sql").read_text())
        self.db.execute("INSERT INTO resources(id) VALUES('r')")
        self.db.execute("INSERT INTO occurrences(id,resource_id,page_start,page_end) VALUES('o','r',5,6)")
    def tearDown(self):
        self.db.close()
    def variant(self, id):
        self.db.execute("INSERT INTO variants(id,title,origin) VALUES(?, 'Même titre', 'SOURCE')",(id,))
    def test_shared_title_and_shared_page_are_allowed(self):
        for id in ('a','b'):
            self.variant(id)
            self.db.execute("INSERT INTO exercise_sources VALUES(?, 'o', 'description', NULL)",(id,))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM exercise_sources").fetchone()[0],2)
    def test_unknown_parameters_allowed(self):
        self.variant('a')
        self.assertEqual(self.db.execute("SELECT family_id,parameters_json FROM variants").fetchone(),(None,'{}'))
    def test_validation_requires_attribution(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO variants(id,origin,status) VALUES('x','SOURCE','VALIDATED')")
    def test_bad_page_range_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO occurrences(id,resource_id,page_start,page_end) VALUES('x','r',7,5)")
    def test_similarity_preserves_both_variants(self):
        self.variant('a'); self.variant('b')
        self.db.execute("INSERT INTO duplicate_candidates(id,left_id,right_id,score,method_version) VALUES('d','a','b',0.9,'test')")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM variants").fetchone()[0],2)
    def test_conflicting_assertions_retained_but_one_selected(self):
        self.variant('a')
        for id,value in [('x','4'),('y','8')]:
            self.db.execute("INSERT INTO assertions VALUES(?, 'a','players_min',?,'SOURCE','o','test','2026-09-07',0)",(id,value))
        self.db.execute("UPDATE assertions SET selected=1 WHERE id='x'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE assertions SET selected=1 WHERE id='y'")
    def test_session_can_repeat_variant_and_include_break(self):
        self.variant('a')
        self.db.execute("INSERT INTO sessions(id,origin) VALUES('s','AI_SUGGESTED')")
        for id,position in [('x',0),('y',1)]:
            self.db.execute("INSERT INTO session_exercises(id,session_id,variant_id,position,kind,duration_seconds) VALUES(?,'s','a',?,'EXERCISE',420)",(id,position))
        self.db.execute("INSERT INTO session_exercises(id,session_id,position,kind,duration_seconds) VALUES('z','s',2,'BREAK',600)")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM session_exercises").fetchone()[0],3)
