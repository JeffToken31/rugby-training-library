Poursuivre de manière autonome le projet rugby-training-library dans WSL Ubuntu-22.04 :
/home/jeff/projects/rugby-training-library
Lire en priorité AGENTS.md, PROJECT.md, l’état actuel du dépôt, les données existantes et les nouvelles instructions de cette conversation avant toute modification.
MODE DE TRAVAIL
L’utilisateur demande d’enchaîner sans relance manuelle.
Travailler par lots complets et continuer automatiquement avec le lot utile suivant tant qu’un travail pertinent, sûr et non redondant reste possible.
Ne solliciter l’utilisateur que lorsqu’une intervention humaine est réellement nécessaire :
authentification précise ;
CAPTCHA ou validation interactive ;
permission système ;
dépense ;
décision irréversible ;
arbitrage pédagogique important impossible à inférer raisonnablement.
Ne pas interrompre le travail pour des choix techniques mineurs, réversibles ou internes.
Rester silencieux lorsqu’il n’y a aucun changement exploitable à signaler.
Notifier uniquement :
une étape majeure réellement utilisable ;
un changement important de stratégie ;
une difficulté bloquante ;
une intervention nécessaire ;
l’atteinte d’un seuil significatif ;
ou la fin du travail autonome.
Ne pas répéter le test sonore.
PRIORITÉ ABSOLUE : LA GROSSE BASE U8
L’objectif immédiat n’est PAS de développer l’interface.
La priorité est de constituer une bibliothèque U8 riche, structurée, fiable et exploitable pour préparer rapidement des séances d’entraînement.
Mettre le front en attente.
Ne modifier les outils, scripts ou architecture que si cela :
débloque la collecte ;
améliore significativement la qualité des données ;
évite des pertes ;
améliore la qualification ;
améliore le dédoublonnage ;
ou permet une ingestion plus massive et fiable.
Ne pas développer de fonctionnalités d’interface par anticipation.
ÉTAT EXISTANT
Le catalogue dépasse déjà 72 fiches.
Ne pas reprendre la migration déjà livrée.
Utiliser :
data/manifest.json
et :
python3 pipeline.py
pour reconstruire les données sans perdre les enrichissements existants.
Les révisions successives sont maintenant prises en charge.
Avant chaque lot important, vérifier l’état réel du catalogue afin d’éviter :
les doublons de collecte ;
les régressions ;
la perte d’enrichissements ;
le retraitement inutile de ressources récemment bloquées.
OBJECTIF QUANTITATIF V1
Cible principale :
environ 200 exercices ou variantes U8 réellement exploitables et correctement structurés.
À partir d’environ 150 exercices/variantes uniques, commencer à évaluer sérieusement la couverture fonctionnelle de la base.
À environ 200 exercices/variantes, ne poursuivre la collecte massive que si :
des thèmes importants restent sous-représentés ;
certaines familles importantes manquent ;
ou les nouvelles sources continuent à apporter un taux significatif de nouveauté.
Ne pas chercher artificiellement à atteindre un nombre.
Ne jamais compter comme exercice :
un simple lien ;
une page d’index ;
un PDF non analysé ;
une vidéo non comprise ;
une ressource générique ;
un doublon ;
une référence sans description exploitable.
MESURER LA SATURATION
Suivre progressivement le rendement des nouvelles collectes.
Lorsqu’un lot d’environ 30 à 50 ressources pertinentes apporte très peu de nouvelles familles ou variantes réellement différentes, considérer que la collecte commence à saturer.
Indicateur pratique :
si moins de 15 à 20 % des nouvelles ressources pertinentes apportent une vraie nouvelle variante ou famille, réduire la collecte généraliste et privilégier :
les thèmes manquants ;
l’enrichissement des fiches existantes ;
la qualification ;
les sources nouvelles ;
les lacunes identifiées.
Ne pas continuer à scraper uniquement pour augmenter le volume.
U8 D’ABORD
U8 / M8 est la priorité fonctionnelle absolue.
L’architecture peut rester extensible à d’autres catégories, mais ne pas complexifier le projet pour U10, U12, U14 ou adultes tant que le périmètre U8 n’est pas suffisamment fonctionnel.
Les ressources M6-M8 peuvent être utilisées lorsqu’elles sont clairement pertinentes pour U8.
Les exercices provenant d’autres catégories peuvent être intégrés uniquement lorsqu’ils sont raisonnablement adaptables et clairement qualifiés comme tels.
Ne jamais présenter une adaptation IA comme une recommandation officielle de la source.
MODÈLE CONCEPTUEL : FAMILLES ET VARIANTES
Ne jamais utiliser le nom comme identifiant logique d’un exercice.
Plusieurs exercices peuvent porter le même nom tout en étant différents.
Inversement, deux exercices portant des noms différents peuvent être équivalents.
Conserver la distinction :
ExerciseFamily → concept pédagogique général
ExerciseVariant → version réellement exécutable avec ses propres paramètres
Resource → document, vidéo, page Web ou autre source
ExerciseOccurrence → endroit précis où une variante apparaît dans une ressource
Session → séance complète
SessionExercise → exercice/variante utilisé dans une séance avec ordre, durée et contexte
Exemple :
Famille : Jeu en couloir
Variantes possibles :
sans opposition ;
opposition passive ;
2 contre 1 ;
fixation + passe ;
défense libre ;
règle de marque spécifique.
Ne pas fusionner automatiquement deux exercices.
Classer plutôt :
même variante probable ;
même famille mais variante différente ;
exercice différent ;
relation incertaine.
Conserver un score ou une indication de similarité lorsque pertinent.
VARIANTES
Les variantes importantes doivent être représentées explicitement.
Une variante peut posséder ses propres :
règles ;
objectifs ;
nombre de joueurs ;
durée ;
dimensions ;
matériel ;
difficulté ;
opposition ;
critères de réussite ;
tags ;
consignes.
Ne pas créer une nouvelle variante pour une différence insignifiante.
Conserver l’origine lorsqu’elle est connue :
SOURCE → explicitement proposée par la ressource
AI_INFERRED → déduite ou structurée par l’IA
COACH_VALIDATED → validée ou créée par un coach
Ne jamais faire passer une variante AI_INFERRED pour une variante provenant de la source originale.
QUALIFICATION AVANT EXTRACTION
Chaque ressource collectée doit d’abord être comprise et qualifiée.
Exemples :
exercice unique ;
séance complète ;
cycle de séances ;
vidéo d’exercice ;
vidéo multi-exercices ;
PDF d’exercice ;
PDF de séance ;
article pédagogique ;
fiche technique ;
règlement ;
contenu de formation.
La stratégie d’ingestion dépend du contenu réel et non simplement du format du fichier.
PDF
Attention particulièrement aux PDF.
PDF contenant UNE séance complète
Si un PDF décrit une séance contenant plusieurs situations :
comprendre sa structure ;
créer ou enrichir la séance ;
identifier chaque exercice ou situation distincte ;
créer les variantes correspondantes lorsque nécessaire ;
conserver leurs pages exactes ;
conserver la relation avec la séance d’origine.
Exemple :
PDF 30 pages
→ séance complète → échauffement pages 4-5 → exercice A pages 6-7 → exercice B pages 8-10 → exercice C pages 11-12 → opposition finale pages 13-14
PDF contenant UN exercice
Si le PDF est déjà une fiche consacrée à un exercice ou une situation unique :
NE PAS le découper artificiellement.
Créer ou enrichir directement l’exercice correspondant.
Même logique pour les vidéos.
DONNÉES À EXTRAIRE
Capturer le maximum d’informations utiles disponibles.
Une fiche peut être incomplète : les champs inconnus doivent rester NULL, UNKNOWN ou équivalent.
Ne pas inventer une valeur uniquement pour remplir un champ.
Rechercher notamment :
titre original ;
titre normalisé ;
famille ;
variante ;
résumé ;
description complète ;
déroulement ;
objectif principal ;
objectifs secondaires ;
thème principal ;
sous-thèmes ;
compétences travaillées ;
catégorie d’âge ;
niveau ;
joueurs minimum ;
joueurs maximum ;
durée ;
matériel ;
dimensions ;
organisation spatiale ;
groupes ;
rotations ;
opposition ;
niveau d’opposition ;
contact / sans contact ;
intensité ;
prise de décision ;
consignes éducateur ;
critères de réussite ;
erreurs fréquentes ;
points d’attention ;
sécurité ;
adaptations ;
variantes ;
progression ;
simplifications ;
complexifications ;
langue ;
organisme ;
auteur ;
date de publication ;
URL ;
pages PDF ;
timestamp vidéo ;
transcription ;
texte brut extrait ;
métadonnées originales ;
date de collecte.
Ajouter de nouveaux champs pertinents si les sources révèlent régulièrement des informations utiles non prévues.
Le but est d’éviter de devoir rescanner toutes les sources lors du développement futur du produit.
QUALITÉ DES FICHES
Privilégier les exercices réellement compréhensibles et utilisables sur le terrain.
Une fiche de qualité doit permettre autant que possible à un coach de comprendre :
ce que les enfants doivent faire ;
pourquoi ils le font ;
comment installer la situation ;
combien de joueurs sont nécessaires ;
quel matériel utiliser ;
comment faire évoluer ou simplifier l’exercice ;
quelles consignes observer.
Une fiche pauvre mais traçable peut être conservée comme candidate.
Ne pas la considérer automatiquement comme exercice pleinement exploitable.
Prévoir ou conserver si possible un indicateur de :
complétude ;
confiance ;
qualité ;
statut de validation.
TRAÇABILITÉ ET PROVENANCE
Conserver la provenance de chaque ressource et autant que possible des informations importantes.
Origines possibles :
SOURCE
AI_INFERRED
COACH_VALIDATED
Conserver :
URL originale ;
titre original ;
organisme ;
document ou vidéo d’origine ;
pages ;
timestamps ;
texte extrait ;
transcription ;
métadonnées ;
date de collecte ;
éventuelle capture permise ;
inconnues ;
historique d’enrichissement.
Ne jamais écraser inutilement les données originales avec une version normalisée.
RESSOURCES ET SOURCES
Diversifier réellement les sources.
Priorités actuelles :
FFR / formation.ffr.fr ;
World Rugby ;
autres fédérations nationales ;
RugbyCoaching et autres sites spécialisés accessibles ;
YouTube ;
clubs, blogs et contenus pédagogiques pertinents ;
réseaux sociaux uniquement lorsqu’ils sont techniquement et légalement accessibles sans contournement.
FFR est une excellente source mais la base ne doit pas devenir une simple bibliothèque FFR.
Chercher progressivement une diversité d’approches pédagogiques.
AUTHENTIFICATION
Un compte RugbyCoaching est connecté dans le navigateur.
Utiliser la session existante si elle permet l’accès normal aux ressources.
Ne jamais :
demander un mot de passe dans le chat ;
extraire les cookies ;
exporter les identifiants ;
contourner un CAPTCHA ;
contourner une protection d’accès.
Demander une intervention uniquement lorsqu’un blocage authentifié précis nécessite réellement que l’utilisateur se reconnecte.
Ne pas répéter inutilement des collectes récemment bloquées.
STOCKAGE ET OUTILS
Utiliser Python standard et SQLite.
Pas de sudo.
Conserver les ressources locales lorsque cela est pertinent, autorisé et utile au retraitement.
Sinon conserver au minimum :
l’URL ;
les métadonnées ;
le contenu extrait permis ;
les occurrences précises.
Push autorisé uniquement vers le dépôt privé :
JeffToken31/rugby-training-library
Ne publier aucun site.
Ne stocker :
aucune donnée concernant des enfants ;
aucun mot de passe ;
aucun cookie ;
aucun token ;
aucun secret.
Aucune dépense sans accord explicite.
CONTEXTE TERRAIN
Conserver comme contexte fonctionnel actuel :
environ 30 enfants ;
environ 5 à 6 éducateurs ;
séance d’environ 90 minutes ;
2 ou 3 groupes selon l’effectif ;
trois ateliers tournants ;
ateliers typiquement de 6 à 8 minutes ;
pause/récréation d’environ 10 minutes ;
opposition finale en lien avec les ateliers.
Ces paramètres servent à évaluer l’utilité d’une fiche pour le contexte réel, mais ne doivent pas éliminer des exercices U8 valables pour d’autres configurations.
FIN DE LA COLLECTE AUTONOME V1
Mettre en pause la collecte massive lorsque :
la bibliothèque approche ou dépasse environ 200 variantes réellement exploitables ;
les principaux domaines U8 sont suffisamment couverts ;
les nouvelles collectes deviennent fortement redondantes ;
les principales sources accessibles ont été raisonnablement explorées ;
les outils de reconstruction et de conservation sont fiables.
À ce moment-là, effectuer un bilan honnête comprenant :
nombre de familles ;
nombre de variantes réellement exploitables ;
nombre de séances complètes ;
répartition par grands thèmes ;
répartition par provenance ;
taux de complétude ;
éléments encore non qualifiés ;
principaux manques ;
principales limites ;
sources bloquées ou inaccessibles ;
niveau de saturation observé.
Ne pas commencer automatiquement un gros développement de front.
Signaler simplement que la base V1 est suffisamment substantielle pour envisager la phase interface.
## UTILISATION DES PLUGINS ET OUTILS DE RECHERCHE

Utiliser les outils disponibles de manière complémentaire, sans multiplier inutilement les recherches.

- Utiliser **Deep Research** pour les recherches larges ou complexes : découverte de nouvelles sources rugby U8/M8, fédérations, bibliothèques d’exercices, PDF, vidéos, ressources pédagogiques ou comparaison de plusieurs sources.
- Utiliser ensuite les **collecteurs et scripts locaux** pour l’ingestion massive, structurée et reproductible des ressources identifiées.
- Utiliser **GitHub** lorsque pertinent pour inspecter le dépôt, suivre les changements, vérifier la CI, gérer les problèmes techniques et publier les changements autorisés sur le dépôt privé prévu.
- Ne pas utiliser Deep Research pour retraiter ce qui existe déjà localement ou pour remplacer une collecte automatisable par les scripts du projet.
- Ne pas multiplier les recherches sur une source récemment bloquée ou déjà explorée sans nouvelle piste.

Lorsqu’une recherche externe identifie une nouvelle source importante :
1. la qualifier ;
2. vérifier son intérêt réel pour U8/M8 ;
3. déterminer si elle contient des exercices, séances, vidéos, PDF ou contenus pédagogiques ;
4. déterminer la meilleure méthode d’ingestion ;
5. seulement ensuite lancer une collecte conséquente.

Privilégier les sources apportant plusieurs exercices réellement exploitables plutôt que l’accumulation de liens isolés.

## PRIORISATION DES LOTS

À chaque relance automatique, commencer par inspecter l’état actuel du dépôt et choisir le prochain travail offrant le meilleur rendement.

Ordre de priorité :
1. finir proprement un lot déjà commencé ;
2. exploiter une source U8 riche déjà identifiée ;
3. enrichir des fiches importantes trop incomplètes ;
4. combler un thème U8 sous-représenté ;
5. découvrir de nouvelles sources ;
6. améliorer les outils uniquement si cela débloque ou fiabilise la collecte.

Ne pas relancer une recherche générale si une source riche déjà connue n’a pas encore été correctement exploitée.

## CONTRÔLE DU RENDEMENT

Après chaque lot conséquent, mesurer au minimum :
- nombre de nouvelles variantes réellement exploitables ;
- nombre de nouvelles familles ;
- nombre de doublons ou variantes déjà connues ;
- nombre de fiches enrichies ;
- nombre de ressources inutilisables ou bloquées.

Si le taux de nouveauté chute fortement, privilégier la collecte ciblée et l’enrichissement plutôt qu’une nouvelle recherche généraliste.