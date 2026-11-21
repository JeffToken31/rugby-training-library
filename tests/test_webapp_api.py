"""Lot 1 — API de webapp.py, testée en WSGI (pas de serveur lancé).

Critère 4 du charter : la cohérence des filtres tags avec
exercise_tags.select est vérifiée sur trois cas (all, any,
incomplètes incluses). La recherche est vérifiée pour
l'insensibilité aux accents et les 3 champs (titre, original_title,
résumé).
"""
import io
import json
import unittest
import unicodedata
from pathlib import Path
from urllib.parse import quote

import exercise_tags as tags
import webapp

ROOT = Path(__file__).resolve().parents[1]


def _fold_independent(text):
    """Même pliage accents, écrit à part pour rester indépendant de webapp."""
    if not text:
        return ""
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii").lower()


def call(path, method="GET", query="", data=None):
    captured = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)

    environ = {"PATH_INFO": path, "REQUEST_METHOD": method, "QUERY_STRING": query}
    if data is not None:
        raw = data if isinstance(data, (bytes, bytearray)) else json.dumps(data, ensure_ascii=False).encode("utf-8")
        environ["wsgi.input"] = io.BytesIO(raw)
        environ["CONTENT_LENGTH"] = str(len(raw))
    body = b"".join(webapp.application(environ, start_response))
    code = int(captured["status"].split(" ", 1)[0])
    return code, captured["headers"], body


def call_json(path, query="", data=None, method="GET"):
    code, headers, body = call(path, query=query, data=data, method=method)
    return code, json.loads(body)


class WebappApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads((ROOT / "exports/APPLICATION.json").read_text(encoding="utf-8"))

    def _expected_search(self, q):
        qf = _fold_independent(q)
        out = []
        for e in self.payload["exercises"]:
            if (
                qf in _fold_independent(e.get("title"))
                or qf in _fold_independent(e.get("original_title"))
                or qf in _fold_independent(e.get("summary"))
            ):
                out.append(e["id"])
        return out

    # ------------------------------------------------------------------
    # /api/catalogue
    # ------------------------------------------------------------------
    def test_catalogue_view_shape_and_counts(self):
        code, view = call_json("/api/catalogue")
        self.assertEqual(code, 200)
        self.assertEqual(view["summary"]["records"], 172)
        # Le catalogue complet est livré (172 cartes) ; la sélection
        # « masquer les incomplètes » est réappliquée côté client sur
        # default_visible. Par défaut : 163 visibles, 9 incomplètes masquées.
        self.assertEqual(len(view["cards"]), 172)
        default_visible = [c for c in view["cards"] if c["default_visible"]]
        self.assertEqual(len(default_visible), 163)
        self.assertEqual(len(view["tag_taxonomy"]["tags"]), 26)
        self.assertEqual(len(view["families"]), 22)
        self.assertTrue(view["policy"]["note"])
        self.assertIn("collection", view["policy"])

    def test_catalogue_media_join_official(self):
        code, view = call_json("/api/catalogue")
        # 4 fiches ont une vidéo candidate dans le rattachement officiel ;
        # 3 d'entre elles sont INCOMPLETES (default_visible = False).
        with_video = {c["id"] for c in view["cards"] if c["media"]["video"]}
        self.assertEqual(
            with_video,
            {
                "ffr-carre-atelier",
                "ffr-carre2-atelier",
                "ffr-gazelles-atelier",
                "ffr-protege-atelier",
            },
        )
        # Seul le carré2 est visible par défaut.
        visible_video = {
            c["id"] for c in view["cards"] if c["media"]["video"] and c["default_visible"]
        }
        self.assertEqual(visible_video, {"ffr-carre2-atelier"})
        # La capture locale est absente dans la copie mission : indicateur honnête.
        for c in view["cards"]:
            if c["media"]["video"] is not None:
                self.assertFalse(c["media"]["local_capture"]["available"])

    def test_media_join_complete_with_incomplete_included(self):
        code, body = call_json("/api/recherche", query="include_incomplete=true")
        self.assertEqual(body["count"], 172)
        with_video = {c["id"] for c in body["cards"] if c["media"]["video"]}
        self.assertEqual(
            with_video,
            {
                "ffr-carre-atelier",
                "ffr-carre2-atelier",
                "ffr-gazelles-atelier",
                "ffr-protege-atelier",
            },
        )

    # ------------------------------------------------------------------
    # /api/recherche
    # ------------------------------------------------------------------
    def test_recherche_default_no_params(self):
        # Défaut produit (2026-11-18) : les fiches incomplètes sont
        # affichées, badge d'état à l'appui.
        code, body = call_json("/api/recherche")
        self.assertEqual(code, 200)
        self.assertEqual(body["count"], 172)
        self.assertEqual(len(body["cards"]), 172)

    def test_recherche_hide_incomplete(self):
        code, body = call_json("/api/recherche", query="include_incomplete=false")
        self.assertEqual(code, 200)
        self.assertEqual(body["count"], 163)
        self.assertEqual(len(body["cards"]), 163)

    def test_recherche_accent_insensitive(self):
        # « récupérer » accentué ou non tombe sur le même ensemble.
        expected = self._expected_search("recuperer")
        self.assertGreater(len(expected), 0)
        for q in ("recuperer", "récupérer", "RECUPERER"):
            code, body = call_json("/api/recherche", query=f"q={quote(q)}")
            self.assertEqual(code, 200)
            self.assertEqual([c["id"] for c in body["cards"]], expected, f"q={q!r}")

    def test_recherche_matches_exercise_tags_select_all(self):
        # Parité explicite sur l'ensemble visible (incomplètes masquées) :
        # le défaut produit « incomplètes affichées » est testé ailleurs.
        tag_ids = ["skill:passe", "format:surnombre"]
        expected = [e["id"] for e in tags.select(self.payload, tag_ids)]
        code, body = call_json(
            "/api/recherche",
            query="tags=skill%3Apasse,format%3Asurnombre&match=all&include_incomplete=false",
        )
        self.assertEqual(code, 200)
        self.assertEqual([c["id"] for c in body["cards"]], expected)

    def test_recherche_matches_exercise_tags_select_any(self):
        tag_ids = ["skill:passe", "format:surnombre"]
        expected = [e["id"] for e in tags.select(self.payload, tag_ids, "any")]
        code, body = call_json(
            "/api/recherche",
            query="tags=skill%3Apasse,format%3Asurnombre&match=any&include_incomplete=false",
        )
        self.assertEqual(code, 200)
        self.assertEqual([c["id"] for c in body["cards"]], expected)

    def test_recherche_matches_exercise_tags_select_incomplete(self):
        tag_ids = ["skill:plaquage"]
        expected = [e["id"] for e in tags.select(self.payload, tag_ids, include_incomplete=True)]
        self.assertEqual(expected, ["bib-plaquage-a-genoux", "bib-plaquage-balise",
                                     "bib-plaquage-soutien", "bib-plaquage-tenue",
                                     "ffr-guide-m8-1c1", "ffr-plaquage-atelier",
                                     "wr-gir-bulldog"])
        code, body = call_json(
            "/api/recherche", query="tags=skill%3Aplaquage&include_incomplete=true"
        )
        self.assertEqual(code, 200)
        self.assertEqual([c["id"] for c in body["cards"]], expected)

    def test_recherche_usage_warmup(self):
        expected = [
            e["id"]
            for e in tags.select(self.payload, session_use="WARMUP")
        ]
        self.assertEqual(len(expected), 8)
        code, body = call_json("/api/recherche", query="usage=WARMUP")
        self.assertEqual(code, 200)
        self.assertEqual(body["count"], 8)
        self.assertEqual([c["id"] for c in body["cards"]], expected)

    # ------------------------------------------------------------------
    # /api/fiches/<id>
    # ------------------------------------------------------------------
    def test_fiche_exists(self):
        code, fiche = call_json("/api/fiches/au-pop-race")
        self.assertEqual(code, 200)
        self.assertEqual(fiche["id"], "au-pop-race")
        self.assertIn("fields", fiche)
        self.assertIn("objectives", fiche["fields"])
        self.assertEqual(fiche["quality"]["state"], "DOCUMENTED_CORE")
        self.assertEqual(fiche["state"], "DOCUMENTED_CORE")

    def test_fiche_404(self):
        code, body = call_json("/api/fiches/inconnue-123")
        self.assertEqual(code, 404)
        self.assertIn("error", body)

    def test_fiche_media_video(self):
        code, fiche = call_json("/api/fiches/ffr-carre-atelier")
        self.assertEqual(code, 200)
        self.assertIsNotNone(fiche["media"]["video"])
        self.assertEqual(fiche["media"]["video"]["review_status"], "NOT_VIEWED")

    # ------------------------------------------------------------------
    # Statique
    # ------------------------------------------------------------------
    def test_static_serving(self):
        index = ROOT / "web" / "out" / "index.html"
        if not index.is_file():
            self.skipTest("web/out non construit")
        code, headers, body = call("/")
        self.assertEqual(code, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn(b"<html", body)

    def test_url_propre_resoud_vers_sa_page_html(self):
        """Régres. — /connexion renvoie la page de connexion, pas le catalogue.

        Le routage statique doit résoudre une URL propre vers <path>.html avant
        le fallback SPA ; sans cela le fallback servait index.html (le
        catalogue) au lieu du formulaire de connexion.
        """
        index = ROOT / "web" / "out" / "connexion.html"
        if not index.is_file():
            self.skipTest("web/out non construit")
        code, headers, body = call("/connexion")
        self.assertEqual(code, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn(b'"page":"/connexion"', body)
        # Pas le catalogue (le fallback SPA) : son marqueur de page est différent.
        self.assertNotIn(b'"page":"/"', body)

    def test_static_path_traversal_blocked(self):
        code, headers, body = call("/../webapp.py")
        self.assertEqual(code, 404)

    def test_head_returns_no_body(self):
        code, headers, body = call("/api/catalogue", method="HEAD")
        self.assertEqual(code, 200)
        self.assertEqual(body, b"")


class SeanceApiTests(unittest.TestCase):
    """Lot 3 — API /api/seances (trame de référence + validation).

    La trame 70/90 est servée telle quelle (gabarit de départ). La
    validation sépare les erreurs bloquantes des avertissements non
    bloquants et retourne la minutage dérivée (marge, opposition).
    """

    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads((ROOT / "exports/APPLICATION.json").read_text(encoding="utf-8"))
        cls.by_id = {e["id"]: e for e in cls.payload["exercises"]}
        cls.incomplete_id = next(
            e["id"] for e in cls.payload["exercises"] if e["quality"]["state"] == "INCOMPLETE"
        )

    def _trame(self):
        code, trame = call_json("/api/seances/trame-u8")
        self.assertEqual(code, 200)
        return json.loads(json.dumps(trame))  # copie profonde indépendante

    def test_trame_renvoit_la_reference_70_90(self):
        trame = self._trame()
        self.assertEqual(trame["duration_min"], 70)
        self.assertEqual(trame["creneau_min"], 90)
        self.assertEqual(len(trame["blocks"]), 3)
        workshops = [b for b in trame["blocks"] if b["kind"] == "WORKSHOPS"]
        self.assertEqual(len(workshops), 1)
        self.assertEqual(len(workshops[0]["rounds"]), 2)
        # Chaque exercice de rotation existe dans le vrai catalogue.
        for rnd in workshops[0]["rounds"]:
            for slot in rnd["assignments"]:
                self.assertIn(slot["variant_id"], self.by_id)

    def test_valider_trame_reference_ok(self):
        trame = self._trame()
        code, res = call_json("/api/seances/valider", data=trame, method="POST")
        self.assertEqual(code, 200)
        self.assertTrue(res["valide"])
        self.assertEqual(res["erreurs"], [])
        self.assertEqual(res["minutage"]["marge_min"], 20)
        self.assertEqual(res["minutage"]["opposition_min"], 50)
        self.assertEqual(res["minutage"]["creneau_min"], 90)
        self.assertEqual(res["minutage"]["planifie_min"], 70)

    def test_valider_avertissement_non_bloquant(self):
        # Faire dépasser le créneau produit un avertissement, pas une erreur.
        trame = self._trame()
        trame["creneau_min"] = 60  # 70 > 60 → dépassement
        code, res = call_json("/api/seances/valider", data=trame, method="POST")
        self.assertEqual(code, 200)
        self.assertTrue(res["valide"])  # non bloquant
        self.assertEqual(res["erreurs"], [])
        self.assertTrue(any("Dépassement du créneau" in a for a in res["avertissements"]))

    def test_valider_exercice_incomplet_refuse(self):
        trame = self._trame()
        slot = trame["blocks"][1]["rounds"][0]["assignments"][0]
        slot["variant_id"] = self.incomplete_id
        code, res = call_json("/api/seances/valider", data=trame, method="POST")
        self.assertEqual(code, 200)
        self.assertFalse(res["valide"])
        self.assertTrue(
            any("Exercice trop incomplet : " + self.incomplete_id in e for e in res["erreurs"])
        )

    def test_valider_exercice_inconnu_refuse(self):
        trame = self._trame()
        slot = trame["blocks"][1]["rounds"][0]["assignments"][0]
        slot["variant_id"] = "n'existe-pas-123"
        code, res = call_json("/api/seances/valider", data=trame, method="POST")
        self.assertEqual(code, 200)
        self.assertFalse(res["valide"])
        self.assertTrue(any("Exercice inconnu" in e for e in res["erreurs"]))

    def test_valider_corps_invalide_400(self):
        code, body = call_json("/api/seances/valider", data=b"{ pas du json }", method="POST")
        self.assertEqual(code, 400)
        self.assertIn("error", body)

    def test_valider_get_405(self):
        code, body = call_json("/api/seances/valider")
        self.assertEqual(code, 405)


if __name__ == "__main__":
    unittest.main()
