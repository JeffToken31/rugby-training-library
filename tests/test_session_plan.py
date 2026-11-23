"""Batterie de minutage de la trame de référence 70/90 (décision du 17 novembre).

Les recettes proviennent de docs/INTERFACE_SEANCES.md (recettes 41 et 42) ;
la fixture catalogue est minimale car `validate` n'examine que les
identifiants référencés par le brouillon.
"""

import unittest

import session_plan


CATALOGUE = {
    "exercises": [
        {"id": "rc-pairs", "quality": {"state": "DOCUMENTED_CORE"}},
        {"id": "rc-two-one", "quality": {"state": "DOCUMENTED_CORE"}},
        {"id": "ffr-plaquage-atelier", "quality": {"state": "INCOMPLETE"}},
    ]
}


def plan():
    return {
        "id": "u8-draft-70",
        "duration_min": 70,
        "creneau_min": 90,
        "players": 14,
        "groups": [
            {"id": "A", "players": 7},
            {"id": "B", "players": 7},
        ],
        "blocks": [
            {"kind": "OPPOSITION", "label": "Opposition d'ouverture", "duration_min": 20, "variant_ids": []},
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
            {"kind": "OPPOSITION", "label": "Opposition de clôture", "duration_min": 30, "variant_ids": []},
        ],
    }


class Trame7090Tests(unittest.TestCase):
    def test_trame_referentielle_70_sur_90_est_valide(self):
        self.assertEqual(session_plan.validate(plan(), CATALOGUE), [])

    def test_fiche_incomplete_utilisable_en_seance(self):
        # Tranché 2026-11-22 : une fiche INCOMPLETE est utilisable en séance —
        # la validation passe ; l'incomplétude est déclarée (libellés fiches),
        # elle ne bloque plus. Le seul refus de référence reste l'exercice
        # inconnu du catalogue.
        p = plan()
        p["blocks"][1]["rounds"][0]["assignments"][0]["variant_id"] = "ffr-plaquage-atelier"
        self.assertEqual(session_plan.validate(p, CATALOGUE), [])

    def test_marge_derivee_jamais_stockee(self):
        p = plan()
        self.assertNotIn("marge_min", p)
        for block in p["blocks"]:
            self.assertNotIn("marge_min", block)
        self.assertEqual(p["creneau_min"] - p["duration_min"], 20)

    def test_recette_41_deux_ateliers_vingt_minutes_deux_rotations(self):
        p = plan()
        block = p["blocks"][1]
        self.assertEqual(block["duration_min"], 20)
        self.assertEqual(len(block["rounds"]), 2)
        for rotation in block["rounds"]:
            self.assertEqual(sorted(s["group_id"] for s in rotation["assignments"]), ["A", "B"])
            self.assertEqual(len({s["station_id"] for s in rotation["assignments"]}), 2)
        self.assertEqual(sum(b["duration_min"] for b in p["blocks"] if b["kind"] == "OPPOSITION"), 50)
        self.assertEqual(session_plan.validate(p, CATALOGUE), [])

    def test_recette_42_cinq_minutes_de_pause_75_planifiees_15_marge(self):
        p = plan()
        p["blocks"].insert(2, {"kind": "PAUSE", "label": "Eau et regroupement", "duration_min": 5, "variant_ids": []})
        p["duration_min"] = 75
        self.assertEqual(session_plan.validate(p, CATALOGUE), [])
        self.assertEqual(p["creneau_min"] - p["duration_min"], 15)

    def test_total_egal_creneau_sans_avertissement(self):
        p = plan()
        p["blocks"][2]["duration_min"] = 50
        p["duration_min"] = 90
        self.assertEqual(session_plan.validate(p, CATALOGUE), [])

    def test_depassement_avertissement_non_bloquant(self):
        p = plan()
        p["blocks"][2]["duration_min"] = 55
        p["duration_min"] = 95
        result = session_plan.validate(p, CATALOGUE)
        avertissements = [m for m in result if m.startswith("Avertissement")]
        self.assertEqual(len(avertissements), 1)
        self.assertIn("Dépassement du créneau : 95 min planifiées pour un créneau de 90 min", avertissements[0])

    def test_creneau_absent_erreur(self):
        p = plan()
        del p["creneau_min"]
        self.assertIn("Créneau invalide : 'creneau_min' absent ou non strictement positif.", session_plan.validate(p, CATALOGUE))

    def test_creneau_nul_erreur(self):
        p = plan()
        p["creneau_min"] = 0
        self.assertIn("Créneau invalide : 'creneau_min' absent ou non strictement positif.", session_plan.validate(p, CATALOGUE))

    def test_duree_manquante_total_partiel(self):
        p = plan()
        p["blocks"][1]["duration_min"] = None
        result = session_plan.validate(p, CATALOGUE)
        partiels = [m for m in result if "Le total est partiel" in m]
        self.assertEqual(len(partiels), 1)
        self.assertTrue(partiels[0].startswith("Avertissement"))
        self.assertNotIn("Durée totale différente de la somme des blocs", result)

    def test_total_partiel_dispense_de_l_egalite_stricte(self):
        p = plan()
        p["blocks"][2]["duration_min"] = None
        p["duration_min"] = 75
        result = session_plan.validate(p, CATALOGUE)
        self.assertEqual(len([m for m in result if "Le total est partiel" in m]), 1)
        self.assertNotIn("Durée totale différente de la somme des blocs", result)

    def test_egalite_stricte_conservee_quand_total_complet(self):
        p = plan()
        p["blocks"][1]["duration_min"] = 25
        self.assertIn("Durée totale différente de la somme des blocs", session_plan.validate(p, CATALOGUE))


class FlottantsEtMalformeTests(unittest.TestCase):
    """m1/M1 — flottants entiers normalisés (miroir front Number.isInteger) ;
    champs manquants côté plan → PlanMalforme lisible (à transformer en 400)."""

    def test_entier_normalise_flottant_entier(self):
        self.assertEqual(session_plan.entier(7), 7)
        self.assertEqual(session_plan.entier(7.0), 7)
        self.assertIsNone(session_plan.entier(7.5))
        self.assertIsNone(session_plan.entier(True))
        self.assertIsNone(session_plan.entier(None))

    def test_positive_accepte_flottant_entier_refuse_bool(self):
        self.assertTrue(session_plan.positive(7.0))
        self.assertFalse(session_plan.positive(7.5))
        self.assertFalse(session_plan.positive(True))
        self.assertFalse(session_plan.positive(0))

    def test_flottant_entier_valide_70_sur_90(self):
        p = plan()
        p["blocks"][0]["duration_min"] = 20.0
        p["duration_min"] = 70.0
        self.assertEqual(session_plan.validate(p, CATALOGUE), [])

    def test_groupe_sans_id_lance_plan_malforme(self):
        p = plan()
        del p["groups"][0]["id"]
        with self.assertRaises(session_plan.PlanMalforme):
            session_plan.validate(p, CATALOGUE)

    def test_affectation_sans_station_id_lance_plan_malforme(self):
        p = plan()
        slot = p["blocks"][1]["rounds"][0]["assignments"][0]
        del slot["station_id"]
        with self.assertRaises(session_plan.PlanMalforme):
            session_plan.validate(p, CATALOGUE)


if __name__ == "__main__":
    unittest.main()
