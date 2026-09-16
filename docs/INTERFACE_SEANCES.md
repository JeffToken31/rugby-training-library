# Cadrage proposé : préparer une séance U8

## Résultat attendu

Un éducateur prépare une séance de 90 minutes depuis son téléphone ou son ordinateur : il choisit un objectif, retrouve des exercices, répartit ses groupes, ajuste les durées puis imprime une fiche lisible sur le terrain. La séance reste modifiable sans altérer la bibliothèque.

## Trois vues suffisent

1. **Bibliothèque** : recherche, filtres combinables et cartes compactes. Chaque carte montre objectif, famille, paramètres connus et badge « documenté », « objectif proposé » ou « observation rapportée ». Les fiches insuffisantes se consultent dans une section séparée. Les exercices proches sont reliés, pas annoncés comme des nouveautés.
2. **Fiche exercice** : installation, déroulement, consignes, réussite, points coach, matériel, espace, variantes et sources. Les inconnues apparaissent clairement. Une zone « Mes réglages pour cette séance » contient effectif, durée et adaptation ; bouton Ajouter à la séance.
3. **Ma séance** : objectif, effectif du jour, éducateurs, 2 ou 3 groupes et chronologie de 90 minutes. Déplacement et duplication des blocs, trois ateliers en parallèle, rotations, pause de 10 minutes et opposition liée à l’objectif. Afficher le temps restant et les choix encore à faire. Enregistrer un brouillon, dupliquer puis imprimer.

Sur téléphone, la chronologie est verticale ; sur ordinateur, bibliothèque et séance peuvent être côte à côte. Éviter un grand tableau illisible sur petit écran. Les réglages techniques de provenance restent dans le détail, avec des libellés compréhensibles.

## Valeurs initiales proposées

30 enfants et 3 groupes de 10, modifiables ; 5 ou 6 éducateurs selon la présence. Trois rotations de 7 minutes avec 1 minute de transition. Le brouillon existant totalise exactement 90 minutes et réserve accueil, démonstration, récréation, eau, opposition et bilan. Ce sont des réglages de départ, pas des durées imposées aux fiches.

Aucun exercice incomplet injecté automatiquement. Les objectifs proposés et observations nécessitent une lecture visible ; les champs absents utiles à l’installation deviennent des questions dans la séance. Pas d’alerte technique pour chaque détail facultatif.

## MVP et limites

Inclure recherche/filtre, consultation, composition, sauvegarde de brouillons, duplication et impression. Pas de suivi individuel des enfants, convocations, messages parents ou calendrier de saison dans cette première livraison. Pas de collecte supplémentaire. Pas de génération automatique d’une séance présentée comme validée.

Proposition technique à arbitrer au cadrage : petite interface responsive consommant l’export JSON, stockage local des brouillons et export/import d’un fichier pour commencer. Si plusieurs éducateurs doivent modifier la même séance en direct, prévoir dès le départ une petite sauvegarde partagée avec accès privé ; ne pas promettre cette collaboration avec du stockage local seul.

## Décisions à prendre ensemble avant le front

- Usage principal : préparer seul puis partager une fiche, ou travailler à plusieurs sur la même séance ?
- Sortie terrain : impression papier/PDF, téléphone, ou les deux ?
- Matériel habituel et règles de contact appliquées par le club : à prévoir dans les réglages initiaux.

Ces décisions n’empêchent pas de terminer les données. Les dimensions inconnues et les situations vidéo encore incomplètes ne justifient pas de relancer une collecte générale.

## Critères de recette de l’interface

Un coach trouve une fiche en combinant thème et famille, voit l’origine d’un objectif proposé, ajoute trois ateliers et obtient un calendrier de rotations sans triple comptage du temps. Il passe de trois groupes à deux, garde un total de 90 minutes, ajuste le matériel et imprime les consignes. Un brouillon incomplet reste un brouillon ; aucune perte après sauvegarde/réouverture ; l’original documentaire reste inchangé après adaptation.
