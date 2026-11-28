"""Magasin joueurs par club (lot P3, cadrage 05, 2026-11-26, D4).

Cadrage du lot (charter-workflows, critère 3) :
- nouvelle table `joueurs_club`, clé = nom du club (même pattern que la
  table `clubs`) — brique transitoire : l'entité club du v2 (V0) l'absorbe
  telle quelle (nom de club → club_id), rien n'est réécrit ;
- (a) le compte « gestionnaire » et un autre compte du même club voient les
  mêmes joueurs ;
- (b) un compte d'un autre club ne voit rien (compte sans club inclus) ;
- (c) joueur = prénom + nom uniquement : aucun autre champ accepté ni
  stocké (RGPD v1.1).

Contrat API :
- GET /api/joueurs → {"joueurs": [<prénom + nom>, ...]} — magasin du club
  du compte appelant (compte sans club : liste vide), ordre alphabétique
  insensible à la casse ;
- POST /api/joueurs {joueur} → 201 {club, joueur, saved_at} ; 400 si le
  compte n'a pas de club, si le nom est invalide ou si le corps n'est pas
  un objet ; 409 si un joueur de ce nom existe déjà pour le club
  (insensible à la casse : le doublon est une faute de frappe, il se
  corrige par une suppression) ; les champs supplémentaires du corps sont
  ignorés, jamais stockés ;
- DELETE /api/joueurs/<joueur> → 200 {ok: true} ; 404 si le joueur est
  inconnu du club du compte appelant (ou si le club est absent).

Isolement : même gabarit que test_coachs_app.py — RTRL_APP_DB pointe sur
un fichier temporaire par test ; la suite ne touche jamais
data/app.sqlite.
"""
import io
import json
import os
import tempfile
import unittest

import app_store
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


class JoueursClubTestBase(unittest.TestCase):
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

    def _inscrire(self, login="gest.a", club=None):
        data = {"login": login, "password": "azerty1234"}
        if club is not None:
            data["club"] = club
        code, body, setc = call_json("/api/auth/inscription", "POST", data=data)
        self.assertEqual(code, 201, body)
        self.assertIsNotNone(setc)
        return token_of(setc)


class PartageParClubTests(JoueursClubTestBase):
    """(a) deux comptes du même club voient les mêmes joueurs ; (b) un
    compte d'un autre club — ou sans club — ne voit rien."""

    def test_meme_club_meme_magasin(self):
        gestionnaire = self._inscrire("gest.a", club="RC A")
        for nom in ("Luc Martin", "Marie Dupont"):
            code, body, _ = call_json(
                "/api/joueurs", "POST", data={"joueur": nom}, cookie=gestionnaire
            )
            self.assertEqual(code, 201, body)
        coach = self._inscrire("coach.a", club="RC A")
        code, body, _ = call_json("/api/joueurs", "GET", cookie=coach)
        self.assertEqual(code, 200)
        self.assertEqual(body["joueurs"], ["Luc Martin", "Marie Dupont"])

    def test_autre_club_ne_voit_rien(self):
        gestionnaire = self._inscrire("gest.a", club="RC A")
        code, _, _ = call_json(
            "/api/joueurs", "POST", data={"joueur": "Luc Martin"}, cookie=gestionnaire
        )
        self.assertEqual(code, 201)
        autre = self._inscrire("coach.b", club="RC B")
        code, body, _ = call_json("/api/joueurs", "GET", cookie=autre)
        self.assertEqual(code, 200)
        self.assertEqual(body["joueurs"], [])

    def test_compte_sans_club_ne_voit_rien(self):
        gestionnaire = self._inscrire("gest.a", club="RC A")
        code, _, _ = call_json(
            "/api/joueurs", "POST", data={"joueur": "Luc Martin"}, cookie=gestionnaire
        )
        self.assertEqual(code, 201)
        sans_club = self._inscrire("coach.c")
        code, body, _ = call_json("/api/joueurs", "GET", cookie=sans_club)
        self.assertEqual(code, 200)
        self.assertEqual(body["joueurs"], [])

    def test_ordre_alpha_insensible_a_la_casse(self):
        token = self._inscrire("gest.a", club="RC A")
        for nom in ("Zoé Petit", "adam Durand", "Benoît Roy"):
            code, body, _ = call_json(
                "/api/joueurs", "POST", data={"joueur": nom}, cookie=token
            )
            self.assertEqual(code, 201, body)
        code, body, _ = call_json("/api/joueurs", "GET", cookie=token)
        self.assertEqual(body["joueurs"], ["adam Durand", "Benoît Roy", "Zoé Petit"])


class FormeTests(JoueursClubTestBase):
    """(c) joueur = prénom + nom uniquement : aucun autre champ accepté ni
    stocké (RGPD v1.1)."""

    def test_champs_supplementaires_ignorés(self):
        token = self._inscrire("gest.a", club="RC A")
        code, body, _ = call_json(
            "/api/joueurs", "POST",
            data={
                "joueur": "Luc Martin",
                "categorie": "U8",
                "date_naissance": "2018-01-01",
                "email": "x@y.z",
            },
            cookie=token,
        )
        self.assertEqual(code, 201, body)
        self.assertEqual(set(body), {"club", "joueur", "saved_at"})
        code, body, _ = call_json("/api/joueurs", "GET", cookie=token)
        self.assertEqual(body["joueurs"], ["Luc Martin"])

    def test_table_ne_stocke_que_club_joueur_saved_at(self):
        self._inscrire("gest.a", club="RC A")
        with app_store.AppStore(self.db_path) as store:
            colonnes = [r[1] for r in store.conn.execute("PRAGMA table_info(joueurs_club)")]
        self.assertEqual(colonnes, ["club", "joueur", "saved_at"])


class AjoutValidationTests(JoueursClubTestBase):
    """Ajout : 409 doublon par club (insensible à la casse), 400 sans
    club / nom invalide / corps non objet, 401 sans session."""

    def test_doublon_meme_club_409(self):
        token = self._inscrire("gest.a", club="RC A")
        code, _, _ = call_json(
            "/api/joueurs", "POST", data={"joueur": "Luc Martin"}, cookie=token
        )
        self.assertEqual(code, 201)
        code, body, _ = call_json(
            "/api/joueurs", "POST", data={"joueur": "luc martin"}, cookie=token
        )
        self.assertEqual(code, 409, body)

    def test_meme_nom_autre_club_accepte(self):
        club_a = self._inscrire("gest.a", club="RC A")
        club_b = self._inscrire("gest.b", club="RC B")
        code, _, _ = call_json(
            "/api/joueurs", "POST", data={"joueur": "Luc Martin"}, cookie=club_a
        )
        self.assertEqual(code, 201)
        code, _, _ = call_json(
            "/api/joueurs", "POST", data={"joueur": "Luc Martin"}, cookie=club_b
        )
        self.assertEqual(code, 201)
        # Les deux magasins restent indépendants.
        code, body, _ = call_json("/api/joueurs", "GET", cookie=club_a)
        self.assertEqual(body["joueurs"], ["Luc Martin"])

    def test_sans_club_400(self):
        token = self._inscrire("coach.c")
        code, body, _ = call_json(
            "/api/joueurs", "POST", data={"joueur": "Luc Martin"}, cookie=token
        )
        self.assertEqual(code, 400, body)

    def test_nom_invalide_400(self):
        token = self._inscrire("gest.a", club="RC A")
        for valeur in ("L", "x" * 81, 42, None):
            code, body, _ = call_json(
                "/api/joueurs", "POST", data={"joueur": valeur}, cookie=token
            )
            self.assertEqual(code, 400, body)

    def test_corps_non_objet_400(self):
        token = self._inscrire("gest.a", club="RC A")
        code, body, _ = call("/api/joueurs", "POST", data=b"[1, 2]", cookie=token)
        self.assertEqual(code, 400, body)

    def test_sans_session_401(self):
        code, body, _ = call_json("/api/joueurs", "GET")
        self.assertEqual(code, 401, body)


class SuppressionTests(JoueursClubTestBase):
    """DELETE /api/joueurs/<joueur> : 200 puis 404, insensible à la
    casse, jamais vers le magasin d'un autre club (C1)."""

    def test_suppression_200_puis_404(self):
        token = self._inscrire("gest.a", club="RC A")
        code, _, _ = call_json(
            "/api/joueurs", "POST", data={"joueur": "Luc Martin"}, cookie=token
        )
        self.assertEqual(code, 201)
        code, body, _ = call_json("/api/joueurs/Luc%20Martin", "DELETE", cookie=token)
        self.assertEqual(code, 200, body)
        self.assertEqual(body, {"ok": True})
        code, body, _ = call_json("/api/joueurs", "GET", cookie=token)
        self.assertEqual(body["joueurs"], [])
        code, body, _ = call_json("/api/joueurs/Luc%20Martin", "DELETE", cookie=token)
        self.assertEqual(code, 404, body)

    def test_suppression_insensible_a_la_casse(self):
        token = self._inscrire("gest.a", club="RC A")
        code, _, _ = call_json(
            "/api/joueurs", "POST", data={"joueur": "Luc Martin"}, cookie=token
        )
        self.assertEqual(code, 201)
        code, body, _ = call_json("/api/joueurs/luc%20martin", "DELETE", cookie=token)
        self.assertEqual(code, 200, body)

    def test_suppression_autre_club_404(self):
        club_a = self._inscrire("gest.a", club="RC A")
        club_b = self._inscrire("gest.b", club="RC B")
        code, _, _ = call_json(
            "/api/joueurs", "POST", data={"joueur": "Luc Martin"}, cookie=club_a
        )
        self.assertEqual(code, 201)
        code, body, _ = call_json("/api/joueurs/Luc%20Martin", "DELETE", cookie=club_b)
        self.assertEqual(code, 404, body)
        code, body, _ = call_json("/api/joueurs", "GET", cookie=club_a)
        self.assertEqual(body["joueurs"], ["Luc Martin"])


class MethodesTests(JoueursClubTestBase):
    """Méthodes non prévues : 405 (collection et détail), 400 si
    l'identifiant porte un segment de plus."""

    def test_put_collection_405(self):
        token = self._inscrire("gest.a", club="RC A")
        code, _, _ = call("/api/joueurs", "PUT", data={"joueur": "Luc Martin"}, cookie=token)
        self.assertEqual(code, 405)

    def test_get_detail_405(self):
        token = self._inscrire("gest.a", club="RC A")
        code, _, _ = call("/api/joueurs/Luc%20Martin", "GET", cookie=token)
        self.assertEqual(code, 405)

    def test_segment_supplementaire_400(self):
        token = self._inscrire("gest.a", club="RC A")
        code, _, _ = call("/api/joueurs/Luc%20Martin/supplementaire", "DELETE", cookie=token)
        self.assertEqual(code, 400)
