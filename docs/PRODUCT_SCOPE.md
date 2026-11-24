# Périmètre produit

## Public et priorités

La première cible est l’éducateur U8 qui prépare sa séance ou consulte une fiche sur son téléphone. La priorité va au catalogue visuel, à la recherche, aux filtres et à la fiche atelier. Viennent ensuite la composition de séance, la sauvegarde, la réutilisation et le partage.

## Trouver et consulter un atelier

La bibliothèque actuelle compte 158 fiches, dont certaines sont des variantes ou des situations proches. Les rapprochements restent visibles et les sources sont conservées. Les [statistiques du catalogue](../exports/CATALOGUE.md#controle) décrivent le corpus livré.

Le catalogue propose la recherche textuelle et des filtres combinables par compétence et forme de jeu. Les filtres de durée, d’effectif, d’espace ou de matériel s’appuient sur les paramètres disponibles. Si une contrainte ne peut pas être vérifiée, distinguer les résultats compatibles des fiches à vérifier. Une fiche trop peu décrite reste consultable à part, hors sélection pour une séance.

La carte facilite l’accès à la fiche, au média disponible et à l’ajout à la séance. La fiche explique l’objectif, l’installation, le déroulement, les consignes, les variantes et ce que l’éducateur peut observer. Elle donne accès aux sources et aux médias disponibles. Une fiche reste utilisable sans média si sa description suffit.

La durée, l’effectif, la difficulté, le niveau de contact et l’adéquation U8 restent inconnus tant qu’ils ne sont pas établis. Distinguer les éléments documentés, les propositions et les observations rapportées. Une durée proposée pour préparer une séance ou une durée observée pour une manche garde son statut d’origine. Décrire une activité ne vaut pas validation pédagogique.

## Préparer une séance U8

Pour un créneau de 90 minutes, la trame vise **environ 50 minutes d’opposition**, avec la possibilité d’en prévoir davantage selon le terrain, et **deux ateliers pour environ 20 minutes au total**. Cela donne **environ 70 minutes planifiées et 20 minutes de marge** dans la trame de référence.

La marge absorbe les retards, l’installation, les consignes, les démonstrations, les transitions, les regroupements, l’hydratation et les imprévus. La trame est indicative et modifiable. Échauffement, jeu, pause ou transition peuvent faire partie de la séance selon les besoins. Voir le [parcours et le calcul du temps](INTERFACE_SEANCES.md).

## Sauvegarder, réutiliser et partager

- Une authentification simple des éducateurs fait partie de la V1 : elle permet d’identifier l’auteur, de conserver ses brouillons et de rattacher ses propositions à son compte.
- Un coach peut être ajouté au club **sans compte** (nom seul) ; l’attribution « quel coach gère quoi » (séance, atelier) est une donnée interne.
- Une séance incomplète peut être sauvegardée en brouillon.
- Reprendre une proposition partagée crée une nouvelle séance qui conserve un lien vers l’original. Une adaptation de durée, d’effectif ou d’organisation appartient à la séance et laisse la fiche source intacte.
- La consultation mobile est prioritaire. Les modes de partage envisagés sont le lien, le partage natif du téléphone et une fiche PDF synthétique pour le terrain. L’ordre de livraison et les accès restent à décision.
- La fiche PDF de terrain et le récapitulatif partagé ne mentionnent **pas les noms de joueurs** (minimisation : la pièce partagée porte les exercices, les durées et l’effectif, pas les personnes) ; la prévisualisation du PDF avant partage est une vue du même contenu, sans donnée supplémentaire.

## Assistance IA à terme

L’éducateur pourrait demander un brouillon à partir d’un objectif, d’un effectif, d’un créneau et de contraintes. L’assistance réutilise en priorité les fiches suffisamment décrites de la bibliothèque, par identifiant et selon leurs tags, leur provenance et les contraintes connues. Elle indique les réglages à confirmer, explique brièvement la composition et laisse l’éducateur modifier puis relire la proposition. Une proposition d’IA reste un brouillon et sa durée doit être vérifiable par le même calcul que pour une séance composée manuellement.

## Hors périmètre du MVP

La gestion des joueurs en v1.1 (décision 2026-11-24, re-tranche de la ligne rouge 5 du charter V1) est limitée aux **prénom + nom**, dans le dashboard par club et par catégorie, sans aucun autre champ : minimisation par non-collecte. Le RGPD formel (consentement du représentant légal, conservation, suppression à la sortie, DPA, incident 72 h) est reporté à la V2 (voir `v2-cadrage.md`).

Rester hors périmètre : date de naissance, données de santé, NIR, photos, coordonnées des parents, comptes joueurs, messagerie parents, présences, convocations, calendrier de saison, équipes de plateau, statistiques individuelles, notifications avancées, rôles avancés, invitations et collaboration temps réel. Les intégrations SportEasy et WhatsApp Business sont également hors périmètre.

Voir les [décisions et questions ouvertes](DECISIONS.md).
