"""Front lot P5 « cases de présence à l’attachement » (charter-workflows
critère 5).

Le comportement est épinglé côté TypeScript par les snapshots « p5: » de
web/scripts/replay-vectors.mts (fonctions pures de web/lib/equipes.ts). Ce
fichier épingle le câblage du front : les cases par joueur à l’attachement et
au préremplissage — les chaînes présentes dans les sources sont les mêmes qui
sont servies dans l’export statique (build). Le contrat de séance est
inchangé : les validateurs (15+8 vecteurs Python et TS) restent verts.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def lire(chemin: str) -> str:
    return (ROOT / chemin).read_text(encoding="utf-8")


class CasPresencesEquipesTests(unittest.TestCase):
    def test_fonctions_pures_de_presences(self):
        equipes = lire("web/lib/equipes.ts")
        self.assertIn("joueursCoches", equipes)
        self.assertIn("basculerPresences", equipes)
        self.assertIn("redistribuerPresences", equipes)
        # Une absence s’écrit `false` ; tout ce qui n’est pas `false` est
        # considéré présent (map vide = tous présents).
        self.assertIn("presences[n] !== false", equipes)

    def test_repartition_preserve_le_contrat(self):
        equipes = lire("web/lib/equipes.ts")
        # Seules `players` et `joueurs` sont mutées : le nom des groupes est
        # préservé par la copie, les validateurs ne lisent que `players`.
        self.assertIn("players: r.length", equipes)
        self.assertIn("roundRobinJoueurs", equipes)


class CasPresencesConstructeurTests(unittest.TestCase):
    def test_attachement_alimente_les_cases(self):
        constructeur = lire("web/components/SessionBuilder.tsx")
        # La liste complète des joueurs de l’équipe attachée est posée, sans
        # aucune absence par défaut, en mode plat (source de groupes à null).
        self.assertIn("setJoueursEquipe", constructeur)
        self.assertIn("setGroupesSource(null)", constructeur)
        self.assertIn("setPresences({})", constructeur)

    def test_cases_affichees_dans_le_bloc_equipe(self):
        constructeur = lire("web/components/SessionBuilder.tsx")
        self.assertIn("Présences —", constructeur)
        self.assertIn("type=\"checkbox\"", constructeur)
        self.assertIn("presence-item", constructeur)
        # Le compteur de présents est lisible par les lecteurs d’écran.
        self.assertIn("aria-live", constructeur)

    def test_bascule_recalcule_la_repartition(self):
        constructeur = lire("web/components/SessionBuilder.tsx")
        self.assertIn("basculerPresence", constructeur)
        self.assertIn("redistribuerPresences", constructeur)
        self.assertIn("basculerPresences", constructeur)
        # L’effectif validé suit le compte des groupes après chaque bascule.
        self.assertIn("d.players = (d.groups ?? []).reduce((a, x) => a + x.players, 0);", constructeur)

    def test_prefill_pose_les_cases(self):
        constructeur = lire("web/components/SessionBuilder.tsx")
        # Préremplissage « groupes nommés » : union ordonnée des joueurs des
        # groupes + source de répartition conservée (le joueur récoché
        # revient dans SON groupe).
        self.assertIn("setGroupesSource(groupesEquipe)", constructeur)
        self.assertIn("flatMap((ge) => ge.joueurs)", constructeur)


if __name__ == "__main__":
    unittest.main()
