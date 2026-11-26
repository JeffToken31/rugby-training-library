"""Épingle le lot P6 (charter-workflows, critère 6) : étiquettes UI
« votre club » (compte sans catégorie) / « votre catégorie » (compte avec)
sur la carte d’en-tête de /club, et l’aide sous le champ club à l’inscription.
Exécuté : wsl python3 -m unittest discover -s tests -q
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def lire(chemin: str) -> str:
    return (ROOT / chemin).read_text(encoding="utf-8")


class EtiquettesVueClub(unittest.TestCase):
    def test_ternaire_votre_categorie_ou_votre_club(self):
        src = lire("web/pages/club.tsx")
        self.assertIn("moi.categorie ? \"Votre catégorie\" : \"Votre club\"", src)

    def test_classe_club_view_dans_la_page_et_le_css(self):
        self.assertIn("className=\"club-view\"", lire("web/pages/club.tsx"))
        self.assertIn(".club-view", lire("web/styles/globals.css"))

    def test_label_dans_le_bloc_connecte_apres_verifie_et_moi(self):
        src = lire("web/pages/club.tsx")
        self.assertLess(
            src.index("verifie && moi ?"), src.index("className=\"club-view\"")
        )


class AideChampClubInscription(unittest.TestCase):
    def test_aide_dans_le_label_du_champ_club(self):
        src = lire("web/pages/connexion.tsx")
        self.assertIn("Club (facultatif)", src)
        self.assertIn("className=\"connexion-aide\"", src)
        self.assertIn("rejoindre le même espace", src)

    def test_classe_connexion_aide_dans_le_css(self):
        self.assertIn(".connexion-aide", lire("web/styles/globals.css"))


if __name__ == "__main__":
    unittest.main()
