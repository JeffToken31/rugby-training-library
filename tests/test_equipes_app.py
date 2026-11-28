"""Équipes d'effectif et coachs disponibles (tranché 2026-11-22).

Cadrage du lot 3 :
- une équipe est un dispositif d'effectif rattaché au compte : nom (seul
  champ obligatoire, 1 à 80 caractères), club, catégorie, effectif et
  coachs rattachés facultatifs — les tailles varient d'un club à l'autre ;
- identifiant slug dérivé du nom (POST sans `id`), unique par compte ;
- `GET /api/coachs` liste les comptes et coachs nommés du club du
  compte appelant (lot P2, cadrage 05, 2026-11-26) ; sans club : le
  compte et ses coachs nommés — comptes : nom = login, id = null ;
  coachs nommés : login = null, id = slug (lot L4, 2026-11-25) :
  brouillons et propositions restent strictement privés (C1
  inchangé) ;
- 404, pas 403, sur les équipes d'autrui (C1).

Isolement : même gabarit que test_auth_app.py — RTRL_APP_DB pointe sur un
fichier temporaire par test ; la suite ne touche jamais data/app.sqlite.
"""
import io
import json
import os
import sqlite3
import tempfile
import unittest
from urllib.parse import quote

import app_store
import webapp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


class EquipesTestBase(unittest.TestCase):
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


class AccesTests(EquipesTestBase):
    """401 sans session ; 405 sur la mauvaise méthode ; 400 sur un identifiant
    invalide ; 404, pas 403, sur les équipes d'autrui (C1)."""

    def test_coachs_401_sans_session(self):
        code, body, _ = call_json("/api/coachs")
        self.assertEqual(code, 401)
        self.assertIn("Authentification", body["error"])

    def test_equipes_401_sans_session(self):
        code, body, _ = call_json("/api/equipes")
        self.assertEqual(code, 401)
        code, body, _ = call_json("/api/equipes/u8", method="DELETE")
        self.assertEqual(code, 401)

    def test_coachs_405_methode_inconnue(self):
        # POST et DELETE sont devenus des méthodes valides de l'API (v1.1 :
        # coachs sans compte) ; seule une méthode réellement inconnue est 405.
        token = self._inscrire()
        code, body, _ = call_json("/api/coachs", method="PUT", data={"x": 1}, cookie=token)
        self.assertEqual(code, 405)

    def test_identifiant_invalide_400(self):
        token = self._inscrire()
        code, body, _ = call_json("/api/equipes/bad id", cookie=token)
        self.assertEqual(code, 400)
        code, body, _ = call_json("/api/equipes/" + "a" * 129, cookie=token)
        self.assertEqual(code, 400)

    def test_equipe_autrui_404_pas_403(self):
        token_a = self._inscrire("coach.a")
        token_b = self._inscrire("coach.b")
        code, eq, _ = call_json("/api/equipes", "POST", data={"nom": "U8 A"}, cookie=token_a)
        self.assertEqual(code, 201)
        code, body, _ = call_json(f"/api/equipes/{eq['id']}", cookie=token_b)
        self.assertEqual(code, 404)
        self.assertIn("introuvable", body["error"])


class CreationTests(EquipesTestBase):
    """POST : nom obligatoire (seul champ requis), slug automatique,
    contrôles de club / catégorie / effectif / coachs."""

    def test_creation_slug_auto_dans_nom(self):
        token = self._inscrire()
        code, eq, _ = call_json(
            "/api/equipes", "POST", data={"nom": "U8 Étoiles"}, cookie=token
        )
        self.assertEqual(code, 201, eq)
        self.assertEqual(eq["id"], "u8-etoiles")
        self.assertEqual(eq["nom"], "U8 Étoiles")
        self.assertIsNone(eq["club"])
        self.assertIsNone(eq["categorie"])
        self.assertIsNone(eq["effectif"])
        self.assertEqual(eq["coachs"], [])
        self.assertTrue(eq["saved_at"])

    def test_creation_slug_collision_suffise(self):
        token = self._inscrire()
        code, eq1, _ = call_json("/api/equipes", "POST", data={"nom": "U8"}, cookie=token)
        code, eq2, _ = call_json("/api/equipes", "POST", data={"nom": "u8"}, cookie=token)
        self.assertEqual(code, 201)
        self.assertEqual(eq1["id"], "u8")
        self.assertEqual(eq2["id"], "u8-2")

    def test_creation_slug_vide_tombe_sur_equipe(self):
        token = self._inscrire()
        # Nom qui ne laisse aucun caractère alphanumérique après le fold :
        # le slug de secours « equipe » est utilisé.
        code, eq, _ = call_json("/api/equipes", "POST", data={"nom": "!!!"}, cookie=token)
        self.assertEqual(code, 201, eq)
        self.assertEqual(eq["id"], "equipe")

    def test_creation_nom_requis(self):
        token = self._inscrire()
        for data in ({}, {"club": "RC Test"}, {"nom": "   "}, {"nom": 42}):
            code, body, _ = call_json("/api/equipes", "POST", data=data, cookie=token)
            self.assertEqual(code, 400, data)
            self.assertIn("Nom d'équipe requis", body["error"])

    def test_creation_nom_trop_long(self):
        token = self._inscrire()
        code, body, _ = call_json(
            "/api/equipes", "POST", data={"nom": "É" * 81}, cookie=token
        )
        self.assertEqual(code, 400)

    def test_creation_categorie_invalide(self):
        token = self._inscrire()
        code, body, _ = call_json(
            "/api/equipes", "POST",
            data={"nom": "U8", "categorie": "U99"}, cookie=token,
        )
        self.assertEqual(code, 400)
        self.assertIn("Catégorie", body["error"])

    def test_creation_categorie_valide(self):
        token = self._inscrire()
        for cat in app_store.CATEGORIES:
            code, eq, _ = call_json(
                "/api/equipes", "POST",
                data={"nom": f"U8 {cat}", "categorie": cat}, cookie=token,
            )
            self.assertEqual(code, 201, cat)
            self.assertEqual(eq["categorie"], cat)

    def test_creation_effectif_invalide(self):
        token = self._inscrire()
        for effectif in (-1, True, "10", 2.5, [3]):
            code, body, _ = call_json(
                "/api/equipes", "POST",
                data={"nom": "U8", "effectif": effectif}, cookie=token,
            )
            self.assertEqual(code, 400, effectif)
            self.assertIn("Effectif", body["error"])

    def test_creation_effectif_zero_et_absent(self):
        token = self._inscrire()
        code, eq, _ = call_json(
            "/api/equipes", "POST", data={"nom": "U8", "effectif": 0}, cookie=token
        )
        self.assertEqual(code, 201)
        self.assertEqual(eq["effectif"], 0)
        code, eq, _ = call_json("/api/equipes", "POST", data={"nom": "U9"}, cookie=token)
        self.assertEqual(code, 201)
        self.assertIsNone(eq["effectif"])

    def test_creation_club_trop_long(self):
        token = self._inscrire()
        code, body, _ = call_json(
            "/api/equipes", "POST",
            data={"nom": "U8", "club": "C" * 81}, cookie=token,
        )
        self.assertEqual(code, 400)

    def test_creation_coachs_normalises_sans_duplis(self):
        token = self._inscrire()
        code, eq, _ = call_json(
            "/api/equipes", "POST",
            data={"nom": "U8", "coachs": [" Coach.A ", "coach.a", "coach.b"]},
            cookie=token,
        )
        self.assertEqual(code, 201, eq)
        self.assertEqual(eq["coachs"], ["coach.a", "coach.b"])

    def test_creation_coachs_format_invalide(self):
        # v1.1 : « bad login! » serait désormais un nom de coach valide
        # (2 à 80 caractères) ; « A » (1 caractère) est invalide en login
        # comme en nom libre.
        token = self._inscrire()
        for coachs in ("coach.a", ["A"], [None]):
            code, body, _ = call_json(
                "/api/equipes", "POST", data={"nom": "U8", "coachs": coachs},
                cookie=token,
            )
            self.assertEqual(code, 400, coachs)

    def test_creation_corps_non_objet(self):
        token = self._inscrire()
        code, body, _ = call_json("/api/equipes", "POST", data=["U8"], cookie=token)
        self.assertEqual(code, 400)


class MiseAJourTests(EquipesTestBase):
    """PUT = mise à jour complète : un champ absent est remis à absent ;
    PUT sur un identifiant inconnu crée l'équipe (upsert)."""

    def test_put_remplacement_complet(self):
        token = self._inscrire()
        code, eq, _ = call_json(
            "/api/equipes", "POST",
            data={"nom": "U8", "club": "RC Test", "effectif": 14,
                  "categorie": "U8", "coachs": ["coach.b"]},
            cookie=token,
        )
        self.assertEqual(code, 201)
        code, eq2, _ = call_json(
            f"/api/equipes/{eq['id']}", "PUT",
            data={"nom": "U8 bis", "categorie": "U8"}, cookie=token,
        )
        self.assertEqual(code, 200, eq2)
        self.assertEqual(eq2["nom"], "U8 bis")
        self.assertIsNone(eq2["club"])
        self.assertIsNone(eq2["effectif"])
        self.assertEqual(eq2["coachs"], [])
        code, recu, _ = call_json(f"/api/equipes/{eq['id']}", cookie=token)
        self.assertEqual(code, 200)
        self.assertEqual(recu, eq2)

    def test_put_cree_si_absente(self):
        token = self._inscrire()
        code, eq, _ = call_json(
            "/api/equipes/nouvelle", "PUT", data={"nom": "Nouvelle"}, cookie=token
        )
        self.assertEqual(code, 200, eq)
        self.assertEqual(eq["nom"], "Nouvelle")

    def test_put_invalide_400(self):
        token = self._inscrire()
        code, eq, _ = call_json("/api/equipes", "POST", data={"nom": "U8"}, cookie=token)
        self.assertEqual(code, 201)
        code, body, _ = call_json(
            f"/api/equipes/{eq['id']}", "PUT", data={"nom": 3}, cookie=token
        )
        self.assertEqual(code, 400)

    def test_get_inconnue_404(self):
        token = self._inscrire()
        code, body, _ = call_json("/api/equipes/nulle", cookie=token)
        self.assertEqual(code, 404)

    def test_delete_puis_404(self):
        token = self._inscrire()
        code, eq, _ = call_json("/api/equipes", "POST", data={"nom": "U8"}, cookie=token)
        self.assertEqual(code, 201)
        code, body, _ = call_json(f"/api/equipes/{eq['id']}", "DELETE", cookie=token)
        self.assertEqual(code, 200)
        self.assertEqual(body, {"ok": True})
        code, body, _ = call_json(f"/api/equipes/{eq['id']}", cookie=token)
        self.assertEqual(code, 404)
        # Suppression idempotente : encore 200.
        code, body, _ = call_json(f"/api/equipes/{eq['id']}", "DELETE", cookie=token)
        self.assertEqual(code, 200)

    def test_liste_ne_contient_que_mon_compte(self):
        token_a = self._inscrire("coach.a")
        token_b = self._inscrire("coach.b")
        call_json("/api/equipes", "POST", data={"nom": "Équipe A"}, cookie=token_a)
        call_json("/api/equipes", "POST", data={"nom": "Équipe B"}, cookie=token_b)
        code, body, _ = call_json("/api/equipes", cookie=token_a)
        self.assertEqual(code, 200)
        self.assertEqual([e["nom"] for e in body["equipes"]], ["Équipe A"])


class CoachsTests(EquipesTestBase):
    """GET /api/coachs : liste filtrée par le club du compte appelant
    (lot P2, cadrage 05, 2026-11-26) — comptes du même club (nom =
    login) et coachs nommés du club / du compte (login = null, id =
    slug — lot L4, 2026-11-25) ; identifiants et rattachements seuls —
    aucune donnée de brouillon ou proposition (C1 inchangé). L'API
    complète est couverte par test_coachs_app.py."""

    def test_liste_filtree_par_club(self):
        # Lot P2 (cadrage 05, 2026-11-26) : la liste est filtrée par le
        # club du compte appelant — l'union globale inter-clubs n'est plus
        # restituée (couvert en détail par test_coachs_app.py).
        token_a = self._inscrire("coach.a")
        code, _, setc_b = call_json(
            "/api/auth/inscription", "POST",
            data={"login": "coach.b", "password": "azerty1234",
                  "club": "RC B", "categorie": "U8"},
        )
        self.assertEqual(code, 201)
        token_b = token_of(setc_b)
        code, body, _ = call_json("/api/coachs", cookie=token_a)
        self.assertEqual(code, 200)
        # coach.a sans club : lui-même seul — coach.b (club RC B) n'est
        # plus restitué.
        self.assertEqual([c["nom"] for c in body["coachs"]], ["coach.a"])
        # coach.b (club RC B) : lui-même seul — coach.a n'appartient pas
        # au club RC B et n'y a pas de coach nommé.
        code, body, _ = call_json("/api/coachs", cookie=token_b)
        self.assertEqual(code, 200)
        self.assertEqual(
            body["coachs"],
            [
                {"nom": "coach.b", "login": "coach.b", "club": "RC B", "categorie": "U8",
                 "id": None},
            ],
        )


    def test_champs_exacts_sans_fuites(self):
        token = self._inscrire("coach.a")
        code, body, _ = call_json("/api/coachs", cookie=token)
        self.assertEqual(code, 200)
        for c in body["coachs"]:
            self.assertEqual(set(c), {"nom", "login", "club", "categorie", "id"})

    def test_club_et_categorie_facultatifs(self):
        token = self._inscrire()
        code, body, _ = call_json("/api/coachs", cookie=token)
        self.assertEqual(code, 200)
        self.assertEqual(body["coachs"][0]["club"], None)
        self.assertEqual(body["coachs"][0]["categorie"], None)


class SchemaTests(EquipesTestBase):
    """Sur une base créée avant la table `equipes` (base existante), la
    première ouverture ajoute la table sans perte de données ; l'ouverture
    répéter ne crée pas en double (CREATE TABLE IF NOT EXISTS)."""

    def test_base_existante_premiere_ouverture(self):
        conn = sqlite3.connect(self.db_path)
        conn.executescript(
            "CREATE TABLE comptes ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " login TEXT NOT NULL UNIQUE,"
            " salt_hex TEXT NOT NULL,"
            " pw_hash_hex TEXT NOT NULL,"
            " created_at TEXT NOT NULL,"
            " club TEXT,"
            " categorie TEXT);"
        )
        conn.execute(
            "INSERT INTO comptes (login, salt_hex, pw_hash_hex, created_at, club, categorie)"
            " VALUES ('coach.existant', 'aa', 'bb', '2026-01-01T00:00:00Z', 'RC Test', 'U8')"
        )
        conn.commit()
        conn.close()
        with app_store.AppStore(self.db_path) as store:
            noms = [r[0] for r in store.conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
            self.assertIn("equipes", noms)
            self.assertEqual(store.list_equipes(1), [])
            compte = store.get_account(1)
            self.assertEqual(compte["login"], "coach.existant")
        # Seconde ouverture : rien de cassé, la table existe toujours.
        with app_store.AppStore(self.db_path) as store:
            self.assertEqual(store.list_equipes(1), [])


class JoueursTests(EquipesTestBase):
    """Lot L3 (v1.1, 2026-11-24) : liste de joueurs sur l'équipe — prénom +
    nom, trim + espaces internes pliés, dédoublonnage insensible à la casse
    (la première occurrence gagne) ; PUT sans `joueurs` → vide (mise à
    jour complète)."""

    def test_creation_joueurs_echo_normalises(self):
        token = self._inscrire()
        code, eq, _ = call_json(
            "/api/equipes", "POST",
            data={"nom": "U8",
                  "joueurs": [" Léa  Martin ", "léa martin", "Noah Dupont"]},
            cookie=token,
        )
        self.assertEqual(code, 201, eq)
        self.assertEqual(eq["joueurs"], ["Léa Martin", "Noah Dupont"])

    def test_creation_sans_joueurs_vide(self):
        token = self._inscrire()
        code, eq, _ = call_json("/api/equipes", "POST", data={"nom": "U8"}, cookie=token)
        self.assertEqual(code, 201)
        self.assertEqual(eq["joueurs"], [])
        code, recu, _ = call_json(f"/api/equipes/{eq['id']}", cookie=token)
        self.assertEqual(code, 200)
        self.assertEqual(recu["joueurs"], [])

    def test_creation_joueurs_non_liste_400(self):
        token = self._inscrire()
        code, body, _ = call_json(
            "/api/equipes", "POST",
            data={"nom": "U8", "joueurs": "Léa Martin"}, cookie=token,
        )
        self.assertEqual(code, 400)

    def test_creation_joueurs_element_invalide_400(self):
        token = self._inscrire()
        for joueurs in ([42], [None], ["A"], ["Léa " + "x" * 80]):
            code, body, _ = call_json(
                "/api/equipes", "POST",
                data={"nom": "U8", "joueurs": joueurs}, cookie=token,
            )
            self.assertEqual(code, 400, joueurs)

    def test_put_sans_joueurs_remis_vide(self):
        token = self._inscrire()
        code, eq, _ = call_json(
            "/api/equipes", "POST",
            data={"nom": "U8", "joueurs": ["Noah Dupont"]}, cookie=token,
        )
        self.assertEqual(code, 201)
        self.assertEqual(eq["joueurs"], ["Noah Dupont"])
        code, eq2, _ = call_json(
            f"/api/equipes/{eq['id']}", "PUT",
            data={"nom": "U8"}, cookie=token,
        )
        self.assertEqual(code, 200, eq2)
        self.assertEqual(eq2["joueurs"], [])

    def test_put_joueurs_invalide_400(self):
        token = self._inscrire()
        code, eq, _ = call_json("/api/equipes", "POST", data={"nom": "U8"}, cookie=token)
        self.assertEqual(code, 201)
        code, body, _ = call_json(
            f"/api/equipes/{eq['id']}", "PUT",
            data={"nom": "U8", "joueurs": ["A"]}, cookie=token,
        )
        self.assertEqual(code, 400)


class MigrationJoueursTests(EquipesTestBase):
    """Sur une base créée avant le lot L3 (table `equipes` sans
    `joueurs_json`), la première ouverture ajoute la colonne sans perte de
    données (migration idempotente, `app_store._migrate_equipes`)."""

    def test_base_existante_ajout_colonne_sans_perte(self):
        conn = sqlite3.connect(self.db_path)
        conn.executescript(
            "CREATE TABLE comptes ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " login TEXT NOT NULL UNIQUE,"
            " salt_hex TEXT NOT NULL,"
            " pw_hash_hex TEXT NOT NULL,"
            " created_at TEXT NOT NULL,"
            " club TEXT,"
            " categorie TEXT);"
            "CREATE TABLE equipes ("
            " id TEXT NOT NULL,"
            " compte_id INTEGER NOT NULL,"
            " nom TEXT NOT NULL,"
            " club TEXT,"
            " categorie TEXT,"
            " effectif INTEGER,"
            " coachs_json TEXT NOT NULL DEFAULT '[]',"
            " saved_at TEXT NOT NULL,"
            " PRIMARY KEY (compte_id, id));"
        )
        conn.execute(
            "INSERT INTO comptes (login, salt_hex, pw_hash_hex, created_at, club, categorie)"
            " VALUES ('coach.existant', 'aa', 'bb', '2026-01-01T00:00:00Z', 'RC Test', 'U8')"
        )
        conn.execute(
            "INSERT INTO equipes (id, compte_id, nom, club, categorie, effectif, coachs_json, saved_at)"
            " VALUES ('u8', 1, 'U8', 'RC Test', 'U8', 14, '[\"coach.b\"]', '2026-01-01T00:00:00Z')"
        )
        conn.commit()
        conn.close()
        with app_store.AppStore(self.db_path) as store:
            colonnes = {row[1] for row in store.conn.execute("PRAGMA table_info(equipes)")}
            self.assertIn("joueurs_json", colonnes)
            eq = store.get_equipe(1, "u8")
            self.assertEqual(eq["nom"], "U8")
            self.assertEqual(eq["coachs"], ["coach.b"])
            self.assertEqual(eq["joueurs"], [])
        # Seconde ouverture : rien de cassé (idempotence).
        with app_store.AppStore(self.db_path) as store:
            self.assertEqual(store.list_equipes(1)[0]["joueurs"], [])


class GroupesTests(EquipesTestBase):
    """Lot peaufinage C (2026-11-25) : groupes nommés librement de l'équipe
    — {nom, joueurs} ; le nom est un texte libre de 2 à 80 caractères ; les
    joueurs d'un groupe doivent appartenir à l'effectif de l'équipe (insensible
    à la casse) et un joueur n'appartient qu'à un seul groupe (doublons
    intra-groupe et inter-groupes rejetés) ; PUT sans `groupes` → vide
    (mise à jour complète, comme les autres champs)."""

    def _creer(self, token, joueurs=None, groupes=None):
        corps = {"nom": "U8"}
        if joueurs is not None:
            corps["joueurs"] = joueurs
        if groupes is not None:
            corps["groupes"] = groupes
        code, eq, _ = call_json("/api/equipes", "POST", data=corps, cookie=token)
        self.assertEqual(code, 201, eq)
        return eq

    def test_creation_groupes_disjoints_dans_effectif(self):
        token = self._inscrire()
        eq = self._creer(
            token,
            joueurs=["Léa Martin", "Noah Dupont", "Chloé Petit", "Tom Bernard"],
            groupes=[
                {"nom": "Bleus", "joueurs": ["Léa Martin", "Noah Dupont"]},
                {"nom": "Rouges", "joueurs": ["Chloé Petit"]},
            ],
        )
        self.assertEqual(
            eq["groupes"],
            [
                {"nom": "Bleus", "joueurs": ["Léa Martin", "Noah Dupont"]},
                {"nom": "Rouges", "joueurs": ["Chloé Petit"]},
            ],
        )
        # Persistance : le GET renvoie les mêmes groupes.
        code, recu, _ = call_json(f"/api/equipes/{eq['id']}", cookie=token)
        self.assertEqual(code, 200)
        self.assertEqual(recu["groupes"], eq["groupes"])

    def test_creation_sans_groupes_vide_par_defaut(self):
        token = self._inscrire()
        eq = self._creer(token, joueurs=["Léa Martin"])
        self.assertEqual(eq["groupes"], [])

    def test_groupe_nom_normalise_et_casse_insensible(self):
        token = self._inscrire()
        eq = self._creer(
            token,
            joueurs=["Léa Martin"],
            # « LÉA MARTIN » : mêmes caractères que l'effectif, seule la
            # casse diffère — `casefold` ignore la casse (pas les accents).
            groupes=[{"nom": "  Bleus  ", "joueurs": ["LÉA MARTIN"]}],
        )
        # Nom de groupe normalisé (trim) ; joueur reconnu dans l'effectif
        # sans tenir compte de la casse (le nom stocké est celui saisi).
        self.assertEqual(eq["groupes"][0]["nom"], "Bleus")
        self.assertEqual(eq["groupes"][0]["joueurs"], ["LÉA MARTIN"])

    def test_put_sans_groupes_remis_vide(self):
        token = self._inscrire()
        eq = self._creer(
            token,
            joueurs=["Léa Martin"],
            groupes=[{"nom": "Bleus", "joueurs": ["Léa Martin"]}],
        )
        code, eq2, _ = call_json(
            f"/api/equipes/{eq['id']}", "PUT", data={"nom": "U8"}, cookie=token
        )
        self.assertEqual(code, 200, eq2)
        self.assertEqual(eq2["groupes"], [])

    def test_put_groupes_met_a_jour(self):
        token = self._inscrire()
        eq = self._creer(token, joueurs=["Léa Martin", "Noah Dupont"])
        self.assertEqual(eq["groupes"], [])
        code, eq2, _ = call_json(
            f"/api/equipes/{eq['id']}", "PUT",
            data={
                "nom": "U8",
                "joueurs": ["Léa Martin", "Noah Dupont"],
                "groupes": [{"nom": "Vert", "joueurs": ["Noah Dupont"]}],
            },
            cookie=token,
        )
        self.assertEqual(code, 200, eq2)
        self.assertEqual(eq2["groupes"], [{"nom": "Vert", "joueurs": ["Noah Dupont"]}])

    def test_groupe_joueur_hors_effectif_400(self):
        token = self._inscrire()
        code, body, _ = call_json(
            "/api/equipes", "POST",
            data={
                "nom": "U8",
                "joueurs": ["Léa Martin"],
                "groupes": [{"nom": "Bleus", "joueurs": ["Étranger X"]}],
            },
            cookie=token,
        )
        self.assertEqual(code, 400)
        self.assertIn("effectif", body["error"])

    def test_joueur_dans_deux_groupes_400(self):
        token = self._inscrire()
        code, body, _ = call_json(
            "/api/equipes", "POST",
            data={
                "nom": "U8",
                "joueurs": ["Léa Martin", "Noah Dupont"],
                "groupes": [
                    {"nom": "Bleus", "joueurs": ["Léa Martin"]},
                    {"nom": "Rouges", "joueurs": ["Léa Martin"]},
                ],
            },
            cookie=token,
        )
        self.assertEqual(code, 400)
        self.assertIn("un joueur au plus dans un groupe", body["error"])

    def test_doublon_intra_groupe_400(self):
        token = self._inscrire()
        code, body, _ = call_json(
            "/api/equipes", "POST",
            data={
                "nom": "U8",
                "joueurs": ["Léa Martin", "Noah Dupont"],
                "groupes": [
                    {
                        "nom": "Bleus",
                        "joueurs": ["Léa Martin", "léa martin"],
                    }
                ],
            },
            cookie=token,
        )
        self.assertEqual(code, 400)

    def test_nom_groupe_invalide_400(self):
        token = self._inscrire()
        for nom in (None, "", "A", "B" * 81):
            code, body, _ = call_json(
                "/api/equipes", "POST",
                data={"nom": "U8", "groupes": [{"nom": nom, "joueurs": []}]},
                cookie=token,
            )
            self.assertEqual(code, 400, nom)

    def test_groupes_non_liste_400(self):
        token = self._inscrire()
        code, body, _ = call_json(
            "/api/equipes", "POST",
            data={"nom": "U8", "groupes": "Bleus"}, cookie=token,
        )
        self.assertEqual(code, 400)

    def test_groupe_non_objet_400(self):
        token = self._inscrire()
        code, body, _ = call_json(
            "/api/equipes", "POST",
            data={"nom": "U8", "groupes": ["Bleus"]}, cookie=token,
        )
        self.assertEqual(code, 400)

    def test_joueurs_groupe_non_liste_400(self):
        token = self._inscrire()
        code, body, _ = call_json(
            "/api/equipes", "POST",
            data={
                "nom": "U8",
                "joueurs": ["Léa Martin"],
                "groupes": [{"nom": "Bleus", "joueurs": "Léa Martin"}],
            },
            cookie=token,
        )
        self.assertEqual(code, 400)


class MigrationGroupesTests(EquipesTestBase):
    """Sur une base créée avant le lot peaufinage C (table `equipes` avec
    `joueurs_json` mais sans `groupes_json`), la première ouverture ajoute la
    colonne sans perte de données (migration idempotente,
    `app_store._migrate_equipes`)."""

    def test_base_existante_ajout_colonne_sans_perte(self):
        conn = sqlite3.connect(self.db_path)
        conn.executescript(
            "CREATE TABLE comptes ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " login TEXT NOT NULL UNIQUE,"
            " salt_hex TEXT NOT NULL,"
            " pw_hash_hex TEXT NOT NULL,"
            " created_at TEXT NOT NULL,"
            " club TEXT,"
            " categorie TEXT);"
            "CREATE TABLE equipes ("
            " id TEXT NOT NULL,"
            " compte_id INTEGER NOT NULL,"
            " nom TEXT NOT NULL,"
            " club TEXT,"
            " categorie TEXT,"
            " effectif INTEGER,"
            " coachs_json TEXT NOT NULL DEFAULT '[]',"
            " joueurs_json TEXT NOT NULL DEFAULT '[]',"
            " saved_at TEXT NOT NULL,"
            " PRIMARY KEY (compte_id, id));"
        )
        conn.execute(
            "INSERT INTO comptes (login, salt_hex, pw_hash_hex, created_at, club, categorie)"
            " VALUES ('coach.existant', 'aa', 'bb', '2026-01-01T00:00:00Z', 'RC Test', 'U8')"
        )
        conn.execute(
            "INSERT INTO equipes (id, compte_id, nom, club, categorie, effectif, "
            "coachs_json, joueurs_json, saved_at) "
            "VALUES ('u8', 1, 'U8', 'RC Test', 'U8', 14, '[\"coach.b\"]', "
            "'[\"Léa Martin\", \"Noah Dupont\"]', '2026-01-01T00:00:00Z')"
        )
        conn.commit()
        conn.close()
        with app_store.AppStore(self.db_path) as store:
            colonnes = {row[1] for row in store.conn.execute("PRAGMA table_info(equipes)")}
            self.assertIn("groupes_json", colonnes)
            eq = store.get_equipe(1, "u8")
            # Les joueurs existants sont conservés ; les groupes sont vides.
            self.assertEqual(eq["joueurs"], ["Léa Martin", "Noah Dupont"])
            self.assertEqual(eq["coachs"], ["coach.b"])
            self.assertEqual(eq["groupes"], [])
        # Seconde ouverture : rien de cassé (idempotence).
        with app_store.AppStore(self.db_path) as store:
            eq = store.get_equipe(1, "u8")
            self.assertEqual(eq["joueurs"], ["Léa Martin", "Noah Dupont"])
            self.assertEqual(eq["groupes"], [])


if __name__ == "__main__":
    unittest.main()
