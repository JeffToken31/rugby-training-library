import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import catalogue_v2 as v2
import pipeline

STUBS=("CATEGORIES.md","DUREES.md","AMELIORATIONS_FICHES.md","COMPARAISONS.md","QUALITE_APPLICATION.md","INDEX.md","FICHES_DETAILLEES.md")

class M2UnifiedTests(unittest.TestCase):
    def test_unified_is_sole_render_path_when_flag_active(self):
        # m2 : consolidation_review actif → le catalogue unifié est le seul
        # chemin de rendu ; la chirurgie application_data est court-circuitée
        # (fiche_preparation.export / timing.export ne doivent pas être appelés).
        with tempfile.TemporaryDirectory() as tmp:
            db=v2.connect(Path(tmp)/"db.sqlite")
            manifest=json.loads((v2.ROOT/"data/manifest.json").read_text())
            with patch.object(pipeline.captures,"fetch",side_effect=AssertionError("Réseau inattendu")),\
                 patch("fiche_preparation.export",side_effect=AssertionError("Chirurgie inattendue")),\
                 patch("timing.export",side_effect=AssertionError("Chirurgie inattendue")):
                pipeline.run(db,manifest,v2.ROOT,Path(tmp)/"exports")
            out=Path(tmp)/"exports"
            catalogue=(out/"CATALOGUE.md").read_text(encoding="utf-8")
            self.assertIn("# Catalogue complet des exercices U8",catalogue)
            self.assertNotIn("Tags proposés",catalogue)
            for name in STUBS:
                text=(out/name).read_text(encoding="utf-8")
                self.assertIn("Vue intégrée au catalogue",text,name+" doit être un stub de redirection")
            seances=(out/"SEANCES.md").read_text(encoding="utf-8")
            self.assertIn("# Séances sources",seances)
            self.assertNotIn("Vue intégrée au catalogue",seances)
            self.assertTrue((out/"APPLICATION.json").is_file())
            self.assertTrue((out/"catalogue.json").is_file())
            self.assertTrue((out/"exercises.csv").is_file())
            self.assertEqual(len(list((out/"fiches").glob("*.md"))),172)
            payload=json.loads((out/"APPLICATION.json").read_text(encoding="utf-8"))
            self.assertEqual(len(payload["exercises"]),172)
            db.close()

    def test_legacy_views_rendered_when_flag_absent(self):
        # Sans consolidation_review, les vues historiques sont rendues
        # (chirurgie application_data active, pas de stubs).
        with tempfile.TemporaryDirectory() as tmp:
            db=v2.connect(Path(tmp)/"db.sqlite")
            manifest=json.loads((v2.ROOT/"data/manifest.json").read_text())
            manifest["application"].pop("consolidation_review")
            with patch.object(pipeline.captures,"fetch",side_effect=AssertionError("Réseau inattendu")):
                pipeline.run(db,manifest,v2.ROOT,Path(tmp)/"exports")
            out=Path(tmp)/"exports"
            catalogue=(out/"CATALOGUE.md").read_text(encoding="utf-8")
            self.assertIn("# Bibliothèque rugby U8",catalogue)
            self.assertIn("Tags proposés",catalogue)
            self.assertNotIn("# Catalogue complet des exercices U8",catalogue)
            detail=(out/"FICHES_DETAILLEES.md").read_text(encoding="utf-8")
            self.assertIn("# Fiches avec organisation et déroulement sourcés",detail)
            self.assertNotIn("Vue intégrée au catalogue",detail)
            self.assertIn("# Base destinée à la création de séances",(out/"QUALITE_APPLICATION.md").read_text(encoding="utf-8"))
            self.assertNotIn("Vue intégrée au catalogue",(out/"COMPARAISONS.md").read_text(encoding="utf-8"))
            self.assertNotIn("Vue intégrée au catalogue",(out/"INDEX.md").read_text(encoding="utf-8"))
            self.assertEqual(len(list((out/"fiches").glob("*.md"))),172)
            db.close()
