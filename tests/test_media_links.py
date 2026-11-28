import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_media():
    return json.loads((ROOT / "data" / "media-links-20261122.json").read_text(encoding="utf-8"))

def corpus_ids():
    payload = json.loads((ROOT / "exports" / "APPLICATION.json").read_text(encoding="utf-8"))
    return {e["id"] for e in payload["exercises"]}

class MediaLinksTests(unittest.TestCase):
    def setUp(self):
        self.media = load_media()
        self.links = self.media["links"]
        self.by_id = {l["variant_id"]: l for l in self.links}

    def test_one_decision_per_fiche_covering_the_corpus(self):
        # 173 : + ffr-m8-lecture-jeu-11c1 (fiche ajoutée le 2026-11-24,
        # entrée « pas de lien, pas de variante »).
        self.assertEqual(len(self.links), 173)
        self.assertEqual(len(self.by_id), 173)
        self.assertEqual(set(self.by_id), corpus_ids())

    def test_link_entries_are_well_formed(self):
        for l in self.links:
            if l["url"] is not None:
                self.assertRegex(l["url"], r"^https?://")
                self.assertIsInstance(l["title"], str)
                self.assertTrue(l["title"].strip())
                self.assertIn(l["origin"], ("SOURCE", "AI_INFERRED", "USER_REPORTED"))
            self.assertIn(l["review_status"], ("REVIEWED",))
            self.assertEqual(l["checked_on"], "2026-11-22")

    def test_null_entries_declare_no_link_and_no_variant(self):
        for l in self.links:
            if l["url"] is None:
                self.assertIsNone(l["title"])
                self.assertIsNone(l["origin"])
                self.assertFalse(l["is_variant"])
                self.assertIsNone(l["variant_note"])

    def test_totals_and_variant_declaration(self):
        with_link = [l for l in self.links if l["url"]]
        variants = [l for l in with_link if l["is_variant"]]
        self.assertEqual(len(with_link), 97)
        self.assertEqual(len(variants), 44)
        self.assertEqual(len(with_link) - len(variants), 53)
        for l in variants:
            self.assertIsInstance(l["variant_note"], str)
            self.assertTrue(l["variant_note"].strip())
        self.assertEqual(sum(1 for l in with_link if l["origin"] == "SOURCE"), 33)
        self.assertEqual(sum(1 for l in with_link if l["origin"] == "AI_INFERRED"), 64)

    def test_every_exported_fiche_declares_its_media_state(self):
        fiches = sorted((ROOT / "exports" / "fiches").glob("*.md"))
        self.assertEqual(len(fiches), 173)
        no_link = declared_variants = with_link = 0
        for path in fiches:
            text = path.read_text(encoding="utf-8")
            has_link = "**Vidéo de l’exercice" in text
            has_variant = "**Vidéo — variante" in text
            has_none = "**Pas de lien vidéo, pas de variante identifiée" in text
            self.assertEqual(sum((has_link, has_variant, has_none)), 1,
                             "état de média non déclaré dans " + path.name)
            self.assertIn(path.stem, self.by_id)
            if has_link:
                with_link += 1
                self.assertFalse(self.by_id[path.stem]["is_variant"])
            elif has_variant:
                declared_variants += 1
                self.assertTrue(self.by_id[path.stem]["is_variant"])
            else:
                no_link += 1
                self.assertIsNone(self.by_id[path.stem]["url"])
        # 76 : +1 fiche « pas de lien, pas de variante » (2026-11-24).
        self.assertEqual((with_link, declared_variants, no_link), (53, 44, 76))

    def test_source_links_are_documentary_pages(self):
        payload = json.loads((ROOT / "exports" / "APPLICATION.json").read_text(encoding="utf-8"))
        src = {e["id"]: e["source"]["url"] for e in payload["exercises"]}
        rctv = dm = 0
        for fid, l in self.by_id.items():
            if l["url"] is None or l["origin"] != "SOURCE":
                continue
            host = l["url"].split("/")[2]
            if host == "www.rugbycoaching.tv":
                # La vidéo embarquée est sur la page source de la fiche.
                self.assertEqual(l["url"].split("?")[0].rstrip("/"),
                                 src[fid].split("?")[0].rstrip("/"), fid + " : " + l["url"])
                rctv += 1
            elif host == "www.dailymotion.com":
                # Chaîne officielle France Rugby.
                self.assertRegex(l["url"], r"^https://www\.dailymotion\.com/video/[a-z0-9]+/?$", fid + " : " + l["url"])
                dm += 1
            else:
                self.fail(fid + " : lien source inattendu " + l["url"])
        self.assertEqual((rctv, dm), (29, 4))

if __name__ == "__main__":
    unittest.main()
