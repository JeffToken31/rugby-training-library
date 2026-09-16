# Cadrage courant — 16 septembre 2026

## Décision utilisateur
Suspendre toute collecte supplémentaire. Consolider les 150 fiches existantes et préparer les données et le cadrage de l’interface de création de séances. Ne pas rechercher de nouveaux exercices ni développer le front avant le cadrage. Les anciennes priorités quantitatives (200 fiches, etc.) sont remplacées par cette décision.

## Terrain
Priorité U8 ; environ 30 enfants, 5–6 éducateurs, séance de 90 minutes, 2 ou 3 groupes, trois ateliers de 6–8 minutes, récréation de 10 minutes, échauffement et opposition reliée aux objectifs des ateliers. Consignes et transitions incluses dans les 90 minutes. Matériel et règles du club à préciser au cadrage de l’interface.

## Source de vérité
Les lots immuables et révisions sont ordonnés dans data/manifest.json. Python standard et SQLite, WSL Ubuntu-22.04, utilisateur jeff, sans sudo. Exécuter python3 pipeline.py hors réseau. L’application utilisera exports/APPLICATION.json ; ne pas analyser les fiches Markdown pour reconstruire les données.

150 fiches ne signifie pas 150 jeux uniques. Les 22 familles éditoriales sont distinctes des deux familles historiques SQL. Conserver les rapprochements et toutes les sources ; aucune fusion automatique. Les statuts documentaires ne prouvent ni exhaustivité ni validation coach. Le bilan à jour est exports/QUALITE_APPLICATION.md.

## Provenance
Séparer faits documentés, propositions IA, valeurs historiques non réexaminées et observations utilisateur. Les inconnues restent nulles. Ne jamais inventer dimensions, effectifs, contact, critères de réussite ou règles manquantes pour afficher une fiche complète. Les propositions sont modifiables dans une séance sans modifier la fiche source.

Carré 2 : intégrer la description utilisateur et l’interdiction d’empêcher les voleurs. Les 30 secondes évoquées ne sont pas une durée prescrite. Les autres situations vidéo incomplètes restent à part ; ne pas redemander le PDF octobre déjà reçu.

## Livraison et prochaine étape
Consulter docs/INTERFACE_SEANCES.md et docs/CONTRAT_APPLICATION.md. Prévoir bibliothèque, fiche et constructeur de séance, sans gestion des enfants ou des parents au MVP. Dépôt GitHub privé. Aucun secret ni donnée personnelle enfant. Archives brutes locales non publiées. L’ancienne automatisation de collecte est en pause.

Historique conservé dans docs/archive/PROJECT_avant_consolidation.md. Les anciens bilans datés décrivent leur lot ; ils ne fixent plus la priorité courante.

## Répartition du travail confirmée

L’utilisateur confie ici les actions sur la base : affiner les informations existantes, attribuer les tags et permettre plusieurs catégories sans dupliquer les fiches. Le cadrage de l’application sera mené dans une autre conversation ; ne pas lancer son développement ici. Les tags sont versionnés dans data/exercise-tags.json et intégrés à la reconstruction. Aucune collecte supplémentaire.

## Génération IA souhaitée
L’utilisateur veut demander des propositions de séances selon ses attentes dans le créateur, puis les modifier et les adapter. Voir docs/GENERATION_SEANCES_IA.md. Préparer les données utiles ici ; cadrage et interface restent dans l’autre conversation. Les budgets de durée proposés sont séparés des faits sources et ne constituent pas des prescriptions d’effort.

## Lecture centralisée
Le point d’entrée utilisateur est exports/CATALOGUE.md. Les anciennes vues séparées redirigent vers ses sections. Priorité aux compléments vérifiables dans les archives existantes ; conserver les limites de la relecture et les rapprochements non résolus.
