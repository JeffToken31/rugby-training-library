# Décisions produit

## 2026-11-17 — Authentification simple des éducateurs en V1

**Décision.** La V1 comprend une authentification simple des éducateurs pour identifier l’auteur, conserver ses brouillons et rattacher ses propositions à son compte. La gestion des clubs, les rôles avancés et les invitations restent hors périmètre.

**Impact.** Le choix du mécanisme d’authentification, du stockage et des règles précises de consultation et de reprise reste à définir. Cette décision décrit le produit visé, pas une fonctionnalité déjà disponible.

## 2026-11-17 — Représentation du créneau dans les brouillons

**Décision.** Le brouillon porte `creneau_min` (créneau de la séance, entier strictement positif) ; `duration_min` reste le temps planifié, égal à la somme des blocs. La marge est dérivée (créneau − planifié), jamais stockée. Un temps planifié supérieur au créneau déclenche un avertissement non bloquant ; un créneau absent ou invalide est une erreur. Un bloc sans durée reste écriable : le total est alors marqué partiel par un avertissement qui nomme le réglage manquant.

**Raison.** L’audit du socle (mission `audit-socle-70-90`) a montré que la cible 70/90 n’existait ni dans le code ni dans les données et que le validateur la rejetait par sa seule égalité stricte ; l’arbitrage A1–A3 du checkpoint du 17 novembre choisit un champ explicite plutôt qu’une marge stockée et un avertissement plutôt qu’un refus, pour rester conforme au retour informatif demandé par [l’interface des séances](INTERFACE_SEANCES.md#trame-et-calcul-du-temps).

**Impact.** Le brouillon d’exemple est remplacé par la [trame de référence](#2026-11-17-trame-u8-et-marge-operationnelle) (70 planifiées sur 90, ateliers en deux rotations) ; la question ouverte « Créneau et temps planifié » est clôturée ; le [contrat](CONTRAT_APPLICATION.md#exemple-structurel-et-contrôles-existants) décrit la nouvelle représentation.

## 2026-11-17 — Trame U8 et marge opérationnelle

**Décision.** Pour 90 minutes de créneau, recommander environ 50 minutes d’opposition et deux ateliers pour environ 20 minutes au total. La trame de référence planifie environ 70 minutes, avec environ 20 minutes de marge. Les affectations simultanées se comptent une fois par rotation et le constructeur laisse l’éducateur ajuster la trame.

**Raison.** Les retours terrain et une formation d’éducateur ont conduit à donner davantage de place à l’opposition et à ménager du temps pour la logistique et les imprévus.

**Impact.** Cette décision remplace la trame à trois ateliers de 6 à 8 minutes, la récréation fixe et le remplissage systématique des 90 minutes du [cadrage de septembre](../archive/docs-legacy/PROJECT_2026-09-16.md) et de son [exemple](../archive/docs-legacy/SEANCE_EXEMPLE.md). Voir la [trame active](INTERFACE_SEANCES.md#trame-et-calcul-du-temps) et sa [représentation dans les brouillons](#2026-11-17-representation-du-creneau-dans-les-brouillons).

## 2026-11-17 — Bibliothèque et préparation de séances comme cœur du MVP

**Décision.** Priorité à la recherche d’ateliers et à la préparation mobile de séances depuis le corpus existant. L’éducateur garde la main sur ses brouillons et crée une nouvelle proposition pour reprendre une séance partagée. Les réglages d’une séance restent distincts des données sources.

**Raison.** Répondre aux deux usages prioritaires avec le corpus disponible et permettre aux éducateurs de réutiliser leurs propositions.

**Impact.** Les objectifs quantitatifs de collecte et les scénarios de gestion de club ou de saison documentés en septembre restent historiques. Le [périmètre actuel](PRODUCT_SCOPE.md) situe l’assistance IA après le parcours manuel.

## Questions ouvertes

| Sujet | Décision ou vérification attendue |
| --- | --- |
| Créneau et temps planifié | Clôturée le 17 novembre : [représentation du créneau dans les brouillons](#2026-11-17-representation-du-creneau-dans-les-brouillons). |
| Sauvegarde et accès | Définir le mécanisme d’authentification simple, le stockage, qui peut consulter ou reprendre une proposition et ce qui doit être conservé si une fiche évolue. |
| Partage | Déterminer quels modes livrer en premier et préciser le contenu de la fiche PDF ou imprimée pour le terrain. |
| Réglages de terrain | Confirmer les valeurs initiales utiles pour l’effectif, les groupes, les éducateurs, le matériel et les règles de contact du club. |
