# Bibliothèque rugby U8

Base interne d'exercices pour préparer les entraînements. Dépôt privé, sans données enfants.

## Consulter
- [Index par thème et fiches individuelles](exports/INDEX.md)
- [Catalogue complet](exports/CATALOGUE.md)
- [Proposition de séance de 90 minutes](docs/SEANCE_EXEMPLE.md)
- [Nouveau cadrage et modèle conceptuel](docs/ARCHITECTURE.md)

Le lot historique contient 33 fiches et 26 ressources référencées. Dix fiches comportent des propositions terrain U8 séparées des faits sources. Ces propositions ne sont pas validées par un coach. Les 73 liens candidats découverts ne sont pas 73 exercices qualifiés.

## Utiliser dans WSL
Python 3.10+, sans dépendance ni sudo :

```sh
python3 library.py import data/seed.json
python3 library.py search passe
python3 library.py search --theme passe --basis proposal --players 8 --minutes 8
python3 library.py export
python3 library.py stats
python3 -m unittest discover -s tests -v
```

Les filtres numériques excluent les inconnues. Par défaut ils portent sur les chiffres sources ; --basis proposal utilise les réglages U8 proposés. Une durée vidéo n'est jamais une durée d'atelier.

## Transition du modèle
Le catalogue utilise encore le schéma historique. Le prototype schema/v2.sql prépare les familles, variantes, ressources, occurrences, séances, assertions et rapprochements. Il est testé séparément ; la migration et le branchement de la recherche restent à faire. Les titres ne seront jamais des identifiants et les similitudes ne provoqueront pas de suppressions automatiques.

data/seed.json conserve les données éditables ; les exports sont reproductibles. discover.py repère des liens publics et conserve les erreurs d'accès dans data/discovery.json ; il ne réalise pas encore le pipeline complet d'extraction. Voir [la collecte](docs/COLLECTE.md).
