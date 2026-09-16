# Contrat de lecture application — version 1

## Construction et responsabilités

`python3 pipeline.py` reconstruit les lots, applique les révisions et produit `exports/APPLICATION.json` sans réseau. Le JSON est la vue de lecture du front ; SQLite reste le moteur de reconstruction. Les observations et propositions restent dans des fichiers versionnés référencés par le manifeste. Aucun remplacement des faits historiques.

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

Filtres disponibles immédiatement : recherche texte, thème, famille, organisme, âge source, état de description, présence/origine des rubriques. Durée et effectif : uniquement sur valeurs PRESENT, et avec choix « paramètres source » ou « mes réglages ». Ne pas masquer les inconnus sans proposer de les afficher. Le matériel est encore du texte, donc recherche textuelle plutôt que fausses quantités normalisées. Ne pas compter les familles comme des exercices uniques.

## Séance indépendante du catalogue

Le brouillon `data/session-draft.example.json` donne un exemple de contrat : identifiant, statut DRAFT, objectif, durée, effectif, éducateurs, groupes et blocs ordonnés. Les exercices sont référencés par identifiant ; les réglages choisis appartiennent à la séance, pas à la source. Pour la future sauvegarde, conserver l’empreinte du catalogue et un instantané des fiches utilisées afin qu’un enrichissement ne change pas une séance passée.

Un bloc d’ateliers contient des rotations successives ; les affectations des groupes à l’intérieur d’une rotation sont simultanées. Trois groupes × trois rotations de 7 minutes + 1 minute de transition occupent 24 minutes, pas 72. À deux groupes, trois stations peuvent tourner avec une station libre.

`session_plan.validate` vérifie effectifs, somme des durées, affectations et références. Il refuse les fiches INCOMPLETE. Il ne vérifie pas la pédagogie, le matériel disponible ou la sécurité. Le brouillon fourni a des blocs à choisir et ne doit pas porter le statut « prêt à utiliser ».

Avant export terrain dans la future interface : choisir les activités encore vides, lier opposition et objectif, confirmer les paramètres, lever les incertitudes utiles, contrôler les éducateurs et matériel, conserver les choix du coach. Pas de compte ni de données d’enfants requis pour ce MVP.

## Tags de filtrage — complément du 16 septembre

`tag_taxonomy.tags` expose les définitions : identifiant stable, libellé français et dimension (`skill` ou `format`). Chaque exercice expose `tag_ids` et `tagging` (origine AI_INFERRED, date, champs examinés et statut EDITORIAL_REVIEWED ou PROVISIONAL). Le classement est une décision éditoriale appliquée au corpus, pas une extraction de mots-clés au chargement.

Les 17 compétences et 10 formes de jeu sont combinables. Un même identifiant peut être listé dans plusieurs catégories ; l’union des résultats doit être dédupliquée par identifiant. Les tags ne créent aucune variante et ne décident pas de fusion entre deux fiches proches. Les thèmes historiques et les 22 familles sont conservés.

`exercise_tags.select` implémente ET/OU, rejette les tags inconnus et exclut par défaut les fiches INCOMPLETE. Le tag Plaquage pointe actuellement vers une fiche encore incomplète : afficher ce manque plutôt que proposer une autre activité de contact comme équivalente. Absence d’un tag ≠ preuve d’absence d’une compétence. Niveau de contact et adéquation U8 restent distincts et non déduits.

La dimension « forme de jeu » n’est pas forcée quand aucun des formats définis ne décrit correctement la fiche. Les tags sont affichés dans le catalogue, dans chaque fiche et dans exports/CATEGORIES.md.
