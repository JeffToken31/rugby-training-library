# Modèle cible — décision du 7 septembre 2026

## Priorité et périmètre
Construire une grosse bibliothèque d'exercices U8 pour quelques coachs. Python standard, SQLite et fichiers locaux suffisent. Ni front, ni gestion des enfants, ni prise en charge complexe des autres catégories à ce stade. Le catalogue existant est conservé comme format historique de transition.

## 1. Qualifier avant d'extraire
Le format (PDF, HTML, VIDEO, POST) est distinct du type pédagogique :
| Type | Stratégie |
|---|---|
| SESSION_PDF / SESSION_VIDEO | Repérer la chronologie réelle, créer la séance et extraire chaque situation, avec pages ou temps |
| EXERCISE_PDF / EXERCISE_VIDEO | Une situation par défaut ; variantes seulement si les règles changent réellement |
| WEB_PAGE | Examiner le contenu : fiche unique, index de liens ou ensemble de situations |
| CYCLE | Créer les séances explicitement décrites et leur ordre, sans inventer les séances manquantes |
| TECHNICAL_DOCUMENT | Extraire les situations exécutables ; conserver les conseils comme contenu associé |
| PEDAGOGICAL_CONTENT | Documenter les principes ; ne pas fabriquer un exercice pour chaque paragraphe |
| RULES | Référence datée ; aucun exercice généré automatiquement |

Une ressource peut avoir plusieurs qualifications. En cas d'incertitude, conserver la candidature et la qualification proposée, pas un découpage arbitraire. Un PDF de 30 pages n'est pas nécessairement une séance. Une page d'index alimente la découverte et ne compte pas comme exercice.

## 2. Objets et relations
- **ExerciseFamily** : principe commun, identifiant stable indépendant du titre. Regroupement initial facultatif, révisable.
- **ExerciseVariant** : situation exécutable, avec ses règles et paramètres. Plusieurs variantes par famille ; famille NULL tant que le rapprochement n'est pas examiné.
- **Resource** : objet publié avec URL et métadonnées. Plusieurs captures datées possibles.
- **ResourceOccurrence** : passage précis d'une capture : pages PDF (numérotation fichier, base 1), temps vidéo en secondes ou section HTML. Plusieurs variantes peuvent partager un passage et une variante avoir plusieurs passages.
- **ExerciseSource** : lien variante–occurrence, rôle (description, variante, illustration, contradiction), sans imposer une source principale.
- **Session** : séance source ou proposition, distincte d'une ressource. Une séance comporte des activités et des pauses.
- **SessionExercise** : variante, ordre, durée choisie, groupe et réglages de séance. Même variante réutilisable plusieurs fois.
- **Tag** : vocabulaire simple pour thème, compétence, opposition, contact, décision, niveau. Les catégories d'âge originales restent séparées de l'adéquation U8 estimée.

Origine d'une variante : SOURCE, AI_SUGGESTED ou COACH. Statut de traitement : IMPORTED, AI_PARSED, REVIEWED, VALIDATED, REJECTED. REVIEWED signifie vérification documentaire, pas validation pédagogique. VALIDATED nécessite une validation explicite attribuée à un coach ; ne jamais la déduire d'une lecture par IA.

## 3. Informations conservées
Le noyau relationnel contient identifiants, liens, origine, état, ordre, provenance et dates. Les paramètres évolutifs sont en JSON : titres original/normalisé, descriptions, objectifs, thèmes et sous-thèmes, compétences, âges, niveau, joueurs min/max, durée, matériel, espace/dimensions, organisation, déroulement, consignes, réussite, erreurs, points coach, opposition, intensité, contact, décision et variantes décrites. Les inconnues restent NULL.

Chaque information qualifiée possède un chemin de champ, une valeur et une origine SOURCE / AI_INFERRED / COACH_VALIDATED, l'occurrence qui la justifie, l'auteur du traitement et sa date. Plusieurs assertions contradictoires sont conservées ; la valeur retenue pour l'affichage reste une décision explicite. Une donnée inférée n'écrase jamais une donnée source silencieusement.

Complétude facultative : proportion des champs utiles renseignés, avec liste/version des champs évalués. Ce score ne mesure ni qualité pédagogique ni sécurité, et ne bloque jamais l'import.

## 4. Traçabilité et conservation
Captures immuables : URL demandée/finale, date, statut HTTP, type MIME, empreinte SHA-256, version extracteur et chemins vers fichiers conservés. Archive locale distincte des exports et ignorée par Git par défaut. Télécharger un PDF public seulement lorsque pertinent et permis. Conserver pages et texte brut lorsque les conditions le permettent ; sinon URL, localisation, métadonnées, courts extraits autorisés et reformulation. Ne pas republier de longues transcriptions ou documents protégés dans le dépôt. Pas de téléchargement vidéo par défaut.

Une nouvelle extraction crée un nouveau traitement sur la capture, sans effacer le précédent. Les captures existantes sont réutilisées lorsque possible. Pour les données historiques sans capture, indiquer explicitement cette absence ; ne pas prétendre disposer du texte brut.

## 5. Rapprochements
Dédupliquer les téléchargements par empreinte n'est pas fusionner les exercices. L'URL canonique et l'identifiant fournisseur aident à identifier une ressource ; aucun titre n'est une clé unique.

Créer des candidats de rapprochement avec score, méthode/version et explication : SAME_FAMILY, SAME_VARIANT, DIFFERENT_VARIANT, DIFFERENT_EXERCISE, UNDECIDED. Comparer objectifs, règles, opposition, organisation et contraintes, pas seulement les titres. Garder les deux fiches jusqu'à décision ; les fusions ultérieures conservent aliases, occurrences et journal de décision. Pas de suppression automatique par similarité.

## 6. Pipeline
Découverte → capture brute → qualification → stratégie → extraction de candidats → normalisation → tags → familles candidates → rapprochements → insertion → validation éventuelle.
Chaque étape conserve état, version et erreur pour reprendre une collecte interrompue. Les blocages d'accès restent visibles ; aucun contournement et aucune demande de validation coach fiche par fiche.

## 7. Schéma et migration
Le prototype SQL séparé est dans schema/v2.sql. Il n'est pas encore la base de production du catalogue. Avant bascule :
1. Sauvegarder et importer le JSON historique sans perte.
2. Convertir chaque source en ressource ; chaque localisation en occurrence non structurée si ses coordonnées ne sont pas fiables.
3. Convertir les exercices en variantes SOURCE, sans famille inventée.
4. Convertir les adaptations U8 en propositions AI_SUGGESTED liées à leur variante d'origine ; examiner lesquelles sont de véritables variantes ou seulement des paramètres.
5. Conserver les références complémentaires comme occurrences avec rôle explicite ; ne pas assimiler automatiquement leurs règles.
6. Vérifier les comptes, les champs historiques et les liens ; comparer les exports avant de remplacer le lecteur existant.

Le verrou UNIQUE(source, localisation) du format historique ne sera pas repris. Plusieurs exercices peuvent partager une page et un exercice apparaître à plusieurs endroits. Les prochaines collectes massives attendent cette migration ; la découverte déjà effectuée reste réutilisable.

## Avancement du 7 septembre
Le migrateur de transition et le lecteur v2 sont désormais utilisables : voir LOT_2026-09-07.md. Les propositions historiques restent attachées comme paramètres inférés tant que leur nature de variante n'est pas établie. Cela évite de gonfler artificiellement le nombre d'exercices.
