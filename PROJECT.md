# Bibliothèque rugby U8
Référence de cadrage : mise à jour utilisateur du 7 septembre 2026, détaillée dans [ARCHITECTURE](docs/ARCHITECTURE.md).

Référence opérationnelle complémentaire : [CONTRAT_DE_LIVRAISON](docs/CONTRAT_DE_LIVRAISON.md). Clarification utilisateur : cible finale = très grande base d'exercices et interface riche pour rechercher, trier, filtrer et préparer les séances, priorité U8. Le nombre de fiches déjà collectées ne constitue ni un plafond ni un corpus à compléter entièrement avant tout ajout. Faire progresser collecte nouvelle, richesse des données et outils ensemble. Ne pas confondre taille du catalogue et qualité.

Priorité absolue : une grosse base structurée d'exercices U8, consultable rapidement par quelques coachs. L'exercice et ses variantes sont au centre ; les ressources alimentent et justifient les fiches. Construire progressivement une interface de consultation et de préparation fondée sur le modèle de données ; la richesse des filtres et des fiches fait partie du produit final.

Technique : Python standard + SQLite, dans WSL sous jeff, sans sudo. Dépôt GitHub privé JeffToken31/rugby-training-library. Aucune donnée enfant, aucun secret. Notifications de cette application ; le test n'a pas produit de son chez l'utilisateur.

Terrain confirmé : environ 30 enfants (à ajuster au démarrage), 5–6 éducateurs, séance de 90 minutes, 2 ou 3 groupes selon présence, trois ateliers de 6–8 minutes, échauffement, opposition reliée aux objectifs, récréation de 10 minutes et temps de consigne. Matériel encore inconnu, non bloquant pour le modèle.

État au 16 septembre : 150 fiches (141 documentées et 9 pistes incomplètes), 87 ressources référencées, quatre trames de séance sources. 137 fiches avec au moins un champ enrichi ; 62 ressources conservées localement. La commande python3 pipeline.py reconstruit le catalogue depuis data/manifest.json, applique tous les enrichissements, contrôle les relations et produit les exports sans réseau. Ajouter --collect pour une collecte bornée. Voir docs/LOT_2026-09-08.md. Les captures locales ne sont pas transportées par Git ; leur présence est vérifiée séparément des références d’empreinte. Suite : diversifier les sources U8, enrichir les autres fiches, organiser les familles ; consultation à reprendre après la priorité de collecte. Les révisions successives d’enrichissement sont disponibles avec historique et provenance par champ ; l’interface reste à développer.

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

Lot demandé de vingt fiches livré : docs/LOT_VINGT_2026-09-09.md. 125 fiches classées, dont 90 avec organisation, déroulement et consignes. Prioriser ensuite les situations collectives avec ballon.

Cadrage autonome du 10 septembre : docs/CADRAGE_AUTONOME_2026-09-10.md. Lot docs/LOT_QUALITE_2026-09-10.md : 12 objectifs sourcés ajoutés et 3 situations collectives, total 128 fiches ; 93 avec organisation, déroulement et consignes.

Vingt fiches supplémentaires livrées le 10 septembre : docs/LOT_VINGT_2026-09-10.md. Total 148 ; 113 avec organisation, déroulement et consignes. Captures nouvelles bloquées (429 Rugby Australia, 403 robots School Games), sans preuve de compte nécessaire. Préparer le bilan de couverture au voisinage de 150.

Bilan du 13 septembre : docs/BILAN_COUVERTURE_148.md et data/coverage-20260913.json. Douze objectifs World Rugby ajoutés ; 82 fiches réunissent objectif, organisation, déroulement et consignes. Priorité suivante : critères de réussite sourcés et situations collectives décisionnelles réellement nouvelles ; pas de reprise généraliste des chasses déjà abondantes.

Lot observations du 13 septembre : docs/LOT_OBSERVATIONS_2026-09-13.md. Quatorze fiches enrichies, 50 avec points coach ; 148 fiches au total. Prochaine collecte : exploiter les cartes Imagine Rugby déjà identifiées pour situations collectives nouvelles, en évitant les chasses et passes déjà présentes.

Lot Imagine du 14 septembre : docs/LOT_IMAGINE_2026-09-14.md ; 149 fiches. Recueil direct 403, une carte débutant extraite du texte indexé. Ne pas recompter le nid, proche de au-nest-pass.

Seuil de 150 fiches le 16 septembre : docs/BILAN_COUVERTURE_150.md. 84 fiches réunissent les quatre champs essentiels. Une variante de passes en profondeur ajoutée ; poursuite ciblée de la qualité et des situations collectives, front en attente.

Rectification du 16 septembre : imagine-depth-running est un doublon probable de wr-chain-reaction ; nouveauté non démontrée. Six fiches enrichies en critères de réussite, soit 20 au total. Voir docs/LOT_CRITERES_2026-09-16.md.

Lot progressions : docs/LOT_PROGRESSIONS_2026-09-16.md. Quinze fiches World Rugby complétées avec les réglages de difficulté sourcés, sans nouvelle fiche. 53 fiches avec points coach.

Lot Rugby Toolbox : docs/LOT_NZ_ESSENTIELS_2026-09-16.md. Cinq fiches complétées ; 89/150 avec les quatre champs essentiels, dont les 24 fiches néo-zélandaises. Validation terrain toujours distincte.

Lot objectifs RugbyCoaching : docs/LOT_RC_OBJECTIFS_2026-09-16.md. Quatre objectifs explicites ajoutés ; 93/150 fiches avec les quatre champs essentiels. Jeu à deux ballons : organisation visuelle restant à vérifier.

Lot Munster : docs/LOT_MUNSTER_2026-09-16.md. Cinq jeux complétés ; 98/150 fiches avec les quatre champs essentiels, 137 enrichies. PDF lisible via lecteur web ; capture locale bloquée au contrôle robots.

Lot écossais : docs/LOT_ECOSSE_ESSENTIELS_2026-09-16.md. Cinq fiches complétées ; 103/150 réunissent objectif, organisation, déroulement et consignes. Les objectifs non explicités restent inconnus.
