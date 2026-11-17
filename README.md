# Rugby Training Library

Pour reprendre le projet, commencer par [PROJECT.md](PROJECT.md). Ce guide sert à consulter le catalogue et à le reconstruire localement.

**[Ouvrir le catalogue complet](exports/CATALOGUE.md)**

Toutes les fiches, catégories, durées, repères coach, adaptations, sources et rapprochements sont réunis dans ce catalogue. Les anciennes vues séparées redirigent vers ses sections. Les fiches individuelles contiennent le même contenu pour un partage direct.

Le [catalogue livré](exports/CATALOGUE.md#controle) compte 158 fiches, 22 familles proposées et huit échauffements. Le nombre de fiches inclut des variantes.

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

Les fichiers dans [exports/](exports/) sont générés depuis les entrées versionnées. Pour corriger le corpus, modifier les entrées et régénérer les sorties. La base SQLite et les captures brutes sont locales et ignorées par Git. Un clone peut reconstruire les descriptions sans les captures. Les indicateurs de disponibilité locale dépendent de la machine.

## Organisation

| Élément | Rôle |
|---|---|
| [data/manifest.json](data/manifest.json) | Ordre des lots et compléments d’application |
| [catalogue_v2.py](catalogue_v2.py), [enrichments.py](enrichments.py) | Import et historique documentaire dans SQLite |
| [application_data.py](application_data.py) | Vue d’application, classement, observations et audit |
| [session_plan.py](session_plan.py) | Contrôles structurels des brouillons de séances |
| [exports/APPLICATION.json](exports/APPLICATION.json) | Vue JSON de lecture v1 pour le futur front |
| [data/session-draft.example.json](data/session-draft.example.json) | Exemple structurel de la trame 70/90 utilisé dans les tests. Voir le [contrat](docs/CONTRAT_APPLICATION.md#exemple-structurel-et-contrôles-existants) |
| [tests/](tests/) | Reconstruction, provenance, intégrité et minutage |

Les bilans datés et les anciennes missions de collecte sont recensés dans l’[inventaire des archives](archive/README.md).

## Tags combinables

Les fiches possèdent des tags combinables, répartis en 17 compétences et 9 formes de jeu dans l’export actuel. Les affectations éditoriales sont dans `data/exercise-tags.json` ; les thèmes historiques et familles restent conservés. Une fiche peut apparaître sous Passe, Soutien et Surnombre sans être dupliquée. Les neuf descriptions insuffisantes sont classées provisoirement.

```sh
python3 exercise_tags.py skill:passe format:surnombre
python3 exercise_tags.py skill:passe skill:reception --match any
python3 exercise_tags.py skill:plaquage --include-incomplete
```

Par défaut, les filtres se combinent avec ET et excluent les fiches trop incomplètes. `--match any` applique OU, toujours sans dupliquer les résultats. Les tags ne certifient pas la sécurité ou l’adéquation U8. Les effectifs, durées et matériel restent des paramètres séparés.

## Échauffements collectés
L’étiquette WARMUP signale les situations publiées comme échauffements. Les étapes « mise en mouvement », « mobilité » et « préparation spécifique » relèvent du classement éditorial. [Échauffements dans le catalogue](exports/CATALOGUE.md#echauffements). Recherche combinable : `python3 exercise_tags.py --usage WARMUP`. Les autres fiches sans usage qualifié ne sont pas déclarées impropres à l’échauffement.
