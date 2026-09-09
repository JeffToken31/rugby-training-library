# Bibliothèque rugby U8
Référence de cadrage : mise à jour utilisateur du 7 septembre 2026, détaillée dans [ARCHITECTURE](docs/ARCHITECTURE.md).

Référence opérationnelle complémentaire : [CONTRAT_DE_LIVRAISON](docs/CONTRAT_DE_LIVRAISON.md). Clarification utilisateur : cible finale = très grande base d'exercices et interface riche pour rechercher, trier, filtrer et préparer les séances, priorité U8. Le nombre de fiches déjà collectées ne constitue ni un plafond ni un corpus à compléter entièrement avant tout ajout. Faire progresser collecte nouvelle, richesse des données et outils ensemble. Ne pas confondre taille du catalogue et qualité.

Priorité absolue : une grosse base structurée d'exercices U8, consultable rapidement par quelques coachs. L'exercice et ses variantes sont au centre ; les ressources alimentent et justifient les fiches. Construire progressivement une interface de consultation et de préparation fondée sur le modèle de données ; la richesse des filtres et des fiches fait partie du produit final.

Technique : Python standard + SQLite, dans WSL sous jeff, sans sudo. Dépôt GitHub privé JeffToken31/rugby-training-library. Aucune donnée enfant, aucun secret. Notifications de cette application ; le test n'a pas produit de son chez l'utilisateur.

Terrain confirmé : environ 30 enfants (à ajuster au démarrage), 5–6 éducateurs, séance de 90 minutes, 2 ou 3 groupes selon présence, trois ateliers de 6–8 minutes, échauffement, opposition reliée aux objectifs, récréation de 10 minutes et temps de consigne. Matériel encore inconnu, non bloquant pour le modèle.

État au 8 septembre : 105 fiches (96 documentées et 9 pistes incomplètes), 62 ressources référencées, quatre trames de séance sources. 87 fiches avec au moins un champ enrichi ; 54 ressources conservées localement. La commande python3 pipeline.py reconstruit le catalogue depuis data/manifest.json, applique tous les enrichissements, contrôle les relations et produit les exports sans réseau. Ajouter --collect pour une collecte bornée. Voir docs/LOT_2026-09-08.md. Les captures locales ne sont pas transportées par Git ; leur présence est vérifiée séparément des références d’empreinte. Suite : diversifier les sources U8, enrichir les autres fiches, organiser les familles ; consultation à reprendre après la priorité de collecte. Les révisions successives d’enrichissement sont disponibles avec historique et provenance par champ ; l’interface reste à développer.

Autonomie : chercher avant de solliciter ; questions uniquement pour authentification, permission, dépense, décision irréversible ou véritable arbitrage fonctionnel/pédagogique. Ne pas réclamer une validation de chaque import. Les propositions IA restent identifiées ; seul un coach peut valider pédagogiquement.

Dernier complément : trois situations Scottish Rugby avec pages PDF vérifiées ; collecte bornée donnant priorité aux ressources encore non capturées. Voir docs/LOT_ECOSSE_2026-09-08.md.

Comparaisons consultables : exports/COMPARAISONS.md expose les rapprochements enregistrés avec les règles de chaque fiche ; aucune fusion automatique.

La collecte couvre désormais toutes les ressources du manifeste. L’état exporté conserve la dernière tentative par ressource, même après reconstruction hors réseau. Capture et extraction pédagogique restent distinctes.

Enrichissement des archives : trois fiches mieux détaillées et objectif seul pour rc-ten. La page FFR échauffement ne contient pas de description exploitable des situations ; vidéo à examiner séparément.

Accès aux comptes : utilisateur disponible pour se connecter lui-même aux sites utiles. Présenter le site et le blocage concret ; ne pas demander de mot de passe. RugbyCoaching affiche LOG IN dans le navigateur au 8 septembre ; connexion proposée pour vérifier les vidéos manquantes. Les refus robots, délais dépassés et textes incomplets ne prouvent pas un besoin de compte.

Autonomie confirmée : enchaîner les lots sans demander de relance. Compte RugbyCoaching connecté dans le navigateur ; aucune extraction de cookies ni de mot de passe vers le collecteur public. Dernier lot : docs/LOT_CONTINU_2026-09-08.md.

World Rugby : deux situations sans contact avec durée et effectif par atelier. Le périmètre de l’effectif apparaît dans la fiche et le CSV pour éviter de confondre cinq joueurs par atelier et trente au total.

Reprise automatique actualisée le 8 septembre : toutes les cinq minutes, au lieu de trente ; enchaîner les lots complets et ne solliciter que pour une intervention nécessaire. Trois fiches U7 Rugby Toolbox ajoutées avec captures : binômes guidés, chasse collective et opposition sans ballon.

Consultation : exports/FICHES_DETAILLEES.md sélectionne les fiches disposant d’une organisation et d’un déroulement sourcés. Recherche par présence de champs, origine et organisme disponible ; 36 tests.

## Priorité confirmée par l’utilisateur
La grosse base avant l’interface. Concentrer le travail sur des lots conséquents d’exercices U8 réellement décrits et sur les champs utiles aux coachs. Mettre le développement de l’interface en attente. Modifier les outils seulement pour débloquer la collecte ou fiabiliser les données. Poursuivre les sources accessibles lorsqu’une autre bloque ; solliciter uniquement une intervention précise.

## Cadrage V1 du 9 septembre
Viser environ 200 variantes U8 réellement exploitables, sans gonfler les comptes. Commencer à examiner la couverture vers 150. Le statut documentaire seul ne mesure pas l’utilisabilité terrain. Suivre par lot les nouvelles variantes, familles, doublons, enrichissements et ressources bloquées. Mesurer la saturation sur 30 à 50 ressources pertinentes ; sous 15–20 % de nouveauté, cibler les lacunes. Finir un lot ouvert avant de rechercher ailleurs. Exploiter les sources riches déjà connues avant une découverte générale. Front toujours en attente.

Dernier lot clos : trois variantes World Rugby et neuf fiches FFR enrichies. Voir docs/LOT_FFR_WR_2026-09-09.md. Les neuf fiches FFR restent incomplètes : organisation vidéo non vérifiée.

Lots enchaînés du 9 septembre : références secondaires attribuées, variante communautaire enrichie, trois situations World Rugby, trois comparaisons et contrôle des 51 archives. Voir docs/LOTS_CONTINUS_2026-09-09.md.

## Priorité exclusive : classement et dédoublonnage
Décision utilisateur du 9 septembre : suspendre nouvelle collecte et interface ; traiter tout le corpus existant. Le classement de data/classification-audit.json est une proposition documentaire, distincte des affectations historiques. Conserver chaque source et ne fusionner aucun cas incertain. Produire un décompte des candidats, fiches composites et descriptions insuffisantes ; ne pas annoncer un nombre d’exercices uniques non démontré.

Audit des cas signalés terminé : 91 affectations, 11 rapprochements et 11 fiches exceptionnelles examinés. Voir exports/CLASSEMENT.md. Les décisions de conservation sont documentées ; elles ne certifient pas l’unicité. Ne pas recommencer cet audit ni relancer la collecte généraliste. Suite éventuelle de la même tâche : obtenir les preuves vidéo précisément listées, puis réviser seulement les cas concernés.

## Collecte reprise sur instruction utilisateur
La nouvelle collecte est de nouveau autorisée. Privilégier les lots documentés ; conserver le classement, écarter les doublons et ne jamais présenter le nombre de fiches comme un nombre certifié de jeux uniques.

Lot demandé de dix fiches livré : docs/LOT_DIX_2026-09-09.md. Catalogue 105, toutes les nouvelles fiches classées dans les familles proposées.
