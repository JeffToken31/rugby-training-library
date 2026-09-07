# Captures et recherche — état opérationnel

## Livré
La recherche v2 combine texte, statut, thème, âge source (recherche textuelle), matériel, durée maximale et nombre de joueurs. Tri par titre, durée ou effectif, inconnues en dernier. Les chiffres source sont séparés des propositions U8 par --basis.

Cas vérifié : passe, 7 minutes maximum, 8 enfants, paramètres proposés → deux fiches (rc-pairs et rc-piggy). Le même filtre sur les chiffres sources ne renvoie aucun résultat. Cela signale une absence de données compatibles connues, pas une impossibilité pédagogique.

capture_resources.py traite des ressources déjà enregistrées. Chaque tentative réseau est datée en base, avec succès ou erreur. Lecture des règles robots, délai réseau de 15 secondes, limite de 5 Mio, formats HTML/PDF/texte seulement. Pas de téléchargement vidéo. Après un blocage, les autres ressources restent traitables ; les autres demandes au même hôte sont reportées dans ce lot.

La capture conserve URL finale, type, taille, empreinte SHA-256 et fichier local. Une reprise vérifie les octets avant réutilisation. Le texte HTML peut être réextrait de cette copie locale ; scripts et styles sont exclus.

## Essai réel
- rc-pass-start-source : page HTML capturée, 84 340 octets. Réutilisation vérifiée sans nouvel accès réseau, texte extrait localement.
- ffr-plan2023 : accès à la collecte interdit par robots.txt ; tentative enregistrée BLOCKED. Aucun PDF téléchargé par ce collecteur.

Les fichiers bruts et textes restent locaux dans data/raw et ne sont pas envoyés sur GitHub. La base locale conserve les journaux ; les lots éditoriaux versionnés restent reconstruisibles indépendamment.

## Limites
Il s'agit du premier collecteur, pas encore d'une collecte massive.
L'extraction HTML produit du texte incluant potentiellement de la navigation ; elle n'est pas encore une extraction structurée des consignes, objectifs et critères de réussite.
Les occurrences historiques ne sont pas automatiquement rattachées à cette nouvelle capture sans vérification de leur correspondance.
Pas encore de réextraction PDF, de traitement de sous-titres temporisés ni de gestion durable des files d'attente. Le champ âge source est textuel et ne vaut pas validation U8.
Une durée maximale connue ne garantit pas que l'exercice ne peut pas être adapté ; une proposition garde son origine distincte.

## Vérifications
25 tests passants, dont séparation des filtres source/proposition, réutilisation sans réseau, réextraction du texte et poursuite après blocage.
La base reste à 60 fiches ; aucun exercice ajouté pour cette étape d'outillage.
