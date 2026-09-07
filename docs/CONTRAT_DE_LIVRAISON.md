# Contrat de livraison — bibliothèque U8

## Résultat attendu
Quelques coachs doivent trouver rapidement une situation exploitable pour préparer un entraînement U8. Le produit principal est une base riche d'exercices et de variantes traçables, alimentée par une chaîne de collecte qui tolère les échecs. Une interface élaborée n'est pas une condition du premier livrable.

Ce cadrage complète ARCHITECTURE.md ; il ne remplace pas le modèle Family / Variant / Resource / Session. Les mentions de Work dans la conversation d'origine expriment une attente d'autonomie, pas une dépendance technique à ce mode. Le projet fonctionne actuellement dans WSL.

## État audité
Au dernier lot : 60 fiches, dont 51 classées comme documentées et 9 incomplètes ; 40 ressources, quatre trames de séance, une famille et trois rapprochements.
Le statut documentaire signifie que du texte a été consulté. Il ne prouve ni extraction exhaustive, ni capacité d'exécution sans consulter la source, ni validation U8.
Aucune capture brute ni transcription complète n'est encore conservée dans les tables prévues. La découverte de liens ne constitue pas un collecteur complet.
Les lots JSON permettent de reconstruire les fiches rédigées ; ils ne permettent pas de refaire une extraction de données jamais conservées.

## Chaîne à livrer et preuves attendues
| Étape | Comportement attendu | Preuve de fonctionnement |
|---|---|---|
| Découverte | Sources FFR M8 prioritaires, puis autres fédérations et éditeurs ; liens accompagnés de leur provenance | Inventaire indiquant où chaque ressource a été trouvée |
| Diagnostic | Accessibilité, format, restriction, méthode possible, intérêt U8 estimé | Un résultat daté par tentative, y compris les échecs |
| Collecte brute | Conserver les documents/textes accessibles lorsque permis, URL finale, empreinte, date et conditions de conservation | Une ressource autorisée retraitée depuis la copie locale |
| Qualification | Distinguer séance, fiche unique, cycle, document technique, règles et contenu pédagogique | Stratégie attribuée avant extraction, qualification incertaine signalée |
| Extraction | Organisation, consignes, objectifs, réussite, matériel et paramètres disponibles ; coordonnées des passages | Comparaison source–fiche montrant ce qui a été extrait et ce qui reste à lire |
| Normalisation | Variantes distinctes, titres non identifiants, vocabulaire cohérent et provenance par champ | Plusieurs occurrences pour une variante et plusieurs variantes sur une page |
| Rapprochement | Candidats explicables, sans suppression automatique | Les deux fiches restent présentes avant décision |
| Recherche | Texte et filtres combinables ; paramètres source séparés des réglages proposés | Exemple : passe, déplacement, 7 minutes, 8 joueurs ; expliquer les exclusions pour valeurs inconnues |
| Consultation | Fiches lisibles, variantes, sources et séances accessibles | Un coach peut préparer une séance sans parcourir le code |
| Reprise | Continuer ailleurs après blocage, reprendre sans perdre ni dupliquer | Exécution contenant un échec et plusieurs succès, puis reprise vérifiée |

## Richesse d'une fiche
Les objectifs, organisation, déroulement, consignes, critères de réussite, erreurs fréquentes, points coach, opposition, contact, décision, matériel, dimensions, effectif, durée et variantes doivent être des champs séparés lorsqu'ils sont disponibles.
Conserver aussi titres originaux et normalisés, langues, organisme/auteur, dates connues, métadonnées et localisations.
Ne pas remplir artificiellement les champs absents.

Pour chaque champ, distinguer :
- PRESENT : valeur disponible, avec provenance.
- NOT_STATED : passage pertinent examiné, information non donnée.
- NOT_EXTRACTED : information pas encore recherchée ou extraction partielle.
- BLOCKED : accès empêchant sa vérification.
- CONFLICTING : plusieurs valeurs incompatibles conservées.

Ces états décrivent la couverture de l'extraction, pas la qualité pédagogique.
SOURCE / AI_INFERRED / COACH_VALIDATED décrivent l'origine de l'information et restent distincts.
Un score de complétude peut aider à repérer les fiches à enrichir ; il ne justifie pas le rejet d'un bon exercice incomplet.

## Tolérance aux échecs
Chaque tentative conserve état, date, erreur et prochaine action éventuelle. Délais et nombre d'essais bornés par source. Respecter les restrictions et les indications de temporisation ; ne pas contourner un accès.
Une source exigeant un compte ou un paiement est inscrite dans la liste des accès restreints ; poursuivre les sources indépendantes.
Une reprise ne doit ni refaire tous les téléchargements, ni écraser une validation coach.
Les fichiers bruts restent locaux par défaut ; leur présence sur GitHub dépend des droits, du volume et de l'utilité du partage.

## Ordre de travail immédiat
1. Reprendre un échantillon représentatif de l'existant : fiche PDF, document de séance, page HTML et vidéo avec texte accessible.
2. Construire et vérifier capture, journal de traitement, qualification et couverture par champ sur cet échantillon.
3. Corriger les pertes entre extraction, base et rendu. Certains champs conservés dans le JSON ne sont pas encore affichés.
4. Gérer les révisions attribuées sans écrasement, puis enrichir les 60 fiches existantes et leurs familles.
5. Porter les filtres utiles dans le lecteur v2.
6. Reprendre l'expansion avec les mêmes exigences, en mesurant richesse et accessibilité plutôt que le seul nombre de fiches.

## Autonomie et échanges
Décider seul des choix techniques réversibles. Pas de demande de validation par table, fichier ou exercice importé.
Solliciter l'utilisateur uniquement pour authentification, permission nécessaire, dépense, décision irréversible ou arbitrage fonctionnel/pédagogique réel.
Aucun message envoyé à des tiers sans autorisation explicite.
Les bilans distinguent sources analysées, ressources collectées, variantes extraites, fiches suffisamment détaillées, contenus bloqués et interventions utiles. Une petite hausse de compteur n'est pas une preuve de MVP terminé.
Ne pas promettre une exécution permanente : les reprises dépendent de l'environnement et du mécanisme de suivi disponible.

## Critère de fin du MVP
Chaîne démontrée sur plusieurs types de sources, reprise après échec vérifiée, provenance consultable, fiches suffisamment riches pour des préparations réelles, recherche utilisable et documentation de reprise.
La validation pédagogique reste attribuée aux coachs. Les limites et les accès restreints sont livrés avec le résultat, sans attente bloquante sur chaque source.
