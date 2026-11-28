"""Front lot P4 « ma catégorie » sur /club (charter-workflows critère 4).

Le filtrage côté API est déjà couvert par test_club_app.py (categorie portée
à l’inscription et restituée par /api/moi) et test_joueurs_club_app.py
(magasin joueurs du club, lot P3). Ce fichier épingle le front : la vue
filtrée par catégorie avec sa bascule « tout » et la section lecture seule du
magasin joueurs — les chaînes présentes dans les sources sont les mêmes qui
sont servies dans l’export statique (build).
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def lire(chemin: str) -> str:
    return (ROOT / chemin).read_text(encoding="utf-8")


class VueMaCategorieFrontTests(unittest.TestCase):
    def test_page_club_porte_la_bascule_tout(self):
        page = lire("web/pages/club.tsx")
        self.assertIn("Voir tout le club", page)
        self.assertIn("Voir ma catégorie", page)
        self.assertIn("equipesVisibles", page)

    def test_page_club_lit_le_magasin_joueurs(self):
        page = lire("web/pages/club.tsx")
        self.assertIn("Joueurs du club", page)
        self.assertIn("listerJoueurs", page)
        # Lecture seule : pas de bouton de retrait du magasin sur /club.
        self.assertNotIn("supprimerJoueur", page)

    def test_fonction_pure_de_la_vue(self):
        vue = lire("web/lib/club-view.ts")
        self.assertIn("equipesVisibles", vue)
        # Comparaison exacte : la liste contrôlée des catégories ne tolère
        # pas de variante orthographique.
        self.assertIn("e.categorie === categorie", vue)

    def test_client_http_du_magasin_joueurs(self):
        auth = lire("web/lib/auth.ts")
        self.assertIn("listerJoueurs", auth)
        self.assertIn("/api/joueurs", auth)


if __name__ == "__main__":
    unittest.main()
