# Consignes de contribution

- Lire [PROJECT.md](PROJECT.md) avant toute intervention. Les documents référencés comme actifs priment sur [les archives](archive/README.md). Signaler toute contradiction ou décision manquante et demander un arbitrage avant de changer le périmètre.
- Préserver les parcours sur téléphone. Limiter les changements au besoin exprimé et les vérifier avec les contrôles du dépôt.
- Préserver la provenance et les valeurs inconnues. Distinguer source, observation et adaptation. Les réglages d’une séance restent dans la séance. Pour corriger le corpus, intervenir sur les entrées versionnées et régénérer les exports.
- Utiliser Python standard et SQLite, sous WSL pour le travail local, sans sudo. Voir le [guide de reconstruction](README.md). Garder les captures brutes en local et exclure secrets et données personnelles d’enfants. Travailler dans une copie du dépôt, hors des fichiers synchronisés du projet ChatGPT.

## Reprise du développement avec QwenCoder

Avant toute intervention, lire [PROJECT.md](PROJECT.md) et les documents actifs qu’il référence. Les archives servent à comprendre l’historique. Limiter chaque intervention au lot demandé et attendre une demande explicite avant d’élargir le périmètre.

### Ordre de livraison

1. **Catalogue mobile** — Rendre les cartes lisibles sur téléphone, avec recherche, filtres principaux et accès rapide aux médias disponibles.
2. **Fiche atelier** — Présenter pour le terrain l’objectif, l’organisation, le déroulement, les consignes et les variantes. Afficher les sources, les médias disponibles et les informations inconnues.
3. **Constructeur de séance** — Composer une séance par blocs et rotations. Garder la trame U8 ajustable avec environ 70 minutes planifiées sur un créneau de 90 minutes, dont environ 50 minutes d’opposition et deux ateliers sur environ 20 minutes au total. Calculer la marge à partir du créneau et du temps planifié. Compter une seule fois les affectations simultanées d’une même rotation.
4. **Sauvegarde et reprise** — Enregistrer et rouvrir un brouillon, le dupliquer et créer une nouvelle proposition à partir d’une séance existante en conservant le lien vers l’original.
5. **Authentification simple** — Identifier l’éducateur et rattacher ses brouillons et ses propositions à son compte, selon les arbitrages de la documentation active.

Commencer par le catalogue mobile. Livrer chaque lot comme un parcours utilisable et testé avant de passer au suivant. L’assistance IA et le partage PDF avancé viennent après ces cinq lots, sur demande explicite.

### Déroulement de chaque lot

- Présenter brièvement ce qui existe, ce qui est réutilisable et ce qui manque pour le lot. Signaler les décisions ouvertes qui bloquent la livraison.
- Définir des critères d’acceptation vérifiables, dont le parcours sur téléphone et les cas limites pertinents.
- Développer le lot en s’appuyant sur le socle et les contrats existants. Corriger les problèmes d’interface dans la couche concernée. Ne pas modifier les données sources pour contourner un problème d’interface. Conserver les adaptations de durée, d’effectif ou d’organisation dans la séance.
- Exécuter les contrôles du dépôt et vérifier le parcours défini. Corriger les écarts, relancer les tests concernés et indiquer les résultats ainsi que les vérifications encore à faire.
