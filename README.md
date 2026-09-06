# Bibliothèque rugby U8

Première version locale pour réduire le temps de recherche des exercices.
**8 fiches (dont une piste incomplète), 7 sources.** Aucun compte joueur ni donnée enfant.

## Consulter sans installer

Ouvrir [le catalogue](exports/CATALOGUE.md) directement sur GitHub.
Chaque fiche distingue la description sourcée de l’adaptation proposée et renvoie au document original.
Le catalogue est un premier lot de validation, pas encore une bibliothèque exhaustive.

## Utiliser dans WSL

Depuis ce dossier, avec Python 3.10 ou plus, sans dépendance et sans sudo :

```sh
python3 library.py import data/seed.json
python3 library.py search passe
python3 library.py search --age M8
python3 library.py search --theme passe --minutes 10 --players 8
python3 library.py export
python3 library.py stats
python3 -m unittest discover -s tests -v
```

Les filtres numériques excluent les fiches dont la durée ou l’effectif est inconnu.
Le premier lot ne contient pas encore ces chiffres : le filtre combiné ci-dessus renverra donc zéro résultat.
Une durée de vidéo n’est jamais utilisée comme durée d’atelier.

## Fichiers

- `data/seed.json` : données éditables et réimportables.
- `data/rugby.sqlite` : base locale générée, non versionnée.
- `exports/CATALOGUE.md` : fiches lisibles sur GitHub.
- `exports/exercises.csv` et `exports/catalogue.json` : exports portables.
- `PROJECT.md` : objectif, périmètre et décisions.
- `docs/COLLECTE.md` : méthode et prochaines sources à examiner.

L’import est transactionnel et réexécutable. Un identifiant existant est actualisé.
Deux identifiants différents ne peuvent pas désigner le même emplacement dans une source.
Les similitudes entre exercices de sources différentes restent à examiner humainement.

## Limites

La collecte initiale est éditoriale, à partir de pages et sous-titres consultés.
Aucun aspirateur web ni téléchargement vidéo. Pas encore d’interface dédiée.
La classification par thème et les adaptations sont éditoriales.
La vérification documentaire ne remplace pas la validation du coach et des règles applicables.
