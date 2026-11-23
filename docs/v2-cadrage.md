# Cadrage v2 — l’app club « SportEasy du rugby »

**Statut.** Cadrage produit, architecture et roadmap de la v2. Aucun code v2 n’est écrit ici : ce document est la base du charter v2 à valider. Les choix qui relèvent de l’utilisateur sont marqués **EN ATTENTE** (jamais de décision en silence).

**Rapport détaillé** (recherche, sources, audit du socle V1, protocoles) : `rapport-agent-v2.md`, hors dépôt.

## 1. Objectif et demande

Demande utilisateur (2026-11-22, verbatim) :

> « Faire une app ressemblant à SportEasy — calendrier, présences, statistiques, personnalisation de l’UI en fonction du club enregistré avec logo et couleur du club, gestion multi-rôles. L’objectif est d’avoir un SportEasy mais spécial rugby, avec en complément fiches conseil (digests dispo) et création de séances (enregistrement). »

La v2 est donc une **application club multi-rôles** qui s’appuie sur la V1 (bibliothèque + constructeur de séance). La V1 reste le « moteur séance » ; la v2 ajoute le « tissu club » : qui fait quoi, pour qui, quand, et comment le club se présente.

### Ce que la V1 apporte déjà

| Bloc | État V1 (vérifié) | Rôle en v2 |
| --- | --- | --- |
| Catalogue | 172 fiches (163 visibles, 9 incomplètes), 22 familles, 26 tags (17 compétences × 9 formes de jeu), provenance et états qualité par champ | Source des digests conseil ; fiches consultables par les parents/éducateurs |
| Constructeur de séance | Trame U8 90/70/20/50, validateur structurel (`session_plan.py`), minutage dérivé, brouillons et propositions par compte, snapshot immuable (D1) | Cœur de la création de séance « avec enregistrement » |
| Authentification | PBKDF2-HMAC-SHA256 (600 k itérations), jeton signé stateless, cookie HttpOnly, anti-énumération | Socle d’identité à étendre en multi-rôles / multi-club |
| Partage de séance | PDF A4 (html2canvas + jsPDF), Web Share API, repli WhatsApp **manuel** (message texte, aucun lien wa.me) | Base du partage terrain par famille |
| Serveur | Python stdlib, wsgiref, port 8347, front Next.js en export statique servi par le serveur, SQLite local | Socle à durcir pour la prod (voir § 5.5) |
| Scoping | Strictement privé par compte (404 pour un brouillon d’un autre compte, C1) | Pattern à généraliser en scoping par club |

Ce qui **n’existe pas** en V1 et fait le cœur de la v2 : entité « club » (le champ `club` actuel est un libellé libre qui n’ouvre aucun accès), rôles, calendrier, présences, statistiques, joueurs/parents, theming, liens de reprise entre propositions.

## 2. Comparaison produit : SportEasy / V1 / v2

**Note sources.** Les outils web étaient en panne pendant cette exécution (WebSearch/WebFetch : erreurs de passerelle) : la connaissance de SportEasy ci-dessous provient de la demande utilisateur et de connaissances générales, **aucune source n’a pu être consultée ni citée dans ce run**. Chaque ligne est donc une cible de cadrage à valider, pas un fait documenté — à vérifier avant les arbitrages produit définitifs (aucun prix, nombre d’équipes ou détail contractuel n’est avancé ici).

| Fonction | SportEasy (à vérifier) | V1 | v2 cible |
| --- | --- | --- | --- |
| Calendrier | Calendrier club + équipes, publication d’événements | Aucune (seule la trame 90/70 de la séance) | **Module Calendrier** : séances, plateaux, événements ; vues par rôle |
| Présences | Appel des joueurs (app mobile) | Aucune | **Module Présences** : pointage par l’éducateur à la séance, vue parents, conservation |
| Statistiques | Stats joueurs, classements (football) | Aucune (le validateur est structurel uniquement) | **Module Statistiques** : agrégats de présence et de régularité uniquement — pas de score individuel de performance |
| Communication | Actualités, chat, notifications | Aucune | Hors v2 (candidat v3, voir § 7) |
| Dossier joueur | Profil joueur (infos, photos, historique) | Aucune | Dossier joueur = identité + catégories/saisons + historique de présence (pas de note de performance) |
| Adhésion / paiement | Inscription et paiement en ligne | Aucune | Hors v2 (obligations légales distinctes ; candidat v3) |
| Portail parents | App parents | Aucune | Accès lecture limité aux données de leurs enfants |
| Personnalisation club | Badge/logo du club dans l’app | Aucune | Logo + couleurs par club (option A runtime, § 3.4) |
| Multi-rôles | Rôles par club | Compte simple, espace strictement privé | 3 rôles + affiliations club/saison (§ 3.5) |
| Séances / entraînement | Fiches d’entraînement | **Cœur de la V1** (catalogue, constructeur, PDF, validation) | Hérité + enregistrement versionné + reprise avec lien d’origine |

### Spécificités rugby mini (U6–U12) à prendre en compte

- U8 = les 7–8 ans (cible V1) ; U6 = 5–6 ans. Les formats de match sont simplifiés pour les plus jeunes et les plateaux sont l’événement territorial ; les licences FFR conditionnent la participation. Les détails de format sont à vérifier auprès de la FFR (aucune source consultée dans ce run).
- Les présences servent à : prévoir le matériel (kit par enfant), la sécurité (savoir qui est là), et les effectifs de plateau. Ce sont les trois justifications produit du module.
- Contrairement au football amateur, **la statistique individuelle de performance n’est pas pratiquée en rugby mini** : la métrique pertinente est la régularité de présence et la participation. C’est un choix produit recommandé (et cohérent avec le RGPD, § 4), pas un fait établi — à valider avec les éducateurs.
- La V1 connaît déjà la notion de **catégorie** (`comptes.categorie`, liste contrôlée U6…U18 + Autre) : elle devient la colonne vertébrale du modèle club.

## 3. Spécification par module

### 3.1 Calendrier

- **Objets** : la saison (période), l’équipe (catégorie × saison), la séance (créneau + lieu + équipe), le plateau/événement (date + lieu + équipes concernées).
- **Source de vérité** : les séances planifiées sont des séances V1 enregistrées (plan 70/90 validé) — le calendrier est une **vue** des séances, pas un second stockage de plans. Un plateau n’est pas une séance : il est rattaché aux équipes concernées.
- **Droits** : voir § 3.5. Les parents voient le calendrier de la/leur catégorie ; l’éducateur le sien ; l’admin club le club entier.
- **Récurrence** : pas d’objet « récurrent » en base — chaque séance est une instance explicite (simplicité ; la création rapide se fait par reprise de la séance précédente, § 3.7).
- **Acceptation** : un parent peut voir, pour la semaine, les séances et plateaux de son enfant sans compte d’un autre club ; une séance modifiée par l’éducateur est visible par les parents à la prochaine ouverture (pas de push en v2).

### 3.2 Présences

- **Donnée stockée** : un enregistrement par (joueur, séance) : statut `PRESENT` / `ABSENT` / `EXCUSE` / `INCONNU`, par qui, quand. **Rien d’autre** : pas de géolocalisation, pas d’heure d’arrivée, pas de lieu. La donnée de « localisation » est le point le plus sensible d’un app pour mineurs : minimisation stricte (RGPD, § 4).
- **Saisie** : par l’éducateur en début de séance (liste des joueurs de l’équipe, pointage rapide). L’absence non justifiée reste `ABSENT` ; la justification par la famille passe par un statut `EXCUSE` saisi par le parent (pas de messagerie : le parent le fait dans l’app).
- **Conservation** : durée de l’adhésion de l’enfant + **1 an** (Q3 tranchée par l’user le 2026-11-23 : reco confirmée, à faire valider par le club).
- **Accès** : le parent uniquement pour ses enfants ; l’éducateur pour son équipe ; l’admin pour le club. Pas de vue « tout le club » pour un parent.
- **Acceptation** : le taux de présence par joueur est calculable depuis les seules données stockées ; un test croise les tenues (un parent ne voit pas le tableau d’un autre enfant).

### 3.3 Statistiques

- **Principe** : agrégats calculés **à la volée** depuis les données stockées (présences, séances). Aucune « table de stats » où l’on stockerait un score : on ne crée pas de données nouvelles sur des mineurs.
- **Ce qui est agrégé (v2)** : nombre de séances, présences, taux de présence, régularité (tendance sur la saison), participation aux plateaux.
- **Ce qui est exclu** : tout score individuel de performance, de « niveau » ou de forme ; toute donnée de santé, de vitesse, de gabarit ; tout classement publié. Justification : rugby mini + RGPD (le profiling de mineurs est le point le plus exposé, § 4). À valider avec les éducateurs : ils peuvent vouloir des indicateurs de progression — le cas échéant, ils seront qualitatifs et saisis par l’éducateur (pas calculés), et **EN ATTENTE** en v2.
- **Qui voit** : le parent ses enfants uniquement ; l’éducateur son équipe (agrégats par joueur de son équipe) ; l’admin le club. Aucune stat n’est exportable « au club entier » pour tous.
- **Acceptation** : aucun champ stocké de performance individuelle ; les agrégats se recalculent après suppression d’une présence (test) ; pas de donnée de santé nulle part dans le modèle.

### 3.4 Personnalisation UI par club (logo + couleurs)

Trois options, avec leur arbitrage :

| Option | Principe | Avantages | Inconvénients |
| --- | --- | --- | --- |
| **A. Variables CSS runtime (recommandée)** | L’API retourne le thème du club actif (`couleur1`, `couleur2`, logo) ; le front (SPA embarquée dans l’export statique) applique des variables CSS ; logo servi par le serveur | Aucun build supplémentaire, thème instantané, compatible avec l’export statique V1, coût zéro | Le front doit gérer l’absence de logo (repli au thème par défaut) ; le logo est un fichier à stocker/valider côté serveur |
| B. Build par club | Un `next build` par tenant | Thème « natif » | Multiplication des builds et de la CI ; incompatible avec l’export statique unique actuel ; surcoût inutile à cette échelle |
| C. Un domaine par club | Sous-domaine par club | Marquage fort | DNS, certificats, infra supplémentaire ; ne répond pas au besoin exprimé (logo + couleurs) |

Recommandation : **option A**. Règles associées : logo en SVG ou PNG ≤ 500 Ko, validé côté serveur (type, taille, pas d’exécutables) ; couleurs hexadécimales ; repli à un thème par défaut si le club n’en a pas ; le thème s’applique à toute la surface de l’app pour le club actif. Le logo n’est pas une donnée personnelle (marque du club) — pas de contrainte RGPD spécifique.

**Acceptation** : un club avec logo + 2 couleurs voit son thème partout (capture d’écran de recette) ; un club sans logo utilise le thème par défaut sans erreur.

### 3.5 Gestion multi-rôles

**Choix structurel recommandé** : les mineurs **n’ont pas de compte**. Les comptes appartiennent aux adultes (éducateurs, administrateurs, parents) ; les joueurs sont des **entités de données** rattachées à leurs représentants légaux. C’est le choix le plus protecteur (moins de comptes = moins de surface d’attaque, moins de données) et le plus usuel dans ce type d’app — **validé par l’user le 2026-11-23 (Q4 tranchée : reco confirmée)**. Les parents ont un accès lecture limité (calendrier, séances, présences, stats, digests), sans messagerie.

| Rôle | Qui | Ce qu’il fait |
| --- | --- | --- |
| `ADMIN` (admin club) | Le/les responsable(s) du club | Gère les affiliations (éducateurs, parents), le thème club, le catalogue d’équipes/saisons, approuve les digests |
| `COACH` (éducateur) | L’éducateur d’une ou plusieurs catégories | Crée/édite les séances de ses équipes, pointe les présences, propose les digests, voit les stats de ses équipes |
| `PARENT` (parent) | Le représentant légal d’un ou plusieurs enfants | Voit calendrier, séances (PDF), présences, stats et digests **de ses enfants uniquement** ; justifie une absence (`EXCUSE`) |

**Affiliations** (le lien rôle ↔ périmètre, toujours bornées par club et saison) :

- `membres` : (compte, club, rôle, active) — un compte peut être `COACH` dans un club et `PARENT` dans un autre (ex. deux parents qui s’entraînent).
- `equipes` : (club, saison, catégorie U6…U12) — l’éducateur est rattaché à des équipes ; le joueur aussi (son équipe de la saison).
- `joueurs` : (nom, prénoms, date de naissance, licence FFR optionnelle, équipe/saison) + rattachement aux comptes parents (1 ou 2).
- `saisons` : (club, début, fin) — la catégorie d’un joueur est **par saison** (un enfant U8 en 2026-27 est U10 en 2028-29).

**Matrice des droits par module**

| Module | ADMIN | COACH | PARENT |
| --- | --- | --- | --- |
| Calendrier | voir tout le club | voir ses équipes | voir les catégories de ses enfants |
| Séances | voir/éditer tout | créer/éditer ses équipes, enregistrer | voir (PDF) les séances de ses enfants |
| Présences | voir tout | pointer ses équipes | voir ses enfants ; poser `EXCUSE` pour ses enfants |
| Statistiques | agrégats club | agrégats de ses équipes | ses enfants uniquement |
| Digests | approuver/envoyer | proposer | recevoir (consulter) |
| Personnalisation club | éditer logo/couleurs | — | — |
| Affiliations | gérer (inviter, retirer) | — | — |

**Spécificités rugby** : un club typique U6–U12 a 3 à 6 catégories actives ; un éducateur est rarement polyvalent sur toute la tranche (l’U8 a ses contraintes de format et de sécurité) ; les saisons correspondent à l’année civile de la FFR. Les rôles ne sont pas « joueurs » : il n’y a pas de compte mineur.

**Acceptation** : un parent inscrit voit zéro donnée d’un autre enfant (test de scoping) ; un éducateur ne peut ni créer ni voir une séance d’une équipe qui n’est pas la sienne (test) ; un compte peut être `COACH` et `PARENT` (test).

### 3.6 Digests de fiches-conseil

- **Contenu** : une sélection de fiches du catalogue V1 (172 fiches, 163 visibles) par catégorie et par période, tirée des tags (17 compétences × 9 formes de jeu) et des fiches conseil (`coach-cues.json`, 20 fiches).
- **Règle de curation — EN ATTENTE** (Q6, seule question restée ouverte après l’arbitrage user du 2026-11-23) : (a) l’éducateur compose manuellement le digest de son équipe (recommandé en premier : simple, pédagogique, zéro algorithme) ; (b) une suggestion automatique par tags + saison ; (c) les deux (suggestion + ajustement). Explication fournie à l’user, retour (a)/(b)/(c) attendu.
- **Circuit** : proposition (éducateur) → approbation (admin) → consultation (parents + éducateurs de la catégorie). Le digest est **immuable une fois publié** (même principe D1 que les propositions V1) ; sa source = identifiants de fiches V1 (pas de copie du texte).
- **Support** : page dans l’app + PDF (réutilise le pipeline `web/lib/pdf.ts`).
- **Acceptation** : un digest publié est lisible par les parents de la catégorie ; un digest ne peut référencer que des fiches `default_visible` (test) ; le PDF reprend les fiches sélectionnées.

### 3.7 Création de séance « avec enregistrement »

« Enregistrement » signifie quatre choses précises (chaque élément a un fondement V1 ou une décision v2) :

1. **Historique immuable** : une séance enregistrée n’est plus modifiable — on la rejoue ou on en crée une dérivée. La V1 a déjà le snapshot immuable (D1) ; la v2 l’étend au contexte club (équipe, date, lieu).
2. **Versionning des brouillons** : la V1 écrase le brouillon à chaque sauvegarde (un seul `saved_at`) ; la v2 garde un historique par brouillon (liste des versions, restauration possible). Décision v2 : la table `historique_brouillons` (n° de version + plan + horodatage).
3. **Reprise avec lien d’origine** : « reprendre une proposition partagée crée une nouvelle séance qui conserve un lien vers l’original » est déjà le produit visé (PRODUCT_SCOPE) — mais **le lien n’est persisté nulle part en V1** (aucune colonne parent dans `propositions`). La v2 ajoute `source_proposal_id` (ou `source_seance_id`) : c’est un corrigendum de la V1, pas une invention.
4. **Publication vers le club** : une séance enregistrée par un éducateur devient consultable par les parents de l’équipe (calendrier + fiche + PDF), sans créer de compte enfant.

**Acceptation** : la reprise d’une séance produit une nouvelle séance dont le lien d’origine est persisté et affiché (test) ; l’historique d’un brouillon conserve les N versions précédentes (test) ; une séance enregistrée est immuable (toute modification passe par une dérivée, test).

## 4. Données et vie privée (RGPD) — section obligatoire

**Préambule.** Les textes cités (RGPD, CNIL) sont des connaissances générales de l’agent ; **aucun site n’a pu être consulté dans ce run** (panne d’outils web) : les numéros d’articles et règles seront **re-vérifiés à l’implémentation** avec les sources officielles avant de figer la conformité. Rien dans ce document ne remplace un conseil juridique.

### 4.1 Cartographie des données

| Donnée | Concerné | Sensibilité | Base légale recommandée |
| --- | --- | --- | --- |
| Nom, prénom, date de naissance du joueur | Mineur | Données personnelles d’un enfant (< 13 ans) | Consentement du représentant légal (formulaire) + intérêt légitime du club pour l’organisation |
| Numéro de licence FFR | Mineur | Donnée tierce (la FFR est le responsable de la donnée licence) | Le club la reçoit pour organiser les plateaux ; elle n’est pas réutilisée ailleurs ; origine : liste fournie par le club. **Q7 tranchée par l’user le 2026-11-23 : affichage seulement, pas de stockage en v2** |
| Coordonnées du parent (compte) | Adulte | Personnelles | Consentement (compte) |
| Présences (date + statut) | Mineur | **Localisation d’un mineur** — minimisation stricte : date + statut seulement, pas d’heure de passage, pas de lieu, jamais de géolocalisation | Intérêt légitime (sécurité, matériel, effectifs de plateau) |
| Statistiques | Mineur | Données **dérivées** d’une personne — mêmes règles que la donnée source | Idem ; agrégat à la volée, rien de stocké |
| Logo, couleurs du club | — | Non personnelles | Hors RGPD |
| Photos | Mineur | Droit à l’image en plus | **Recommandation : aucune photo de joueur en v2** (le logo est celui du club). Si des photos deviennent nécessaires, consentement spécifique par enfant |

### 4.2 Âge, consentement, droits

- Les joueurs (U6–U12) ont moins de 13 ans : le consentement de tout service en ligne leur concernant passe par le **représentant légal** (le RGPD permet aux États de fixer un âge entre 13 et 16 ans ; en France il est fixé à **15 ans** — à re-vérifier à l’implémentation). Un formulaire papier ou en ligne signé par le parent est donc le socle, indépendamment de la question de l’âge du compte.
- Bases légales : **consentement parental** pour l’inscription et le traitement des données de l’enfant ; **intérêt légitime** pour l’organisation (présences, calendrier) avec pondération documentée. Le consentement doit être libre, spécifique, informé et **retraitable** — le retrait des parents doit être possible sans autre traitement que la cessation (et l’effacement après la fin d’adhésion + durée de conservation).
- Droits (accès, rectification, effacement, portabilité, opposition) exercés **par le parent** en tant que représentant légal. Durée de conservation : fin d’adhésion de l’enfant + **1 an** (Q3 tranchée par l’user le 2026-11-23 : reco confirmée), sauf données de licence transmises à la FFR qui suivent leurs propres règles.
- **DPIA** : le traitement à petite échelle d’un club ne l’exige probablement pas, mais il est **recommandé** (enfants + profilage exclu + conservation limitée) — le faire avant le lot 0.
- **Sous-traitance** : le club est responsable de traitement ; le développeur hébergeant le service est **sous-traitant** (article 28) → un contrat (DPA) et une information des parents en sont la conséquence. L’hébergement doit rester **dans l’UE** ; hors UE = mécanismes de transfert à formaliser.

### 4.3 Friction avec l’infra actuelle

- La V1 tourne en **local, hors ligne, sans TLS**, base SQLite sur une machine : c’est acceptable pour un outil d’éducateur, **pas pour des données de mineurs en prod** (confidentialité, intégrité, indisponibilité).
- Conséquences minimales : TLS obligatoire devant le serveur ; **sauvegardes** périodiques (la base applicative contient des données de mineurs) ; procédure d’**incident 72 h** (notification — articles 33/34 : le responsable, ici le club, doit pouvoir être notifié rapidement) ; **registre des traitements** minimal.
- À ce stade la base applicative de production est vide (0 compte) : la base de la v2 partira de zéro, sans migration de données existantes.

**Q3 tranchée par l’user le 2026-11-23 (reco confirmée)** : base légale = consentement parental + intérêt légitime comme ci-dessus ; durée de conservation = fin d’adhésion + 1 an ; visibilité = parents limités à leurs enfants, éducateurs limités à leur équipe ; formulaire de consentement à faire valider par le club.

## 5. Architecture

### 5.1 Extension de la V1 (recommandation)

Trois chemins :

| Option | Principe | Verdict |
| --- | --- | --- |
| **A. Étendre la V1 (recommandée)** | Même repo, même serveur, même base applicative : on ajoute les tables club/rôles/présences et les routes correspondantes | Le socle est validé (141 tests, auth robuste, scoping par compte déjà en place, validateur déterministe, parité Python/TS verrouillée par vecteurs). Le multi-club est un **scoping à étendre**, pas une refonte. Un seul déploiement |
| B. Nouvelle application | Nouveau repo, nouvelle auth | Double maintenance d’une auth et d’un front ; la V1 est déjà un bon socle — perte de temps pure |
| C. App compagnonne | Deux apps, partage d’identifiants | Deux déploiements, deux surfaces d’attaque pour des données qui se croisent (séances ↔ présences) ; le découpage n’apporte rien à cette échelle |

**Q1 tranchée par l’user le 2026-11-23 (reco adoptée)** : cible = pilote d’un club, architecture multi-clubs dès le lot 1. L’option A correspond — le multi-clubs n’est qu’une table `clubs` de plus ; seule la politique d’ouverture change.

### 5.2 Modèle de données cible (schéma conceptuel)

```
clubs(id, nom, ville, departement, logo_path, couleur1, couleur2, theme_json,
     contact_nom, created_at)
saisons(id, club_id, nom, debut, fin)
membres(compte_id, club_id, role[ADMIN|COACH], active, created_at)
     -- compte_id → comptes V1 (identité, mot de passe, login) — inchangé
equipes(id, club_id, saison_id, categorie[U6..U12], nom)
joueurs(id, nom, prenom, date_naissance, licence_ffr, equipe_id, saison_id)
parent_joueurs(compte_id, joueur_id, relation[PARENT_1|PARENT_2],
               consentement_date, active)
seances(id, plan_json, club_id, equipe_id, date, lieu,
         enregistree_le, enregistree_par, source_seance_id, statut)
     -- plan_json = le plan V1 validé (70/90) ; immuable si statut=ENREGISTREE
brouillons_v2 = brouillons V1 + historique_brouillons(compte_id, draft_id,
     n_version, plan_json, saved_at)
presences(joueur_id, seance_id, statut[PRESENT|ABSENT|EXCUSE|INCONNU],
     enregistee_par, enregistee_le)   UNIQUE(joueur_id, seance_id)
plateaux(id, club_id, date, lieu, equipes_json, titre)
digests(id, club_id, equipe_id, periode, fiche_ids_json, etat[BROUILLON|
     APPROUVE|PUBLIE], cree_par, publiee_le)
```

Principes hérités de la V1 et conservés : valeurs inconnues = NULL (jamais 0), provenance par champ, état de qualité, snapshot immuable, scoping strict (tout est scindé par `club_id` ; un parent ne voit que ses `joueur_id` ; un coach que ses `equipe_id`).

### 5.3 Authentification multi-rôles

L’authentification V1 est **conservée à l’identique** (PBKDF2 600 k, jeton `<compte>.<expiration>.<HMAC>`, cookie HttpOnly, anti-énumération, TTL 30 jours). On n’ajoute pas de mécanisme : on étend le **contenu** de la session :

- Le jeton reste signé par le compte ; l’app active (club + rôle) est résolue côté serveur à chaque requête depuis `membres` (pas de rôle « trusté » dans le token — un rôle retiré devient immédiatement inactif).
- `GET /api/moi` retourne la liste des clubs + rôles du compte ; le front propose le club actif.
- Un compte `PARENT` n’a pas d’entrée dans `membres` : son périmètre vient de `parent_joueurs`.

### 5.4 Theming

Option A (§ 3.4) : `GET /api/moi` (ou `GET /api/club/<id>/theme`) → `{couleur1, couleur2, logo_url}` ; le front applique `--club-primary` / `--club-secondary` en variables CSS ; le logo est servi par le serveur avec contrôle de type/taille ; repli thème par défaut. Aucun build par club.

### 5.5 Ce qui est réutilisable tel quel, et ce qu’il faut durcir (audit V1)

**Réutilisable tel quel** : l’auth complète ; le pattern de scoping par compte (→ par club) ; le moteur `session_plan.py` (déterministe, testé, parité TS verrouillée) ; le modèle de provenance/qualité du catalogue ; le pipeline de reconstruction ; le PDF + partage ; la discipline de test (141 méthodes, vecteurs partagés).

**À durcir avant la prod v2** (listés par l’audit, classés par priorité) :

1. **TLS** devant le serveur (reverse proxy) — obligatoire pour des données de mineurs.
2. **Sauvegardes** de `app.sqlite` (fichier SQLite) : sauvegarde périodique + test de restauration.
3. **Mode WAL** pour SQLite (concurrency lecture/écriture ; le mode journal par défaut est fragilisé par le thread par connexion).
4. **Timeouts de lecture** sur le serveur (wsgiref + `ThreadingMixIn` : un client lent retient un thread indéfiniment) + **rate limiting** sur `/api/auth/*` (anti brute-force ; aujourd’hui anti-énumération oui, lockout non).
5. **Procédure d’incident 72 h** + notification (le club doit être averti).
6. **Clé HMAC** de session : stockée dans la table `meta` (base locale) — acceptable, mais à externaliser (fichier hors base) si la base est exposée par une sauvegarde.
7. `content_sha256` variable selon la machine (captures locales) : sans impact en v2 (lecture seule), à savoir.

Les points 1-4 sont des **gabarits d’infrastructure**, pas du code v2 : ils entrent dans le lot de durcissement (lot 6).

## 6. Hébergement — options

| Option | Description | Avantages | Inconvénients |
| --- | --- | --- | --- |
| **1. Ferme Swarm 6 nœuds** | Le service Python + `web/out` en conteneur Docker, TLS par Traefik, domaine propre | Infra existante et maîtrisée (Swarm, Gitea, registry, CI), coût zéro, redondance sur 6 nœuds, TLS déjà en place | **Exclue par l’user le 2026-11-23** (Q2 tranchée : exposition publique validée mais **pas sur l’infra d’entreprise**) |
| 2. Cloud UE (OVH/Scaleway/Hetzner) | VPS ou service managé dans l’UE, Caddy/Traefik pour le TLS | SLA, sauvegardes natives, « propre » contractuellement (DPA avec le fournisseur) | Coût récurrent (ordre de grandeur 10-30 €/mois — à vérifier) ; nouvelle infra à gérer ; DPA à signer |
| 3. Local (machine de l’utilisateur) | Comme la V1, sur la machine locale | Le plus simple ; déjà en place | Indisponibilité dès que la machine dort (veille gérée mais non garantie 24/7) ; SPOF ; la procédure 72 h devient difficile ; pas de redondance |

**Recommandation de l’agent (avant arbitrage)** : option 1 si l’exposition publique est validée (le domaine et le TLS y sont les plus simples) ; sinon option 3 pour un pilote fermé, et option 1/2 pour la mise en prod. **Arbitrage user 2026-11-23** : l’exposition publique est **validée**, mais **pas sur l’infra d’entreprise** — l’option 1 (ferme Swarm) est exclue. Le support public concret (option 2 cloud UE, autre hébergeur…) reste à trancher et est **reporté avec Q5** (« à mettre de côté pour l’instant ») ; en attendant, l’app tourne en local (option 3, état V1).

## 7. Roadmap

Lot 0 est bloquant (arbitrages + base juridique) ; les lots 1-5 sont ordonnés par dépendance ; le lot 6 peut démarrer dès le lot 1 (durcissement en parallèle). Les durées sont des ordres de grandeur d’agent, pas des engagements.

| Lot | Contenu | Dépend de | Critères d’acceptation (vérifiables) | Risque |
| --- | --- | --- | --- | --- |
| **0. Arbitrages & base juridique** | Charter v2 validé ; DPIA recommandé fait ; formulaire de consentement parental rédigé ; mapping des données figé (hébergement : décision reportée — Q2/Q5) | — | Charter signé par l’utilisateur ; mapping + consentement relus (décision d’hébergement reportée) | Faible (du temps) |
| **1. Multi-tenant + identité club** | Tables `clubs`, `saisons`, `membres`, `equipes`, `joueurs`, `parent_joueurs` ; theming option A ; écran d’administration (clubs, affiliations) | Lot 0 | Un club de test avec 3 catégories (U6/U8/U10) ; 5 rôles créés ; thème appliqué (capture) ; **tests de scoping** (aucune fuite entre clubs) ; 100 % des tests | Moyen |
| **2. Calendrier + enregistrement des séances** | Vue calendrier (séances + plateaux) ; enregistrement = séance immuable + contexte club ; reprise avec `source_seance_id` ; versionning des brouillons ; vue parent | Lot 1 | Parcours complet « l’éducateur crée → le parent voit (PDF) » ; la reprise produit une séance liée à l’origine (test) ; l’historique conserve N versions (test) ; immutabilité (test) | Moyen |
| **3. Présences** | Pointage par l’éducateur ; statuts PRESENT/ABSENT/EXCUSE/INCONNU ; conservation ; vue parents ; `EXCUSE` par le parent | Lot 1 | Taux de présence calculable depuis les seules données stockées ; pas de donnée de localisation/horaire (test sur le schéma) ; scoping parent (test) | Moyen-haut (RGPD) |
| **4. Statistiques** | Agrégats à la volée (présences, régularité, plateaux) ; vues par rôle | Lot 3 | Aucun champ de performance individuelle stocké (test) ; recalcul après suppression (test) ; vue parent limitée à ses enfants (test) | Moyen |
| **5. Digests conseil** | Curation (règle tranchée au lot 0) ; circuit proposition/approbation/publication ; page + PDF | Lot 1 | Un digest ne référence que des fiches `default_visible` (test) ; le PDF reprend les fiches ; immuable une fois publié (test) | Faible |
| **6. Durcissement prod** | TLS ; sauvegardes + test de restauration ; WAL ; timeouts + rate limiting ; procédure d’incident 72 h + notification | Lot 1 (en parallèle) | Test de restauration réussi ; procédure d’incident documentée et simulée ; tests 100 % | Moyen-haut |

**Hors v2 (candidats v3, à ne pas ouvrir sans validation)** : communication/nouveaux/notifications ; adhésion + paiement (obligations légales distinctes : paiement, droit de rétractation) ; comptes joueurs ; stats de progression qualitatives (si les éducateurs le demandent, avec la précaution § 3.3) ; intégration SportEasy (hors périmètre V1 par décision — une API serait à auditer).

**Risque principal global** : le périmètre. SportEasy fait beaucoup ; la v2 se borne à 7 modules + durcissement. Toute fonction ajoutée (ex. « juste un chat ») réactive le RGPD (données de mineurs) et la roadmap : **chaque ajout passe par le présent document + validation utilisateur**.

## 8. Questions ouvertes — statuts

Numérotées pour le journal du checkpoint. Aucune ne peut être tranchée par l’agent ; elles bloquent les lots indiqués. **Mise à jour 2026-11-23** : l’user a tranché Q1, Q2, Q3, Q4, Q7 et reporté Q5 (colonne « Décision user ») ; **Q6 reste EN ATTENTE** (explication fournie, retour attendu).

| N° | Question | Bloque | Recommandation de l’agent | Décision user (2026-11-23) |
| --- | --- | --- | --- | --- |
| Q1 | **Cible de la v2** : le club de l’utilisateur (pilote unique) ou un produit multi-clubs dès le départ ? | Lot 0 (périmètre commercial, RGPD à l’échelle) | Pilote un club, architecture multi-clubs dès le lot 1 (le surcoût est faible — une table `clubs`) | **Tranchée — reco adoptée** : pilote un club, architecture multi-clubs dès le lot 1 |
| Q2 | **Exposition publique** : l’app est-elle accessible sur Internet (domaine, TLS) ou en réseau privé ? | Lot 0/6 (hébergement, sécurité, incident 72 h) | Oui, publique via la ferme Swarm (option 1) — sinon pilote local fermé | **Tranchée — reco modifiée** : exposition publique **oui, mais PAS sur l’infra d’entreprise** (la ferme Swarm est exclue) ; le support public concret reste à trancher, lié à Q5 |
| Q3 | **Posture RGPD** : bases légales (consentement parental + intérêt légitime ?), durée de conservation des présences (recommandée : fin d’adhésion + 1 an), qui voit les présences (recommandé : les parents limités à leurs enfants, l’éducateur à son équipe) | Lots 0, 3, 4 | Comme recommandé ; formulaire de consentement à faire valider par le club | **Tranchée — reco confirmée** |
| Q4 | **Comptes des enfants** : confirme-t-on que les mineurs n’ont pas de compte (recommandation) et que les parents ont un accès lecture limité (calendrier, séances, présences, stats, digests) sans messagerie ? | Lots 1, 3, 4 | Oui, comme spécifié § 3.5 | **Tranchée — reco confirmée** : pas de compte mineurs ; lecture parent limitée, sans messagerie |
| Q5 | **Hébergement** : ferme Swarm (recommandée) / cloud UE / local ? Et **DPA sous-traitance** : le club est-il responsable de traitement et l’agent sous-traitant — le document sera-t-il signé ? | Lot 0/6 | Ferme Swarm + DPA formel ; à défaut, cloud UE | **Reportée** (« à mettre de côté pour l’instant ») : hébergement + DPA, y compris le choix du support public consécutif à Q2 |
| Q6 | **Règle de curation des digests** : composition manuelle par l’éducateur (recommandée en premier), suggestion automatique par tags, ou les deux ? | Lot 5 | Manuel d’abord, automatique ensuite | **EN ATTENTE** — l’user a demandé une explication ; options : (a) manuel, (b) auto par tags+saison, (c) les deux (reco : (a) d’abord) ; retour attendu |
| Q7 | **Données de licence FFR** : quelle est la source de vérité (liste fournie par le club ? import ?) et le numéro de licence sera-t-il stocké en v2 ou seulement à l’écran ? | Lot 3 | Pas de stockage en v2 (affichage uniquement) — minimisation | **Tranchée — reco confirmée** : pas de stockage du n° licence FFR en v2, affichage seulement |

## 9. Références

- [Périmètre produit](PRODUCT_SCOPE.md), [Interface des séances](INTERFACE_SEANCES.md), [Contrat de lecture](CONTRAT_APPLICATION.md), [Décisions](DECISIONS.md) — documentation active de la V1.
- Audit du socle V1 (lecture seule, agent dédié de cette session) : rapport complet dans le rapport hors dépôt, sections A-G.
- Rapport détaillé de ce cadrage (recherche, sources, protocoles, points non trouvés) : `rapport-agent-v2.md` (hors dépôt).
