"""Lot L1 (cadrage 06, 2026-11-27) — suggestions des clubs à l'inscription.

- `AppStore.list_clubs` : noms distincts de la table comptes, non vides,
  strip, dé-doublonnés casefold (accents comptent — même règle
  d'orthographe que partout dans l'app), ordre alphabétique ;
- `GET /api/clubs` : endpoint **public** (le formulaire d'inscription
  s'utilise sans session), forme {clubs: [...]}, 405 sinon ;
- aucune donnée personnelle livrée : les noms de club seuls.

Isolement identique à test_auth_app.py (RTRL_APP_DB → base temporaire).
"""
import unittest

import app_store

from test_auth_app import AuthAppTestBase, call_json


class StoreListClubsTests(AuthAppTestBase):
    """Comportement de AppStore.list_clubs sur la table comptes."""

    def test_base_vide_liste_vide(self):
        with app_store.AppStore(self.db_path) as store:
            self.assertEqual(store.list_clubs(), [])

    def test_clubs_vides_et_absents_exclus(self):
        with app_store.AppStore(self.db_path) as store:
            store.create_account("coach.a", "azerty1234")           # sans club
            store.create_account("coach.b", "azerty1234", club="   ")  # → NULL
            store.create_account("coach.c", "azerty1234", club="FC Rive")
            self.assertEqual(store.list_clubs(), ["FC Rive"])

    def test_strip_et_ordre_alphabetique(self):
        with app_store.AppStore(self.db_path) as store:
            store.create_account("coach.a", "azerty1234", club="  Zèbre  ")
            store.create_account("coach.b", "azerty1234", club="Aubagne")
            store.create_account("coach.c", "azerty1234", club="Chalon")
            self.assertEqual(store.list_clubs(), ["Aubagne", "Chalon", "Zèbre"])

    def test_dedoublonnage_casefold_premier_compte_gagne(self):
        # « FC Rive » puis « fc rive » : même club (casefold), une seule
        # occurrence, libellé du premier compte (ordre id).
        with app_store.AppStore(self.db_path) as store:
            store.create_account("coach.a", "azerty1234", club="FC Rive")
            store.create_account("coach.b", "azerty1234", club="fc rive")
            self.assertEqual(store.list_clubs(), ["FC Rive"])

    def test_accents_comptent(self):
        # Même règle d'orthographe que le reste de l'app : les accents ne
        # sont pas effacés — « FC Rivé » est un autre libellé.
        with app_store.AppStore(self.db_path) as store:
            store.create_account("coach.a", "azerty1234", club="FC Rive")
            store.create_account("coach.b", "azerty1234", club="FC Rivé")
            self.assertEqual(store.list_clubs(), ["FC Rive", "FC Rivé"])


class ApiClubsTests(AuthAppTestBase):
    """GET /api/clubs : public, forme {clubs: [...]}, 405 sinon."""

    def _inscrire_club(self, login, club):
        code, body, _ = call_json(
            "/api/auth/inscription", "POST",
            data={"login": login, "password": "azerty1234", "club": club},
        )
        self.assertEqual(code, 201, body)

    def test_public_sans_session(self):
        self._inscrire_club("coach.a", "FC Rive")
        # Pas de cookie : le formulaire d'inscription s'utilise sans
        # session, c'est le cas d'usage du datalist.
        code, body, _ = call_json("/api/clubs")
        self.assertEqual(code, 200)
        self.assertEqual(body, {"clubs": ["FC Rive"]})

    def test_liste_vide_si_aucun_club(self):
        code, body, _ = call_json("/api/clubs")
        self.assertEqual(code, 200)
        self.assertEqual(body, {"clubs": []})

    def test_dedoublonne_et_trie(self):
        self._inscrire_club("coach.a", "FC Rive")
        self._inscrire_club("coach.b", "fc rive")
        self._inscrire_club("coach.c", "Aubagne")
        code, body, _ = call_json("/api/clubs")
        self.assertEqual(code, 200)
        self.assertEqual(body["clubs"], ["Aubagne", "FC Rive"])

    def test_post_refuse_405(self):
        code, body, _ = call_json("/api/clubs", "POST", data={})
        self.assertEqual(code, 405)

    def test_pas_de_donnees_personnelles(self):
        """Le corps ne livre que les noms de club : pas de login, mot de
        passe, catégorie ou autre champ des comptes."""
        self._inscrire_club("coach.a", "FC Rive")
        code, body, _ = call_json("/api/clubs")
        self.assertEqual(code, 200)
        self.assertEqual(set(body), {"clubs"})
        self.assertNotIn("coach.a", str(body))


if __name__ == "__main__":
    unittest.main()
