# Contrat de lecture application — version 1

Référence du socle de données existant. Pour le produit visé et les décisions de développement, partir de [PROJECT.md](../PROJECT.md).

## Construction et responsabilités

`python3 pipeline.py` lit le [manifeste](../data/manifest.json), importe les lots et applique les révisions dans SQLite. [catalogue_v2.py](../catalogue_v2.py) charge [schema/v2.sql](../schema/v2.sql). [application_data.py](../application_data.py) produit la [vue JSON de lecture v1](../exports/APPLICATION.json), que [unified_catalogue.py](../unified_catalogue.py) restitue en Markdown. La reconstruction par défaut fonctionne sans réseau. La vue expose les compléments et leur provenance en conservant les valeurs documentaires.

`schema_version` vaut 1. `content_sha256` identifie le contenu sérialisé avec clés triées, UTF-8, hors empreinte elle-même. La disponibilité des captures locales peut changer cette empreinte entre machines. À environnement identique, deux reconstructions donnent le même export d’application.

## Objets exposés

| Champ | Utilisation |
|---|---|
| exercises[].id | Identifiant stable, jamais le titre comme clé |
| title, original_title, summary | Présentation et recherche textuelle |
| theme, classification | Thème historique et famille éditoriale proposée |
| age_source | Texte d’âge original ; ne pas interpréter comme certification U8 |
| u8_adaptation, u8_proposed_settings | Adaptations et paramètres proposés, distincts des sources |
| participants_scope | Effectif par groupe, binôme, atelier ou autre périmètre |
| fields | Valeurs d’affichage, état et provenance par champ |
| documentary_fields | Valeurs avant compléments d’application |
| source, locator, references, history | Références principales, secondaires et révisions |
| observation | Description rapportée complète, avec incertitudes et durée observée |
| related_candidates, comparison_reviews | Proximités connues ; ne pas fusionner automatiquement |
| quality | Manques, origine des rubriques, visibilité initiale et limites |

Les 12 rubriques suivies sont objectif, organisation, déroulement, consignes, critères de réussite, erreurs fréquentes, points coach, durée, effectifs minimum/maximum, espace et matériel. Les valeurs descriptives historiques peuvent être du texte ou une liste ; le front affiche les listes comme étapes et le texte comme paragraphe. Les paramètres numériques connus restent numériques. Les inconnues sont nulles, jamais zéro ni une chaîne « Non renseigné » dans ces champs structurés.

États : PRESENT, NOT_STATED, NOT_EXTRACTED, BLOCKED, CONFLICTING. Une contradiction ne constitue pas une valeur utilisable pour un filtre numérique. Origines : SOURCE, AI_INFERRED, LEGACY_UNREVIEWED, USER_REPORTED. SOURCE signifie attribution documentaire, pas validation par un entraîneur. Les liens vidéo candidats ne prouvent pas un visionnage.

## Sélection et filtres

- DOCUMENTED_CORE : quatre rubriques essentielles présentes avec objectifs documentés.
- PROPOSED_OBJECTIVE : objectif formulé par IA, à distinguer visuellement et confirmer pour la séance.
- REPORTED_OBSERVATION : déroulement issu d’une description utilisateur ; incertitudes visibles.
- INCOMPLETE : une rubrique essentielle manque ; à part, pas de sélection dans une séance.

`default_visible` sélectionne les trois premiers états. Il ne signifie pas « prêt terrain ». Les durées, effectifs, dimensions et matériel peuvent encore nécessiter des réglages. `coach_validated=false` et `u8_suitability=TO_REVIEW` restent explicites. Le niveau de contact n’a pas été normalisé : UNKNOWN, aucun filtre « sans contact » ne doit le déduire silencieusement.

Champs disponibles pour le futur filtrage : recherche texte, thème, famille, organisme, âge source, état de description, présence/origine des rubriques. Durée et effectif : uniquement sur valeurs PRESENT, et avec choix « paramètres source » ou « mes réglages ». Ne pas masquer les inconnus sans proposer de les afficher. Le matériel est encore du texte, donc recherche textuelle plutôt que fausses quantités normalisées. Ne pas compter les familles comme des exercices uniques.

## Exemple structurel et contrôles existants

Le [brouillon JSON](../data/session-draft.example.json) sert de cas de test structurel. Il reprend l’[exemple de septembre](SEANCE_EXEMPLE.md) avec 90 minutes de blocs et des activités encore à choisir. Le format de l’exemple contient notamment identifiant, statut DRAFT, objectif, durée, effectif, éducateurs, groupes et blocs ordonnés. Les exercices sont référencés par identifiant et les paramètres choisis appartiennent à la séance.

Les rotations se succèdent et les groupes travaillent en parallèle dans une rotation. Dans l’exemple historique, trois rotations comportant chacune 7 minutes de travail et 1 minute de transition occupent 24 minutes au total.

[`session_plan.validate`](../session_plan.py) vérifie les effectifs, les durées, les affectations et les références. Il refuse les identifiants inconnus et les fiches INCOMPLETE. Ses contrôles sont structurels. La préparation pédagogique et les conditions de terrain restent à vérifier par l’éducateur.

**Écart avec la cible.** Le validateur exige que la somme des durées des blocs égale `duration_min`. Il rejette donc un brouillon qui déclare 90 minutes avec seulement 70 minutes de blocs. La [trame produit](INTERFACE_SEANCES.md#trame-et-calcul-du-temps) demande de distinguer créneau, temps planifié et marge. La représentation technique de ces durées et la compatibilité avec l’existant relèvent de l’audit à venir. Voir les [questions ouvertes](DECISIONS.md#questions-ouvertes).

## Tags de filtrage — complément du 16 septembre

`tag_taxonomy.tags` expose les définitions : identifiant stable, libellé français et dimension (`skill` ou `format`). Chaque exercice expose `tag_ids` et `tagging` (origine AI_INFERRED, date, champs examinés et statut EDITORIAL_REVIEWED ou PROVISIONAL). Le classement est une décision éditoriale appliquée au corpus, pas une extraction de mots-clés au chargement.

Les 17 compétences et 9 formes de jeu de l’export actuel sont combinables. Un même identifiant peut être listé dans plusieurs catégories ; l’union des résultats doit être dédupliquée par identifiant. Les tags ne créent aucune variante et ne décident pas de fusion entre deux fiches proches. Les thèmes historiques et les 22 familles sont conservés.

`exercise_tags.select` implémente ET/OU, rejette les tags inconnus et exclut par défaut les fiches INCOMPLETE. Le tag Plaquage pointe actuellement vers une fiche encore incomplète : afficher ce manque plutôt que proposer une autre activité de contact comme équivalente. Absence d’un tag ≠ preuve d’absence d’une compétence. Niveau de contact et adéquation U8 restent distincts et non déduits.

La dimension « forme de jeu » n’est pas forcée quand aucun des formats définis ne décrit correctement la fiche. Les tags sont affichés dans les fiches et dans la [section catégories du catalogue](../exports/CATALOGUE.md#categories).

## Repères de préparation des fiches

`preparation_questions` contient les réglages à définir selon les paramètres absents ou contradictoires : champ, état documentaire et question lisible. Ce ne sont pas des règles ajoutées à la source. `coach_cues`, lorsqu’il existe, contient un indicateur observable et un point d’observation proposés (AI_INFERRED), avec date et champs de référence. Les critères documentaires restent dans `fields.success_criteria` sans remplacement. Vingt fiches bénéficient de ces compléments ; les autres restent sans proposition plutôt que recevoir un texte générique. `source_conflicts` et `bout_seconds` conservent aussi les contradictions historiques et les durées de manche, distinctes de la durée totale.

## Durées de planification
`planning_duration` distingue PLANNING_PROPOSAL, EXISTING_DURATION, KNOWN_ROUND_DURATION et INSUFFICIENT_DESCRIPTION. Une proposition expose profil, durée minimum/maximum en secondes, explication, nombre de séquences, temps par séquence, pauses et retour. Les budgets proposés incluent les explications et retours et laissent le changement de station à planifier. Ils restent des hypothèses éditoriales à confirmer. Les durées documentaires sont exposées séparément. Les profils et affectations sont versionnés dans [data/timing-proposals.json](../data/timing-proposals.json).

## Catalogue centralisé

`unified_catalogue.py` produit le catalogue et les fiches individuelles à partir du même rendu de `APPLICATION.json`. Les anciennes vues DUREES, CATEGORIES, COMPARAISONS et bilans de préparation redirigent vers le catalogue. Les fichiers de données restent séparés pour conserver la provenance et reconstruire l’ensemble ; la lecture utilisateur est centralisée.

`consolidation_review` conserve le contrôle des déroulements identiques et la relecture des 16 rapprochements déjà enregistrés. Le rapprochement examine l’objectif, les règles, l’opposition et l’organisation. Les variantes et leurs sources restent accessibles pendant l’examen, sans fusion automatique. `consolidation_review.missing_review`, repris dans `exercises[].missing_review` pour les fiches concernées, décrit les limites des neuf descriptions insuffisantes. Le nombre de jeux uniques reste indéterminé.

## Usage échauffement
`session_uses` contient WARMUP lorsque la source publie explicitement la situation dans un contenu échauffement. `warmup_usage` conserve source, localisation, origine de cet usage et étape éditoriale (general, mobility, specific). Un tableau vide signifie non qualifié, pas usage interdit. Le sélecteur de fiches combine les tags et l’usage WARMUP. Une future composition d’échauffement pourra assembler plusieurs activités en distinguant leurs budgets de la durée totale du bloc. Les fiches du module enfants ne certifient pas une validation spécifique U8 française.

## Retrouver la provenance

Les descriptions et révisions attribuées sont versionnées dans les entrées du manifeste. Les captures brutes restent locales. Une métadonnée ou un lien candidat ne garantit pas que le support a été visionné ou extrait.

- [Carré 2 dans les entrées](../data/observation-carre2-20260916.json) et [récit d’origine](../archive/docs-legacy/OBSERVATION_CARRE2.md). L’interdiction d’empêcher le vol de ballons est rapportée par le coach. Les quelque 30 secondes évoquées qualifient une observation, et la durée prescrite reste inconnue.
- [Références vidéo de l’atelier FFR d’octobre](../data/ffr-atelier1-video-links.json) et [trace de récupération](../archive/docs-legacy/LIENS_VIDEO_ATELIER1.md). Les liens récupérés documentent la provenance et chaque situation garde ses lacunes visibles.
