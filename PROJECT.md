# Bibliothèque rugby U8
Référence de cadrage : mise à jour utilisateur du 7 septembre 2026, détaillée dans [ARCHITECTURE](docs/ARCHITECTURE.md).

Référence opérationnelle complémentaire : [CONTRAT_DE_LIVRAISON](docs/CONTRAT_DE_LIVRAISON.md). Clarification utilisateur : cible finale = très grande base d'exercices et interface riche pour rechercher, trier, filtrer et préparer les séances, priorité U8. Les 60 fiches actuelles ne sont ni un plafond ni un corpus à compléter entièrement avant tout ajout. Faire progresser collecte nouvelle, richesse des données et outils ensemble. Ne pas confondre taille du catalogue et qualité.

Priorité absolue : une grosse base structurée d'exercices U8, consultable rapidement par quelques coachs. L'exercice et ses variantes sont au centre ; les ressources alimentent et justifient les fiches. Construire progressivement une interface de consultation et de préparation fondée sur le modèle de données ; la richesse des filtres et des fiches fait partie du produit final.

Technique : Python standard + SQLite, dans WSL sous jeff, sans sudo. Dépôt GitHub privé JeffToken31/rugby-training-library. Aucune donnée enfant, aucun secret. Notifications de cette application ; le test n'a pas produit de son chez l'utilisateur.

Terrain confirmé : environ 30 enfants (à ajuster au démarrage), 5–6 éducateurs, séance de 90 minutes, 2 ou 3 groupes selon présence, trois ateliers de 6–8 minutes, échauffement, opposition reliée aux objectifs, récréation de 10 minutes et temps de consigne. Matériel encore inconnu, non bloquant pour le modèle.

État au 8 septembre : 75 fiches (66 documentées et 9 pistes incomplètes), 52 ressources référencées, quatre trames de séance sources. 39 fiches avec au moins un champ enrichi ; 44 ressources conservées localement. La commande python3 pipeline.py reconstruit le catalogue depuis data/manifest.json, applique tous les enrichissements, contrôle les relations et produit les exports sans réseau. Ajouter --collect pour une collecte bornée. Voir docs/LOT_2026-09-08.md. Les captures locales ne sont pas transportées par Git ; leur présence est vérifiée séparément des références d’empreinte. Suite : diversifier les sources U8, enrichir les autres fiches, organiser les familles et construire la consultation pour les coachs. Les révisions successives d’enrichissement sont disponibles avec historique et provenance par champ ; l’interface reste à développer.

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
