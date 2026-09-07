# Bibliothèque rugby U8
Référence de cadrage : mise à jour utilisateur du 7 septembre 2026, détaillée dans [ARCHITECTURE](docs/ARCHITECTURE.md).

Référence opérationnelle complémentaire : [CONTRAT_DE_LIVRAISON](docs/CONTRAT_DE_LIVRAISON.md). Clarification utilisateur : cible finale = très grande base d'exercices et interface riche pour rechercher, trier, filtrer et préparer les séances, priorité U8. Les 60 fiches actuelles ne sont ni un plafond ni un corpus à compléter entièrement avant tout ajout. Faire progresser collecte nouvelle, richesse des données et outils ensemble. Ne pas confondre taille du catalogue et qualité.

Priorité absolue : une grosse base structurée d'exercices U8, consultable rapidement par quelques coachs. L'exercice et ses variantes sont au centre ; les ressources alimentent et justifient les fiches. Construire progressivement une interface de consultation et de préparation fondée sur le modèle de données ; la richesse des filtres et des fiches fait partie du produit final.

Technique : Python standard + SQLite, dans WSL sous jeff, sans sudo. Dépôt GitHub privé JeffToken31/rugby-training-library. Aucune donnée enfant, aucun secret. Notifications de cette application ; le test n'a pas produit de son chez l'utilisateur.

Terrain confirmé : environ 30 enfants (à ajuster au démarrage), 5–6 éducateurs, séance de 90 minutes, 2 ou 3 groupes selon présence, trois ateliers de 6–8 minutes, échauffement, opposition reliée aux objectifs, récréation de 10 minutes et temps de consigne. Matériel encore inconnu, non bloquant pour le modèle.

État : 60 fiches (51 documentées et 9 pistes à compléter), 40 ressources référencées, quatre trames de séance sources. Import de transition v2 opérationnel et testé sans perte du JSON historique ; recherche et exports v2 disponibles. Utiliser catalogue_v2.py et lire docs/LOT_2026-09-07.md. Filtres v2 combinables disponibles. Premier collecteur de captures locales et extraction de texte HTML opérationnels ; voir docs/COLLECTE_OPERATIONNELLE.md. Couverture par champ et enrichissements séparés disponibles sur quatre fiches ; quatre pages conservées localement. Après reconstruction des lots, appliquer data/enrichment-details.json avec la commande enrich. Voir docs/ENRICHISSEMENT.md. Étendre cette extraction, la collecte et les familles ; la gestion de révisions successives reste à construire. Ne pas compter les liens découverts comme exercices qualifiés.

Autonomie : chercher avant de solliciter ; questions uniquement pour authentification, permission, dépense, décision irréversible ou véritable arbitrage fonctionnel/pédagogique. Ne pas réclamer une validation de chaque import. Les propositions IA restent identifiées ; seul un coach peut valider pédagogiquement.
