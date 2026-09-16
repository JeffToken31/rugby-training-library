# Propositions de séances assistées par IA

Intention utilisateur confirmée : dans l’interface de création, demander une proposition selon ses attentes, puis modifier et adapter librement la séance. Ce document décrit le comportement à prévoir ; aucun service IA ou front n’est implémenté ici.

## Entrées
Objectifs et compétences souhaitées, catégorie, durée totale, effectif, groupes, éducateurs, matériel et espace disponibles, contraintes de contact du club, exercices favoris ou à exclure. Valeurs initiales : U8, 90 minutes, environ 30 enfants, 2 ou 3 groupes, 5–6 éducateurs, trois ateliers de 6–8 minutes et récréation de 10 minutes. Les paramètres sont modifiables.

## Construction
Sélectionner d’abord les fiches pertinentes par tags, qualité documentaire et contraintes. L’IA propose ensuite un brouillon référençant les identifiants existants. Elle justifie brièvement la cohérence entre objectif, échauffement, ateliers et opposition. Les neuf fiches INCOMPLETE sont exclues ; les variantes proches évitent de monopoliser une séance. Les inconnues importantes deviennent des réglages à confirmer, pas des faits inventés.

Utiliser planning_duration comme budget proposé quand présent. Préserver les durées documentaires ; une réduction ou répétition devient une adaptation explicite de séance. Une durée de manche n’est pas une durée totale. Les explications et retours inclus dans les budgets ne doivent pas être comptés une deuxième fois ; les changements de station restent à ajouter. Les groupes travaillent simultanément dans chaque rotation.

La somme des blocs doit respecter la durée demandée. Si les contraintes sont incompatibles, proposer un ajustement explicite au lieu d’un résultat faussement conforme. Le calcul est effectué et vérifié par du code, pas seulement par le texte du modèle.

## Sortie et modifications
Retourner un objet de séance structuré : statut DRAFT, objectif, groupes, blocs, rotations, identifiants des fiches, réglages choisis, origine des adaptations et décisions en attente. Conserver la version du catalogue et les descriptions utilisées. Une fiche inconnue ou trop incomplète est rejetée à la validation.

Le coach peut remplacer une activité, ajuster durée ou manches, changer les groupes, réordonner les blocs, verrouiller ce qui lui plaît et demander de régénérer uniquement le reste. Recalculer le temps après chaque modification, sans écraser les choix conservés. La sauvegarde crée une séance indépendante : aucune modification des sources.

Présenter la proposition comme un brouillon pédagogique, non comme une validation fédérale. Le coach relit et décide. La génération ne nécessite aucune donnée personnelle d’enfant.

## Décisions laissées au cadrage de l’interface
Choix du parcours de demande, niveau de détail, gestion des alternatives, sauvegarde et partage. Choix du fournisseur IA, des coûts et de l’hébergement reporté à l’implémentation ; aucune clé ni abonnement à créer pendant le travail sur les données.
