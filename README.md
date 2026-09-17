# Bibliothèque rugby U8 — base pour préparer les séances

**158 fiches conservées, 22 familles proposées, dont huit nouvelles activités d’échauffement.** Ce n’est pas un décompte de jeux uniques. Dépôt privé, sans données enfants.

**[Ouvrir le catalogue complet](exports/CATALOGUE.md)**

Toutes les fiches, catégories, durées, repères coach, adaptations, sources et rapprochements sont réunis dans ce catalogue. Les anciennes vues séparées redirigent vers ses sections. Les fiches individuelles contiennent le même contenu pour un partage direct.

Pour le cadrage et le développement : [interface](docs/INTERFACE_SEANCES.md), [génération IA](docs/GENERATION_SEANCES_IA.md), [contrat des données](docs/CONTRAT_APPLICATION.md), [priorité actuelle](PROJECT.md). Les rapports LOT_* sont des archives de travail, pas le parcours de lecture courant.

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

Les fiches possèdent un classement multi-tags : 17 compétences et 10 formes de jeu. Les affectations éditoriales sont dans `data/exercise-tags.json` ; les thèmes historiques et familles restent conservés. Une fiche peut apparaître sous Passe, Soutien et Surnombre sans être dupliquée. Les neuf descriptions insuffisantes sont classées provisoirement.

```sh
python3 exercise_tags.py skill:passe format:surnombre
python3 exercise_tags.py skill:passe skill:reception --match any
python3 exercise_tags.py skill:plaquage --include-incomplete
```

Par défaut, les filtres se combinent avec ET et excluent les fiches trop incomplètes. `--match any` applique OU, toujours sans dupliquer les résultats. Les tags ne certifient pas la sécurité ou l’adéquation U8. Les effectifs, durées et matériel restent des paramètres séparés.

## Échauffements collectés
[Accéder directement aux échauffements dans le catalogue](exports/CATALOGUE.md#echauffements). L’usage WARMUP est attesté par les ressources consultées ; l’étape proposée (mise en mouvement, mobilité, préparation spécifique) reste un classement éditorial. Recherche combinable : `python3 exercise_tags.py --usage WARMUP`. Les autres fiches sans usage qualifié ne sont pas déclarées impropres à l’échauffement.
