# Bibliothèque rugby U8

Base interne, dépôt privé, sans données enfants.

**60 fiches : 51 documentées et 9 pistes à compléter.** 40 ressources référencées et 4 trames de séance sources. Dix propositions terrain historiques restent distinctes des faits sources.

- [Choisir un exercice](exports/INDEX.md)
- [Catalogue complet](exports/CATALOGUE.md)
- [Séances sources](exports/SEANCES.md)
- [Votre proposition de séance de 90 minutes](docs/SEANCE_EXEMPLE.md)
- [Détail du nouveau lot et limites](docs/LOT_2026-09-07.md)
- [Livrable attendu et critères de réussite](docs/CONTRAT_DE_LIVRAISON.md)
- [Modèle conceptuel](docs/ARCHITECTURE.md)

## Reconstituer la base
Python standard dans WSL, sans sudo :

```sh
python3 catalogue_v2.py import data/seed.json data/ffr-2026.json data/scotland-primary.json data/rc-young-games.json data/rc-cooperation.json
python3 catalogue_v2.py enrich data/enrichment-details.json
python3 catalogue_v2.py search passe
python3 catalogue_v2.py search --status REVIEWED
python3 catalogue_v2.py export
python3 catalogue_v2.py stats
python3 -m unittest discover -s tests -v
```

Les imports identiques sont réexécutables. Une révision modifiant un identifiant existant est refusée pour éviter d'écraser une décision. Les lots complets sont conservés en base avec empreinte.

REVIEWED signifie lecture documentaire, pas validation par un coach. AI_PARSED identifie ici les pistes encore incomplètes. Les titres ne sont pas des identifiants ; plusieurs variantes peuvent partager une page source.

Les anciennes commandes library.py restent utilisables pour le premier lot uniquement. La recherche v2 combine thème, texte d’âge source, matériel, durée maximale, effectif et statut ; tri par titre, durée ou effectif. --basis proposal filtre les réglages proposés, --basis source les faits sources. Les valeurs numériques inconnues sont exclues. Utiliser catalogue_v2.py export pour conserver tous les nouveaux lots dans les exports.

La découverte de liens (discover.py) reste distincte de l'extraction d'exercices. Les archives binaires et vidéos ne sont pas publiées dans ce dépôt.

## Recherche terrain et captures
```sh
python3 catalogue_v2.py search --theme passe --minutes 7 --players 8 --basis proposal
python3 catalogue_v2.py search --material ballon --sort title
python3 capture_resources.py rc-pass-start-source
```

[État des captures et filtres](docs/COLLECTE_OPERATIONNELLE.md). Les copies brutes restent dans data/raw, ignoré par Git.

Quatre fiches disposent désormais de rubriques pédagogiques séparées. Voir [enrichissement et provenance](docs/ENRICHISSEMENT.md).

## Reconstruction complète

Depuis le dossier du projet, `python3 pipeline.py` reconstruit les données et tous les enrichissements décrits dans `data/manifest.json`, puis les exports, sans nouvelle requête réseau. Cette commande remplace l’enchaînement manuel des lots pour l’usage courant.

`python3 pipeline.py --collect --limit 20` ajoute une collecte bornée des ressources du manifeste. Les captures existantes sont réutilisées. Un échec de collecte n’empêche pas les autres ressources ni les exports. Les accès bloqués sont différés ; aucune authentification n’est automatisée.

Lire [le bilan du lot](docs/LOT_2026-09-08.md) et [la couverture des informations](exports/ETAT_COLLECTE.md). Pour vérifier : `python3 -m unittest discover -s tests -q`.
