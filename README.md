# Bibliothèque rugby U8 — base pour préparer les séances

**150 fiches conservées, 22 familles proposées, aucune collecte supplémentaire.** Ce n’est pas un décompte de jeux uniques. Dépôt privé, sans données enfants.

- [Bilan actuel des 150 fiches](exports/QUALITE_APPLICATION.md)
- [Repères pédagogiques ajoutés aux fiches](exports/AMELIORATIONS_FICHES.md)
- [Exercices par compétence et forme de jeu](exports/CATEGORIES.md)
- [Catalogue et descriptions](exports/CATALOGUE.md)
- [Cadrage du créateur de séances](docs/INTERFACE_SEANCES.md)
- [Contrat des données pour l’application](docs/CONTRAT_APPLICATION.md)
- [Rapprochements entre exercices](exports/COMPARAISONS.md)
- [Cadrage courant](PROJECT.md)

## Reconstruire et vérifier

Depuis la racine du dépôt dans WSL, Python standard uniquement :

```sh
python3 pipeline.py
python3 -m unittest discover -s tests -q
```

La reconstruction utilise les fichiers versionnés, sans réseau. Elle fonctionne aussi avec une base vierge :

```sh
python3 pipeline.py --db /tmp/rugby-rebuild.sqlite --out /tmp/rugby-exports
```

Les fichiers dans exports/ sont générés ; modifier les données d’entrée, jamais seulement un export. La base SQLite et les captures brutes sont locales et ignorées par Git. Un clone peut reconstruire les descriptions sans disposer des captures : les indicateurs de disponibilité locale ne sont pas transportables.

## Organisation

| Élément | Rôle |
|---|---|
| data/manifest.json | Ordre des lots et compléments d’application |
| catalogue_v2.py, enrichments.py | Import et historique documentaire |
| application_data.py | Vue d’application, classement, observations et audit |
| session_plan.py | Contrôles structurels des brouillons de séances |
| exports/APPLICATION.json | Contrat de lecture version 1 pour le futur front |
| data/session-draft.example.json | Brouillon de 90 minutes, rotations simultanées |
| tests/ | Reconstruction, provenance, intégrité et minutage |

La vue d’application distingue le noyau documentaire, les objectifs proposés, les observations rapportées et les descriptions insuffisantes. La présence des quatre rubriques essentielles ne vaut pas fiche exhaustive ni validation terrain. Les neuf fiches encore trop peu décrites restent consultables à part, exclues de la sélection par défaut.

Les documents LOT_* et bilans datés sont historiques. Le cadrage courant remplace leurs consignes de poursuite de collecte. Les collecteurs sont conservés pour l’historique mais ne doivent pas être lancés dans cette phase.

## Tags combinables

Les 150 fiches possèdent un classement multi-tags : 17 compétences et 10 formes de jeu. Les affectations éditoriales sont dans `data/exercise-tags.json` ; les thèmes historiques et familles restent conservés. Une fiche peut apparaître sous Passe, Soutien et Surnombre sans être dupliquée. Les neuf descriptions insuffisantes sont classées provisoirement.

```sh
python3 exercise_tags.py skill:passe format:surnombre
python3 exercise_tags.py skill:passe skill:reception --match any
python3 exercise_tags.py skill:plaquage --include-incomplete
```

Par défaut, les filtres se combinent avec ET et excluent les fiches trop incomplètes. `--match any` applique OU, toujours sans dupliquer les résultats. Les tags ne certifient pas la sécurité ou l’adéquation U8. Les effectifs, durées et matériel restent des paramètres séparés.
