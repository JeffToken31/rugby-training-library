"""Lot 5 — Comptes, sessions, brouillons et propositions.

Cadrage validé (02-cadrage-lot5-auth.md) :
- A1 : comptes locaux (PBKDF2-SHA256, token signé, cookie HttpOnly) ;
- B1 : brouillons et propositions rattachés au compte ;
- C1 : strictement privé (test croisé A ≠ B) ;
- D1 : snapshot de séance immuable.

Isolement : la variable d'environnement RTRL_APP_DB pointe sur un fichier
temporaire par test (base vierge à chaque test) ; la suite ne touche jamais
la base d'application réelle (data/app.sqlite).
"""
import io
import json
import os
import tempfile
import unittest
from urllib.parse import quote

import app_store
import webapp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COOKIE = app_store.COOKIE_NAME


def call(path, method="GET", query="", data=None, cookie=None):
    """Appel WSGI direct (même gabarit que test_webapp_api.py), avec cookie
    d'entrée (environ) et lecture de l'en-tête Set-Cookie de sortie."""
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
    """Token brut dans « rtrl_session=<token>; HttpOnly; … » (ou « …=; »)."""
    return set_cookie.partition("=")[2].partition(";")[0]


class AuthAppTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "data", "session-draft.example.json"), encoding="utf-8") as fh:
            cls.trame = json.load(fh)

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

    def _inscrire(self, login="coach.a", mot_de_passe="azerty1234"):
        code, body, setc = call_json(
            "/api/auth/inscription", "POST",
            data={"login": login, "password": mot_de_passe},
        )
        self.assertEqual(code, 201, body)
        self.assertIsNotNone(setc)
        return token_of(setc)

    def _plan(self, n):
        """Copie indépendante de la trame de référence, titre dédié."""
        plan = json.loads(json.dumps(self.trame))
        plan["title"] = f"Séance de test {n}"
        return plan


class CompteTests(AuthAppTestBase):
    """Critère 1 : création de compte, connexion, déconnexion."""

    def test_inscription_puis_moi(self):
        token = self._inscrire("coach.a")
        code, moi, _ = call_json("/api/moi", cookie=token)
        self.assertEqual(code, 200)
        self.assertEqual(moi["login"], "coach.a")
        self.assertTrue(moi["created_at"])

    def test_inscription_normalise_login(self):
        # Espaces et majuscules sont normalisés ; « Coach.A » a déjà pris
        # le compte une fois « coach.a » créé.
        token = self._inscrire(" Coach.A ")
        code, moi, _ = call_json("/api/moi", cookie=token)
        self.assertEqual(code, 200)
        self.assertEqual(moi["login"], "coach.a")
        code, _, _ = call_json(
            "/api/auth/inscription", "POST",
            data={"login": "COACH.A", "password": "azerty1234"},
        )
        self.assertEqual(code, 409)

    def test_inscription_mdp_trop_court(self):
        code, body, _ = call_json(
            "/api/auth/inscription", "POST",
            data={"login": "coach.a", "password": "azerty1"},  # 7 caractères
        )
        self.assertEqual(code, 400)
        self.assertIn("error", body)

    def test_inscription_login_invalides(self):
        for login in ("a", "avec espace", "x" * 33, "àccents", "-début"):
            code, _, _ = call_json(
                "/api/auth/inscription", "POST",
                data={"login": login, "password": "azerty1234"},
            )
            self.assertEqual(code, 400, f"login={login!r}")

    def test_inscription_corps_non_objet(self):
        code, body, _ = call_json("/api/auth/inscription", "POST", data=[1, 2])
        self.assertEqual(code, 400)
        self.assertIn("error", body)

    def test_login_ok(self):
        self._inscrire("coach.a")
        code, body, setc = call_json(
            "/api/auth/login", "POST",
            data={"login": "coach.a", "password": "azerty1234"},
        )
        self.assertEqual(code, 200)
        self.assertEqual(body["login"], "coach.a")
        code, moi, _ = call_json("/api/moi", cookie=token_of(setc))
        self.assertEqual(code, 200)
        self.assertEqual(moi["login"], "coach.a")

    def test_login_message_identique_compte_absent_et_mdp_erreur(self):
        # Pas de fuite : même statut et même message, que le compte existe
        # ou non (seul le mot de passe diffère).
        self._inscrire("coach.a")
        code1, corps1, _ = call_json(
            "/api/auth/login", "POST",
            data={"login": "coach.a", "password": "mauvaise123"},
        )
        code2, corps2, _ = call_json(
            "/api/auth/login", "POST",
            data={"login": "inconnu", "password": "mauvaise123"},
        )
        self.assertEqual(code1, 401)
        self.assertEqual(code2, 401)
        self.assertEqual(corps1["error"], corps2["error"])

    def test_login_corps_non_json(self):
        code, body, _ = call_json("/api/auth/login", "POST", data=b"pas du json")
        self.assertEqual(code, 400)
        self.assertIn("error", body)

    def test_deconnexion_pourvoit_la_session(self):
        token = self._inscrire("coach.a")
        code, body, setc = call_json("/api/auth/deconnexion", "POST", cookie=token)
        self.assertEqual(code, 200)
        # Le serveur est sans état (jeton signé, cadrage A1) : la déconnexion
        # se réalise par le retrait du cookie côté client (Max-Age=0), pas par
        # un retrait serveur. Un client qui ne renvoie plus de cookie n'est
        # plus identifié.
        self.assertIn("Max-Age=0", setc)
        code, _, _ = call_json("/api/moi")
        self.assertEqual(code, 401)

    def test_moi_sans_session(self):
        code, body, _ = call_json("/api/moi")
        self.assertEqual(code, 401)
        self.assertIn("error", body)

    def test_corps_trop_volumineux_413(self):
        corps = {
            "login": "coach.a",
            "password": "azerty1234",
            "remplissage": "x" * (2 * 1000 * 1000),
        }
        code, body, _ = call_json("/api/auth/inscription", "POST", data=corps)
        self.assertEqual(code, 413)
        self.assertIn("error", body)


class SessionTests(AuthAppTestBase):
    """Critère 4 (cas limites) : token tamponné, session expirée."""

    def test_token_tamponne_refuse(self):
        token = self._inscrire("coach.a")
        # On altère le dernier caractère de la signature.
        dernier = token[-1]
        alt = "0" if dernier != "0" else "1"
        faux = token[:-1] + alt
        code, _, _ = call_json("/api/moi", cookie=faux)
        self.assertEqual(code, 401)

    def test_session_expirée_refusée(self):
        token = self._inscrire("coach.a")
        with app_store.AppStore(self.db_path) as store:
            account_id = store.check_session_token(token)
            self.assertIsNotNone(account_id)
            expiré = store.make_session_token(account_id, ttl_seconds=0)
        code, _, _ = call_json("/api/moi", cookie=expiré)
        self.assertEqual(code, 401)


class BrouillonsTests(AuthAppTestBase):
    """Critères 2 et 3 : persistance par compte et confidentialité A ≠ B."""

    def test_brouillons_sans_session(self):
        for path in ("/api/brouillons", "/api/brouillons/x",
                     "/api/propositions", "/api/propositions/1"):
            code, _, _ = call_json(path)
            self.assertEqual(code, 401, path)

    def test_upsert_liste_charge_suppression(self):
        token = self._inscrire("coach.a")
        plan = self._plan(1)
        code, res, _ = call_json(
            "/api/brouillons/brouillon-1", "PUT",
            data={"titre": "Ma séance", "plan": plan}, cookie=token,
        )
        self.assertEqual(code, 200)
        self.assertEqual(res["id"], "brouillon-1")
        self.assertEqual(res["titre"], "Ma séance")
        self.assertIn("saved_at", res)
        # La liste renvoie des références légères (pas le plan complet).
        code, liste, _ = call_json("/api/brouillons", cookie=token)
        self.assertEqual(code, 200)
        self.assertEqual(len(liste["brouillons"]), 1)
        ref = liste["brouillons"][0]
        self.assertEqual(ref["id"], "brouillon-1")
        self.assertEqual(ref["titre"], "Ma séance")
        self.assertNotIn("plan", ref)
        # La lecture par identifiant renvoie le plan intégral.
        code, complet, _ = call_json("/api/brouillons/brouillon-1", cookie=token)
        self.assertEqual(code, 200)
        self.assertEqual(complet["plan"], plan)
        # L'upsert écrase le même identifiant (même liste, nouvelle valeur).
        plan2 = self._plan(2)
        call_json(
            "/api/brouillons/brouillon-1", "PUT",
            data={"titre": "Autre", "plan": plan2}, cookie=token,
        )
        code, liste2, _ = call_json("/api/brouillons", cookie=token)
        self.assertEqual(len(liste2["brouillons"]), 1)
        code, complet2, _ = call_json("/api/brouillons/brouillon-1", cookie=token)
        self.assertEqual(complet2["titre"], "Autre")
        self.assertEqual(complet2["plan"], plan2)
        # La suppression est définitive.
        code, _, _ = call_json("/api/brouillons/brouillon-1", "DELETE", cookie=token)
        self.assertEqual(code, 200)
        code, _, _ = call_json("/api/brouillons/brouillon-1", cookie=token)
        self.assertEqual(code, 404)

    def test_confidentialite_brouillons_a_ne_pas_b(self):
        token_a = self._inscrire("coach.a")
        token_b = self._inscrire("coach.b")
        plan_a = self._plan(1)
        call_json(
            "/api/brouillons/secret-a", "PUT",
            data={"titre": "A", "plan": plan_a}, cookie=token_a,
        )
        # B voit une liste vide…
        code, liste, _ = call_json("/api/brouillons", cookie=token_b)
        self.assertEqual(code, 200)
        self.assertEqual(liste["brouillons"], [])
        # … et ne peut pas lire le brouillon de A (404, pas 403).
        code, _, _ = call_json("/api/brouillons/secret-a", cookie=token_b)
        self.assertEqual(code, 404)
        # Le PUT de B avec le même identifiant crée SON brouillon
        # (espace de noms par compte)…
        plan_b = self._plan(2)
        call_json(
            "/api/brouillons/secret-a", "PUT",
            data={"titre": "B", "plan": plan_b}, cookie=token_b,
        )
        # … et le brouillon de A est intact.
        code, complet, _ = call_json("/api/brouillons/secret-a", cookie=token_a)
        self.assertEqual(code, 200)
        self.assertEqual(complet["titre"], "A")
        self.assertEqual(complet["plan"], plan_a)

    def test_brouillon_id_invalide(self):
        token = self._inscrire("coach.a")
        code, body, _ = call_json(
            "/api/brouillons/" + quote("ma/draft"), "PUT",
            data={"titre": "x", "plan": self._plan(1)}, cookie=token,
        )
        self.assertEqual(code, 400)
        self.assertIn("error", body)

    def test_brouillon_plan_invalide(self):
        token = self._inscrire("coach.a")
        code, body, _ = call_json(
            "/api/brouillons/d1", "PUT",
            data={"titre": "x", "plan": [1, 2, 3]}, cookie=token,
        )
        self.assertEqual(code, 400)
        self.assertIn("error", body)

    def test_brouillon_titre_par_défaut_du_plan(self):
        token = self._inscrire("coach.a")
        plan = self._plan(3)
        code, res, _ = call_json(
            "/api/brouillons/d-titre", "PUT",
            data={"plan": plan}, cookie=token,
        )
        self.assertEqual(code, 200)
        self.assertEqual(res["titre"], plan["title"])


class PropositionsTests(AuthAppTestBase):
    """Critères 2/3 : propositions par compte + critère D1 (snapshot)."""

    def test_proposition_validee(self):
        token = self._inscrire("coach.a")
        plan = self._plan(1)
        code, prop, _ = call_json(
            "/api/propositions", "POST",
            data={"titre": "Prop validée", "plan": plan}, cookie=token,
        )
        self.assertEqual(code, 201)
        self.assertTrue(prop["valide"])
        self.assertEqual(prop["erreurs"], [])
        self.assertEqual(prop["minutage"]["marge_min"], 20)
        self.assertEqual(prop["minutage"]["opposition_min"], 50)
        # La liste est légère ; la lecture par identifiant est complète.
        code, liste, _ = call_json("/api/propositions", cookie=token)
        self.assertEqual(len(liste["propositions"]), 1)
        self.assertNotIn("plan", liste["propositions"][0])
        code, complet, _ = call_json(f"/api/propositions/{prop['id']}", cookie=token)
        self.assertEqual(code, 200)
        self.assertEqual(complet["titre"], "Prop validée")
        self.assertTrue(complet["valide"])
        self.assertEqual(complet["plan"], plan)

    def test_proposition_non_validee_conservee(self):
        token = self._inscrire("coach.a")
        plan = self._plan(1)
        plan["blocks"][1]["rounds"][0]["assignments"][0]["variant_id"] = "n'existe-pas-123"
        code, prop, _ = call_json(
            "/api/propositions", "POST",
            data={"titre": "Prop KO", "plan": plan}, cookie=token,
        )
        self.assertEqual(code, 201)  # conservée même non valide
        self.assertFalse(prop["valide"])
        self.assertTrue(prop["erreurs"])

    def test_snapshot_immuable(self):
        token = self._inscrire("coach.a")
        plan = self._plan(1)
        original = json.loads(json.dumps(plan))
        code, prop, _ = call_json(
            "/api/propositions", "POST",
            data={"titre": "Snap", "plan": plan}, cookie=token,
        )
        self.assertEqual(code, 201)
        # L'appelant modifie ensuite SON plan local.
        plan["title"] = "Modifié après sauvegarde"
        plan["creneau_min"] = 45
        code, complet, _ = call_json(f"/api/propositions/{prop['id']}", cookie=token)
        self.assertEqual(code, 200)
        # La proposition conserve le plan d'origine, mot pour mot.
        self.assertEqual(complet["plan"], original)

    def test_confidentialite_propositions(self):
        token_a = self._inscrire("coach.a")
        token_b = self._inscrire("coach.b")
        code, prop, _ = call_json(
            "/api/propositions", "POST",
            data={"titre": "Prop A", "plan": self._plan(1)}, cookie=token_a,
        )
        self.assertEqual(code, 201)
        code, liste, _ = call_json("/api/propositions", cookie=token_b)
        self.assertEqual(code, 200)
        self.assertEqual(liste["propositions"], [])
        code, _, _ = call_json(f"/api/propositions/{prop['id']}", cookie=token_b)
        self.assertEqual(code, 404)


class MethodesTests(AuthAppTestBase):
    """Cas limites : méthodes non autorisées, corps invalides."""

    def test_methode_non_autorisee_auth(self):
        for path in ("/api/auth/inscription", "/api/auth/login"):
            code, _, _ = call_json(path)  # GET
            self.assertEqual(code, 405, path)

    def test_moi_post_non_autorise(self):
        code, _, _ = call_json("/api/moi", "POST", data={"x": 1})
        self.assertEqual(code, 405)

    def test_brouillon_post_non_autorise(self):
        token = self._inscrire("coach.a")
        code, _, _ = call_json("/api/brouillons/d1", "POST", data={"x": 1}, cookie=token)
        self.assertEqual(code, 405)

    def test_propositions_put_non_autorise(self):
        token = self._inscrire("coach.a")
        code, _, _ = call_json("/api/propositions/1", "PUT", data={"x": 1}, cookie=token)
        self.assertEqual(code, 405)


if __name__ == "__main__":
    unittest.main()
