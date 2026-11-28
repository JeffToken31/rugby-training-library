import json
import unittest
from pathlib import Path
import session_plan
import webapp

ROOT = Path(__file__).resolve().parent.parent
VECTORS = json.loads((ROOT/"tests"/"vectors.json").read_text(encoding="utf-8"))

class SessionVectors(unittest.TestCase):
    # n3 (tranché le 2026-11-22) : même corpus rejoué côté Python
    # (session_plan.validate + webapp.minutage_derivee) et côté TypeScript
    # (web/scripts/replay-vectors.mts). Les messages et le minutage doivent
    # être strictement identiques des deux côtés — verrouille la leçon m1.
    def test_sessions(self):
        for vec in VECTORS["sessions"]:
            with self.subTest(name=vec["name"]):
                catalogue={"exercises":[{"id":k,"quality":{"state":v}} for k,v in vec["etat"].items()]}
                erreurs=session_plan.validate(vec["plan"],catalogue)
                bloquantes=[m for m in erreurs if not m.startswith("Avertissement")]
                avertissements=[m for m in erreurs if m.startswith("Avertissement")]
                attendu=vec["expected"]
                self.assertEqual(bloquantes,attendu["erreurs"],"erreurs")
                self.assertEqual(avertissements,attendu["avertissements"],"avertissements")
                self.assertEqual(webapp.minutage_derivee(vec["plan"]),attendu["minutage"],"minutage")
                self.assertEqual(bloquantes==[],attendu["valide"],"valide")

class FilterVectors(unittest.TestCase):
    # n3 : filtres rejoués sur le vrai exports/APPLICATION.json via
    # webapp.select_catalogue (miroir de web/lib/filter.ts).
    def test_filters(self):
        for vec in VECTORS["filters"]:
            with self.subTest(name=vec["name"]):
                o=vec["opts"]
                cartes=webapp.select_catalogue(
                    query=o.get("query"),
                    tag_ids=o.get("tag_ids",[]),
                    match=o.get("match","all"),
                    include_incomplete=o.get("include_incomplete",True),
                    usage=o.get("usage"))
                ids=[c["id"] for c in cartes]
                attendu=vec["expected"]
                if "ids" in attendu:
                    self.assertEqual(sorted(ids),sorted(attendu["ids"]),"ids")
                else:
                    self.assertEqual(len(ids),attendu["count"],"count")
