"""Lot club (cadrage 03, A/A/A/A validé le 2026-11-20).

Le compte porte deux champs facultatifs :
- `club` : texte de ≤ 80 caractères (libellé simple, n'ouvre aucun accès) ;
- `categorie` : liste contrôlée U6…U18, Autre.

C1 inchangée : un même club pour deux comptes ne crée aucun accès croisé.
Isolement identique à test_auth_app.py (RTRL_APP_DB → base temporaire).
"""
import sqlite3
import unittest

import app_store

from test_auth_app import AuthAppTestBase, call_json, token_of

CATEGORIES = app_store.CATEGORIES


class InscriptionClubTests(AuthAppTestBase):
    """Champs facultatifs à l'inscription + retour de /api/moi."""

    def test_inscription_avec_club_et_categorie(self):
        code, body, setc = call_json(
            "/api/auth/inscription", "POST",
            data={
                "login": "coach.a",
                "password": "azerty1234",
                "club": " FC Rive ",  # les espaces bordants sont effacés
                "categorie": "U8",
            },
        )
        self.assertEqual(code, 201, body)
        self.assertEqual(body["club"], "FC Rive")
        self.assertEqual(body["categorie"], "U8")
        token = token_of(setc)
        code, moi, _ = call_json("/api/moi", cookie=token)
        self.assertEqual(code, 200)
        self.assertEqual(moi["club"], "FC Rive")
        self.assertEqual(moi["categorie"], "U8")

    def test_inscription_sans_club_renvoie_null(self):
        token = self._inscrire("coach.a")
        code, moi, _ = call_json("/api/moi", cookie=token)
        self.assertEqual(code, 200)
        self.assertIsNone(moi["club"])
        self.assertIsNone(moi["categorie"])

    def test_toutes_les_categorie_controlees_sont_acceptees(self):
        for i, cat in enumerate(CATEGORIES):
            code, body, _ = call_json(
                "/api/auth/inscription", "POST",
                data={
                    "login": f"coach.cat{i}",
                    "password": "azerty1234",
                    "categorie": cat,
                },
            )
            self.assertEqual(code, 201, f"categorie={cat!r}")
            self.assertEqual(body["categorie"], cat)

    def test_categorie_hors_liste_refusee(self):
        for cat in ("U99", "u8", "U8 ", "Adulte", ""):
            code, body, _ = call_json(
                "/api/auth/inscription", "POST",
                data={
                    "login": "coach.a",
                    "password": "azerty1234",
                    "categorie": cat,
                },
            )
            self.assertEqual(code, 400, f"categorie={cat!r}")
            self.assertIn("error", body)

    def test_club_trop_long_refuse(self):
        code, body, _ = call_json(
            "/api/auth/inscription", "POST",
            data={
                "login": "coach.a",
                "password": "azerty1234",
                "club": "c" * 81,
            },
        )
        self.assertEqual(code, 400)
        self.assertIn("error", body)
        # La borne exacte (80 caractères) passe.
        code, body, _ = call_json(
            "/api/auth/inscription", "POST",
            data={
                "login": "coach.a",
                "password": "azerty1234",
                "club": "c" * 80,
            },
        )
        self.assertEqual(code, 201, body)

    def test_club_uniquement_des_blancs_devient_absent(self):
        code, body, _ = call_json(
            "/api/auth/inscription", "POST",
            data={
                "login": "coach.a",
                "password": "azerty1234",
                "club": "   ",
            },
        )
        self.assertEqual(code, 201, body)
        self.assertIsNone(body["club"])
        # Non renvoyé par erreur : le corps reste bien un objet.
        self.assertEqual(body["login"], "coach.a")


class MigrationAncienneBaseTests(AuthAppTestBase):
    """Une base créée avant le lot (sans les 2 colonnes) est migrée à
    l'ouverture ; les comptes existants lisent club/categorie = null."""

    def _base_pre_lot(self, login="coach.old"):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "CREATE TABLE comptes ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "login TEXT NOT NULL UNIQUE, "
            "salt_hex TEXT NOT NULL, "
            "pw_hash_hex TEXT NOT NULL, "
            "created_at TEXT NOT NULL)"
        )
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute(
            "INSERT INTO comptes (login, salt_hex, pw_hash_hex, created_at) "
            "VALUES (?, ?, ?, ?)",
            (login, "ab" * 16, "cd" * 32, "2026-01-01T00:00:00Z"),
        )
        conn.commit()
        conn.close()

    def test_migration_idempotente_et_comptes_anciens_intacts(self):
        self._base_pre_lot()
        with app_store.AppStore(self.db_path) as store:
            # Le compte « pré-lot » est lisible, champs nuls.
            compte = store.get_account(1)
            self.assertIsNotNone(compte)
            self.assertEqual(compte["login"], "coach.old")
            self.assertIsNone(compte["club"])
            self.assertIsNone(compte["categorie"])
            # Un compte neuf porte les deux champs sans problème.
            neuf = store.create_account(
                "coach.neuf", "azerty1234", club="FC Rive", categorie="U10"
            )
            self.assertEqual(neuf["club"], "FC Rive")
            self.assertEqual(neuf["categorie"], "U10")
            # Réouverture : pas de double migration, pas d'erreur.
        with app_store.AppStore(self.db_path) as store:
            compte = store.get_account(1)
            self.assertIsNone(compte["club"])


class ConfidentialiteParClubsTests(AuthAppTestBase):
    """C1 inchangée (cadrage 03) : même club ≠ même espace de données."""

    def test_meme_club_ne_partage_rien(self):
        code, body_a, setc_a = call_json(
            "/api/auth/inscription", "POST",
            data={
                "login": "coach.a",
                "password": "azerty1234",
                "club": "FC Rive",
                "categorie": "U8",
            },
        )
        self.assertEqual(code, 201, body_a)
        code, body_b, setc_b = call_json(
            "/api/auth/inscription", "POST",
            data={
                "login": "coach.b",
                "password": "azerty1234",
                "club": "FC Rive",
                "categorie": "U8",
            },
        )
        self.assertEqual(code, 201, body_b)
        token_a = token_of(setc_a)
        token_b = token_of(setc_b)
        # B n'a pas accès aux brouillons de A malgré le même club…
        call_json(
            "/api/brouillons/brouillon-rive", "PUT",
            data={"titre": "Séance A", "plan": self._plan(1)}, cookie=token_a,
        )
        code, liste, _ = call_json("/api/brouillons", cookie=token_b)
        self.assertEqual(code, 200)
        self.assertEqual(liste["brouillons"], [])
        code, _, _ = call_json("/api/brouillons/brouillon-rive", cookie=token_b)
        self.assertEqual(code, 404)
        # … et les deux comptes restent bien distincts.
        code, moi_a, _ = call_json("/api/moi", cookie=token_a)
        code, moi_b, _ = call_json("/api/moi", cookie=token_b)
        self.assertEqual(moi_a["login"], "coach.a")
        self.assertEqual(moi_b["login"], "coach.b")
        self.assertEqual(moi_a["club"], moi_b["club"])


if __name__ == "__main__":
    unittest.main()
