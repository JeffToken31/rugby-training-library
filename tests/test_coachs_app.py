"""Coachs sans compte (v1.1, 2026-11-24) — lot L2 du charter v1.1.

Cadrage du lot (tranché user 2026-11-24) :
- un coach sans compte est ajoutable par nom seul (2 à 80 caractères,
  club facultatif) : POST /api/coachs → 201 {id, nom, club, saved_at} ;
  409 si doublon de nom sur le même compte (insensible à la casse), 400
  si nom invalide ou corps non objet ;
- chaque compte ne gère que ses propres coachs (C1 inchangé) :
  DELETE /api/coachs/<id> → 200 {ok: true}, 404 si l'identifiant est
  inconnu ou rattaché à un autre compte ;
- « coachs disponibles » = union des comptes (nom = login, club,
  catégorie) et des coachs ajoutés par nom (login = null) : forme
  {nom, login, club, categorie} ;
- équipe : `coachs` rattachés = logins enregistrés ou noms libres,
  normalisés avec dédoublonnage (upsert_equipe) ;
- les champs de plan `coach_principal` / `blocks[].coach` sont ignorés
  par le validateur et le minutage : le replay trame-70-90 est
  inchangé.

Le replay est testé directement ici (et non ajouté à vectors.json) : le
fichier de vecteurs est la propriété du chantier en cours sur les fiches
d'opposition, qui en fait varier le nombre d'enregistrements — écart au
§8 du cadrage, journalisé.

Isolement : même gabarit que test_equipes_app.py — RTRL_APP_DB pointe sur
un fichier temporaire par test ; la suite ne touche jamais
data/app.sqlite.
"""
import copy
import io
import json
import os
import tempfile
import unittest

import app_store
import session_plan
import webapp

COOKIE = app_store.COOKIE_NAME


def call(path, method="GET", query="", data=None, cookie=None):
    """Appel WSGI direct, avec cookie d'entrée et lecture de Set-Cookie."""
    captured = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = list(headers)

    environ = {"PATH_INFO": path, "REQUEST_METHOD": method, "QUERY_STRING": query}
    if data is not None:
        raw = data if isinstance(data, (bytes, bytearray)) else json.dumps(data, ensure_ascii=False).encode("utf-8")
        environ["wsgi.input"] = io.BytesIO(raw)
        environ["CONTENT_LENGTH"] = str(len(raw))
    if cookie is not None:
        environ["HTTP_COOKIE"] = f"{COOKIE}={cookie}"
    body = b"".join(webapp.application(environ, start_response))
    code = int(captured["status"].split(" ", 1)[0])
    set_cookie = None
    for key, value in captured["headers"]:
        if key.lower() == "set-cookie" and value.partition("=")[0] == COOKIE:
            set_cookie = value
    return code, body, set_cookie


def call_json(path, method="GET", query="", data=None, cookie=None):
    code, body, set_cookie = call(path, method=method, query=query, data=data, cookie=cookie)
    return code, json.loads(body), set_cookie


def token_of(set_cookie):
    return set_cookie.partition("=")[2].partition(";")[0]


class CoachsTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmp.name, "app-test.sqlite")
        self._old_env = os.environ.get("RTRL_APP_DB")
        os.environ["RTRL_APP_DB"] = self.db_path

    def tearDown(self):
        if self._old_env is None:
            os.environ.pop("RTRL_APP_DB", None)
        else:
            os.environ["RTRL_APP_DB"] = self._old_env
        self._tmp.cleanup()

    def _compte(self, login="coach.a"):
        with app_store.AppStore(self.db_path) as store:
            return store.create_account(login, "azerty1234")["id"]

    def _inscrire(self, login="coach.a", mot_de_passe="azerty1234"):
        code, body, setc = call_json(
            "/api/auth/inscription", "POST",
            data={"login": login, "password": mot_de_passe},
        )
        self.assertEqual(code, 201, body)
        self.assertIsNotNone(setc)
        return token_of(setc)


class NomTests(CoachsTestBase):
    """normalize_coach_name : nom libre de 2 à 80 caractères, espaces
    pliés, sinon ValueError (→ 400 côté API)."""

    def test_nom_simple(self):
        self.assertEqual(app_store.normalize_coach_name("Marie Dupont"), "Marie Dupont")

    def test_espaces_plies(self):
        self.assertEqual(app_store.normalize_coach_name("  Marie   Dupont  "), "Marie Dupont")

    def test_bornes_valides(self):
        self.assertEqual(app_store.normalize_coach_name("AB"), "AB")
        self.assertEqual(app_store.normalize_coach_name("x" * 80), "x" * 80)

    def test_noms_invalides(self):
        for valeur in ("A", "x" * 81, 42, None, ["M"]):
            with self.assertRaises(ValueError):
                app_store.normalize_coach_name(valeur)


class AjoutTests(CoachsTestBase):
    def _store(self):
        return app_store.AppStore(self.db_path)

    def test_ajout_retourne_identifiants(self):
        compte_id = self._compte()
        with self._store() as store:
            c = store.ajouter_coach(compte_id, "Marie Dupont")
        self.assertEqual(set(c), {"id", "nom", "club", "saved_at"})
        self.assertEqual(c["nom"], "Marie Dupont")
        self.assertEqual(c["club"], None)
        self.assertEqual(c["id"], "marie-dupont")

    def test_ajout_avec_club(self):
        compte_id = self._compte()
        with self._store() as store:
            c = store.ajouter_coach(compte_id, "Marie Dupont", "  RC Montauban  ")
        self.assertEqual(c["club"], "RC Montauban")

    def test_club_vide_devient_null(self):
        compte_id = self._compte()
        with self._store() as store:
            c = store.ajouter_coach(compte_id, "Marie Dupont", "   ")
        self.assertIsNone(c["club"])

    def test_club_trop_long(self):
        compte_id = self._compte()
        with self._store() as store:
            with self.assertRaises(ValueError):
                store.ajouter_coach(compte_id, "Marie Dupont", "x" * 81)

    def test_doublon_nom_insensible_casse(self):
        compte_id = self._compte()
        with self._store() as store:
            store.ajouter_coach(compte_id, "Marie Dupont")
            with self.assertRaises(app_store.CoachExists):
                store.ajouter_coach(compte_id, "marie dupont")

    def test_nom_invalide(self):
        compte_id = self._compte()
        with self._store() as store:
            with self.assertRaises(ValueError):
                store.ajouter_coach(compte_id, "A")

    def test_slug_occupe_prend_suffixe(self):
        compte_id = self._compte()
        with self._store() as store:
            c1 = store.ajouter_coach(compte_id, "Marie Dupont")
            c2 = store.ajouter_coach(compte_id, "marie-dupont")
        self.assertEqual(c1["id"], "marie-dupont")
        self.assertEqual(c2["id"], "marie-dupont-2")


class SuppressionTests(CoachsTestBase):
    def _store(self):
        return app_store.AppStore(self.db_path)

    def test_suppression_ok(self):
        compte_id = self._compte()
        with self._store() as store:
            c = store.ajouter_coach(compte_id, "Marie Dupont")
            store.supprimer_coach(compte_id, c["id"])
            with self.assertRaises(ValueError):
                store.supprimer_coach(compte_id, c["id"])

    def test_suppression_inconnue(self):
        compte_id = self._compte()
        with self._store() as store:
            with self.assertRaises(ValueError):
                store.supprimer_coach(compte_id, "inconnu")

    def test_comptes_isoles(self):
        compte_a = self._compte("coach.a")
        compte_b = self._compte("coach.b")
        with self._store() as store:
            c = store.ajouter_coach(compte_a, "Marie Dupont")
            # B ne peut pas supprimer le coach d'A, même identique :
            # la clé primaire est (compte_id, id).
            with self.assertRaises(ValueError):
                store.supprimer_coach(compte_b, c["id"])


class ListeTests(CoachsTestBase):
    """Union : comptes d'abord (nom = login), puis coachs nommés
    (login = null, categorie = null), formes exactes."""

    def _store(self):
        return app_store.AppStore(self.db_path)

    def test_union_comptes_puis_nommes(self):
        compte_a = self._compte("coach.a")
        self._compte("coach.b")
        with self._store() as store:
            store.ajouter_coach(compte_a, "Zoé Martin", "RC A")
            store.ajouter_coach(compte_a, "Aa Bernard")
            coachs = store.list_coaches()
        self.assertEqual(
            coachs,
            [
                {"nom": "coach.a", "login": "coach.a", "club": None, "categorie": None},
                {"nom": "coach.b", "login": "coach.b", "club": None, "categorie": None},
                {"nom": "Aa Bernard", "login": None, "club": None, "categorie": None},
                {"nom": "Zoé Martin", "login": None, "club": "RC A", "categorie": None},
            ],
        )


class ApiAccesTests(CoachsTestBase):
    """401 sans session ; 405 sur la mauvaise méthode ; 400 sur un
    identifiant invalide."""

    def test_post_sans_session(self):
        code, body, _ = call_json("/api/coachs", method="POST", data={"nom": "A B"})
        self.assertEqual(code, 401)

    def test_delete_sans_session(self):
        code, body, _ = call_json("/api/coachs/marie-dupont", method="DELETE")
        self.assertEqual(code, 401)

    def test_put_racine_405(self):
        token = self._inscrire()
        code, body, _ = call_json("/api/coachs", method="PUT", data={"nom": "A B"}, cookie=token)
        self.assertEqual(code, 405)

    def test_put_detaill_405(self):
        token = self._inscrire()
        code, body, _ = call_json("/api/coachs/marie-dupont", method="PUT", data={}, cookie=token)
        self.assertEqual(code, 405)

    def test_identifiant_avec_barre_400(self):
        token = self._inscrire()
        code, body, _ = call_json("/api/coachs/a/b", method="DELETE", cookie=token)
        self.assertEqual(code, 400)


class ApiAjoutTests(CoachsTestBase):
    """POST /api/coachs : 201 {id, nom, club, saved_at} ; 409 doublon ;
    400 nom invalide, corps non objet ou corps illisible."""

    def test_post_201(self):
        token = self._inscrire()
        code, body, _ = call_json(
            "/api/coachs", method="POST",
            data={"nom": "Marie Dupont", "club": "RC A"}, cookie=token,
        )
        self.assertEqual(code, 201)
        self.assertEqual(set(body), {"id", "nom", "club", "saved_at"})
        self.assertEqual(body["nom"], "Marie Dupont")
        self.assertEqual(body["club"], "RC A")
        self.assertEqual(body["id"], "marie-dupont")

    def test_post_club_absent(self):
        token = self._inscrire()
        code, body, _ = call_json(
            "/api/coachs", method="POST", data={"nom": "Marie Dupont"}, cookie=token,
        )
        self.assertEqual(code, 201)
        self.assertIsNone(body["club"])

    def test_post_doublon_409(self):
        token = self._inscrire()
        code, _, _ = call_json(
            "/api/coachs", method="POST", data={"nom": "Marie Dupont"}, cookie=token,
        )
        self.assertEqual(code, 201)
        code, _, _ = call_json(
            "/api/coachs", method="POST", data={"nom": "marie dupont"}, cookie=token,
        )
        self.assertEqual(code, 409)

    def test_post_nom_court_400(self):
        token = self._inscrire()
        code, _, _ = call_json("/api/coachs", method="POST", data={"nom": "A"}, cookie=token)
        self.assertEqual(code, 400)

    def test_post_sans_nom_400(self):
        token = self._inscrire()
        code, _, _ = call_json("/api/coachs", method="POST", data={"x": 1}, cookie=token)
        self.assertEqual(code, 400)

    def test_post_corps_liste_400(self):
        token = self._inscrire()
        code, _, _ = call_json(
            "/api/coachs", method="POST", data=["Marie Dupont"], cookie=token,
        )
        self.assertEqual(code, 400)

    def test_post_corps_invalide_400(self):
        token = self._inscrire()
        code, _, _ = call_json("/api/coachs", method="POST", data=b"pas du json", cookie=token)
        self.assertEqual(code, 400)


class ApiSuppressionTests(CoachsTestBase):
    """DELETE /api/coachs/<id> : 200 {ok: true}, 404 inconnu ou rattaché
    à un autre compte (C1)."""

    def test_supprimer_le_sien_200(self):
        token = self._inscrire()
        code, coach, _ = call_json(
            "/api/coachs", method="POST", data={"nom": "Marie Dupont"}, cookie=token,
        )
        self.assertEqual(code, 201)
        code, body, _ = call_json(f"/api/coachs/{coach['id']}", method="DELETE", cookie=token)
        self.assertEqual(code, 200)
        self.assertEqual(body, {"ok": True})
        code, _, _ = call_json(f"/api/coachs/{coach['id']}", method="DELETE", cookie=token)
        self.assertEqual(code, 404)

    def test_supprimer_celui_d_autrui_404(self):
        token_a = self._inscrire("coach.a")
        token_b = self._inscrire("coach.b")
        code, coach_a, _ = call_json(
            "/api/coachs", method="POST", data={"nom": "Marie Dupont"}, cookie=token_a,
        )
        self.assertEqual(code, 201)
        # B n'a pas ce coach (même id possible, mais la clé primaire est
        # (compte_id, id)) : la tentative par B reste 404 et le coach d'A
        # est intact — A peut supprimer le sien.
        code, _, _ = call_json(f"/api/coachs/{coach_a['id']}", method="DELETE", cookie=token_b)
        self.assertEqual(code, 404)
        code, _, _ = call_json(f"/api/coachs/{coach_a['id']}", method="DELETE", cookie=token_a)
        self.assertEqual(code, 200)


class EquipeCoachsTests(CoachsTestBase):
    """Équipe : `coachs` rattachés = logins enregistrés ou noms libres,
    normalisés (upsert_equipe)."""

    def test_nom_libre_accepte(self):
        token = self._inscrire()
        code, body, _ = call_json(
            "/api/equipes", method="POST",
            data={"nom": "U8 A", "coachs": ["Marie Dupont"]}, cookie=token,
        )
        self.assertEqual(code, 201)
        self.assertEqual(body["coachs"], ["Marie Dupont"])

    def test_login_enregistre_accepte(self):
        token = self._inscrire()
        code, body, _ = call_json(
            "/api/equipes", method="POST",
            data={"nom": "U8 A", "coachs": ["coach.a"]}, cookie=token,
        )
        self.assertEqual(code, 201)
        self.assertEqual(body["coachs"], ["coach.a"])

    def test_mixte_normalise(self):
        token = self._inscrire()
        code, body, _ = call_json(
            "/api/equipes", method="POST",
            data={
                "nom": "U8 A",
                "coachs": ["coach.a", "  Marie   Dupont  ", "Marie  Dupont"],
            },
            cookie=token,
        )
        self.assertEqual(code, 201)
        self.assertEqual(body["coachs"], ["coach.a", "Marie Dupont"])

    def test_invalide_400(self):
        token = self._inscrire()
        code, _, _ = call_json(
            "/api/equipes", method="POST",
            data={"nom": "U8 A", "coachs": ["A"]}, cookie=token,
        )
        self.assertEqual(code, 400)

    def test_non_liste_400(self):
        token = self._inscrire()
        code, _, _ = call_json(
            "/api/equipes", method="POST",
            data={"nom": "U8 A", "coachs": "coach.a"}, cookie=token,
        )
        self.assertEqual(code, 400)


class ReplayPlanCoachTests(CoachsTestBase):
    """Les champs `coach_principal` / `blocks[].coach` sont ignorés par le
    validateur et le minutage : replay trame-70-90 inchangé (même leçon
    que les vecteurs, testé ici directement)."""

    def _plan(self):
        return {
            "duration_min": 70,
            "creneau_min": 90,
            "players": 14,
            "coaches": 2,
            "groups": [{"id": "A", "players": 7}, {"id": "B", "players": 7}],
            "blocks": [
                {
                    "kind": "OPPOSITION",
                    "label": "Opposition d'ouverture",
                    "duration_min": 20,
                    "variant_ids": [],
                },
                {
                    "kind": "WORKSHOPS",
                    "label": "Deux ateliers en rotation",
                    "duration_min": 20,
                    "rounds": [
                        {
                            "work_min": 10,
                            "transition_min": 0,
                            "assignments": [
                                {"group_id": "A", "station_id": "1", "variant_id": "rc-pairs"},
                                {"group_id": "B", "station_id": "2", "variant_id": "rc-two-one"},
                            ],
                        },
                        {
                            "work_min": 10,
                            "transition_min": 0,
                            "assignments": [
                                {"group_id": "A", "station_id": "2", "variant_id": "rc-two-one"},
                                {"group_id": "B", "station_id": "1", "variant_id": "rc-pairs"},
                            ],
                        },
                    ],
                },
                {
                    "kind": "OPPOSITION",
                    "label": "Opposition de clôture",
                    "duration_min": 30,
                    "variant_ids": [],
                },
            ],
        }

    def _catalogue(self):
        return {
            "exercises": [
                {"id": "rc-pairs", "quality": {"state": "DOCUMENTED_CORE"}},
                {"id": "rc-two-one", "quality": {"state": "DOCUMENTED_CORE"}},
            ]
        }

    def _resultats(self, plan):
        erreurs = session_plan.validate(plan, self._catalogue())
        bloquantes = [m for m in erreurs if not m.startswith("Avertissement")]
        avertissements = [m for m in erreurs if m.startswith("Avertissement")]
        return bloquantes, avertissements, webapp.minutage_derivee(plan)

    def test_replay_avec_coachs_inchange(self):
        plan_base = self._plan()
        plan_coach = copy.deepcopy(plan_base)
        plan_coach["coach_principal"] = "Marie Dupont"
        plan_coach["blocks"][1]["coach"] = "Marie Dupont"

        reference = self._resultats(plan_base)
        resultats = self._resultats(plan_coach)
        self.assertEqual(resultats, reference)
        self.assertEqual(reference[0], [])
        self.assertEqual(reference[1], [])
        self.assertEqual(
            reference[2],
            {
                "creneau_min": 90,
                "planifie_min": 70,
                "marge_min": 20,
                "opposition_min": 50,
                "partiel": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
