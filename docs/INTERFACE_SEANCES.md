# Interface des séances

Comportement attendu du futur constructeur. Le [contrat de lecture](CONTRAT_APPLICATION.md#exemple-structurel-et-contrôles-existants) décrit les validations disponibles aujourd’hui.

## Créer et composer

Depuis « Nouvelle séance », l’éducateur ouvre une trame U8 préremplie. Il peut préciser le titre ou la date, le créneau, l’objectif et l’effectif estimé. L’effectif, le nombre de groupes et les éducateurs s’ajustent à la présence réelle. Un objectif ou un atelier encore à choisir peut rester vide dans un brouillon.

Afficher une chronologie verticale sur téléphone. Chaque bloc s’ouvre pour régler ses paramètres. L’éducateur peut ajouter, déplacer, dupliquer ou retirer un bloc. Depuis les ateliers, il peut ouvrir la fiche, accéder au média, choisir une activité et renseigner les réglages de séance.

| Bloc | À régler selon le besoin |
| --- | --- |
| Opposition | Durée, groupes ou équipes, organisation et consigne choisie par l’éducateur. |
| Ateliers | Groupes, stations, affectations et durée par rotation. |
| Jeu | Durée, activité, organisation et équipes ou groupes. |
| Échauffement | Durée et organisation des activités ou phases. |
| Pause ou transition | Durée si elle est planifiée et note facultative. |

## Trame et calcul du temps

Sur un créneau de **90 minutes**, proposer **20 min d’opposition**, **20 min pour le bloc des deux ateliers en rotation**, puis **30 min d’opposition**. L’écran affiche **70 min planifiées**, **20 min de marge** et **50 min d’opposition**. Les valeurs suivent le [modèle U8 indicatif](PRODUCT_SCOPE.md#préparer-une-séance-u8).

| Rotation | Groupe A | Groupe B | Temps écoulé |
| --- | --- | --- | --- |
| 1 | Atelier 1 | Atelier 2 | 10 min |
| 2 | Atelier 2 | Atelier 1 | 10 min |
| **Bloc ateliers** | | | **20 min** |

Les rotations successives s’additionnent. Pendant une rotation, les affectations simultanées partagent la même durée. Toute transition explicitement planifiée compte une seule fois, dans son bloc ou comme bloc séparé. Un temps déjà compris dans un budget d’atelier reste dans ce budget. Les aléas et temps de terrain sans bloc prévu utilisent la marge.

Recalculer après chaque modification et afficher le créneau, le temps planifié, la marge ou le dépassement et le total d’opposition. Une marge réduite, une opposition plus courte que le repère U8 ou un dépassement donnent un retour informatif qui laisse le brouillon modifiable. Si une durée manque, signaler que le total est partiel et indiquer le réglage à compléter.

## Adapter, sauvegarder et reprendre

Les valeurs de l’atelier et les réglages effectués dans la séance restent identifiables. Par exemple, adapter une fiche à deux groupes de sept enregistre ce réglage dans la séance. Si la fiche ne documente pas une information utile à l’installation, afficher « À confirmer ». Les fiches trop peu décrites restent consultables dans la bibliothèque.

L’éducateur peut sauvegarder un brouillon, le rouvrir, consulter une proposition partagée et ouvrir « Créer une nouvelle proposition à partir de cette séance ». La copie garde la relation à la proposition d’origine et peut évoluer indépendamment. La vue terrain donne la chronologie, les groupes, les consignes et les réglages utiles sur téléphone. Voir le [périmètre de partage](PRODUCT_SCOPE.md#sauvegarder-réutiliser-et-partager).

## Critères de recette

- Créer la trame depuis un téléphone, y ajouter deux ateliers et obtenir 20 minutes pour deux rotations successives de 10 minutes, avec deux groupes en parallèle à chaque rotation.
- Ajouter 5 minutes de pause à la trame de référence et obtenir 75 minutes planifiées et 15 minutes de marge. Afficher un dépassement si le total excède le créneau.
- Enregistrer puis rouvrir un brouillon avec des choix en attente. Modifier l’effectif d’un atelier dans la séance et retrouver la valeur de la fiche d’origine.
- Créer une variante d’une proposition partagée. Retrouver la proposition d’origine et consulter les deux séances séparément.
