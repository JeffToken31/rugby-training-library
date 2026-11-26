// Lot 3 — constructeur de séance (vue S6). La trame U8 70/90 est servie
// telle quelle comme gabarit de départ (POST /api/seances/valider en
// référence). Édition par blocs : titre, créneau, effectifs par groupe,
// durée, rotations des ateliers (travail / transition), exercices.
// La minutage (créneau, planifié, marge, opposition) est recalculée à
// chaque frappe — miroir exact du serveur (web/lib/session.ts) — et le
// bouton « Vérifier (serveur) » reste la référence.
// Le picker n'attribue que : un slot qui porte un exercice le conserve
// jusqu'à ce qu'on le remplace (jamais de variant_id null → pas
// d'« Exercice inconnu : None » côté serveur).
// Lot 4 : le brouillon est sauvegardé à chaud dans localStorage (un seul par
// navigateur), proposé à la réouverture dans un bandeau (reprendre / repartir
// de la trame U8) — jamais de perte silencieuse. L'export/import est du JSON
// brut, même contrat que le validateur.
// Lot 5 : si un compte est connecté (prop « moi »), la section « Sauvegarde
// et reprise » ajoute l'enregistrement sur le compte — brouillons par compte
// (B1) et propositions immuables validées à l'enregistrement (D1), mêmes API
// que webapp.py. Le fichier localStorage reste le filet hors connexion.

import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import type {
  Card,
  CatalogueView,
  ConseilCoach,
  Equipe,
  Fiche,
  GroupeEquipe,
  SeanceCheck,
  SessionBlock,
  SessionPlan,
} from "../lib/types";
import { fetchConseils, fetchFiche, fetchTrameU8, validerSeance } from "../lib/api";
import { clearDraft, loadDraft, parseImport, saveDraft } from "../lib/draft";
import type { SavedDraft } from "../lib/draft";
import {
  ajouterCoach,
  chargerBrouillon,
  chargerProposition,
  creerEquipe,
  creerProposition,
  listerBrouillons,
  listerCoachs,
  listerEquipes,
  listerPropositions,
  sauvegarderBrouillon,
  supprimerBrouillon,
} from "../lib/auth";
import type {
  BrouillonRef,
  CoachRef,
  CorpsEquipe,
  Moi,
  Proposition,
  PropositionRef,
} from "../lib/auth";
import {
  atelierIdsDuPlan,
  generateSessionPdf,
  renderSheetPages,
} from "../lib/pdf";
import {
  basculerPresences,
  joueursCoches,
  parserJoueurs,
  repartirEffectif,
  redistribuerPresences,
  roundRobinJoueurs,
} from "../lib/equipes";
import type { PrefillPayload } from "../lib/prefill";
import {
  lienWhatsApp,
  partagerPieceJointe,
  recapTextePlan,
} from "../lib/share";
import { selectCards } from "../lib/filter";
import { BADGE_LABELS, cardDurationLabel } from "../lib/format";
import { etatParIdDe, KIND_LABELS, validerLocale } from "../lib/session";

type PickerTarget =
  | { kind: "slot"; blockIndex: number; roundIndex: number; slotIndex: number }
  | { kind: "block"; blockIndex: number };

const BADGE_CLASS: Record<string, string> = {
  INCOMPLETE: "badge-red",
  PROPOSED_OBJECTIVE: "badge-amber",
  REPORTED_OBSERVATION: "badge-slate",
};

// Catégories proposées dans le formulaire d'équipe — même liste que la
// validation côté compte (app_store.CATEGORIES).
const CATEGORIES_UI = [
  "babys",
  "U6",
  "U8",
  "U10",
  "U12",
  "U14",
  "U16",
  "U18",
  "Autre",
];

function clonePlan(plan: SessionPlan): SessionPlan {
  return structuredClone(plan);
}

// Horodatage lisible d'une sauvegarde (ISO → « 19/11/2026, 14:03 »).
function savedLabel(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("fr-FR", { hour12: false });
}

export default function SessionBuilder({
  view,
  moi,
  prefill,
}: {
  view: CatalogueView | null;
  moi: Moi | null;
  // Lot L4 : snapshot écrit par la page « club » — appliqué à la première
  // ouverture, sur la copie de la trame (la trame vierge reste le retour).
  prefill?: PrefillPayload | null;
}) {
  const [plan, setPlan] = useState<SessionPlan | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [picker, setPicker] = useState<PickerTarget | null>(null);
  const [pickerQuery, setPickerQuery] = useState("");
  const [serverCheck, setServerCheck] = useState<SeanceCheck | null>(null);
  const [serverTime, setServerTime] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  // Lot 4 — persistance client (localStorage) : la trame de départ est
  // conservée pour pouvoir y repartir ; un brouillon existant est proposé
  // dans un bandeau avant de continuer (jamais de perte silencieuse).
  const [initialDraft, setInitialDraft] = useState<SessionPlan | null>(null);
  const [pendingDraft, setPendingDraft] = useState<SavedDraft | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Lot 5 — persistance par compte (si connecté) : les listes de brouillons
  // et de propositions sont légères (sans plan, comme l'API) ; le résultat
  // de la dernière proposition est affiché en place (D1 : snapshot immuable,
  // validité figée au moment de l'enregistrement).
  const [brouillons, setBrouillons] = useState<BrouillonRef[]>([]);
  const [propositions, setPropositions] = useState<PropositionRef[]>([]);
  const [compteBusy, setCompteBusy] = useState(false);
  const [compteMsg, setCompteMsg] = useState<string | null>(null);
  const [propResult, setPropResult] = useState<Proposition | null>(null);

  // Lot 7 — partage PDF d'une proposition validée : l'id de la proposition en
  // cours de génération (pour désactiver le bouton) + un message d'issue
  // (téléchargement de secours, envoi réussi, erreur).
  const [pdfBusy, setPdfBusy] = useState<number | null>(null);
  const [pdfMsg, setPdfMsg] = useState<string | null>(null);
  // Aperçu du PDF (v1.1 L1) : proposition + matière chargée + pages rendues.
  const [pdfPreview, setPdfPreview] = useState<{
    p: PropositionRef;
    prop: Proposition;
    fiches: Record<string, Fiche>;
    conseils: ConseilCoach[];
    pages: { data: string; hPx: number }[];
  } | null>(null);
  // Lien WhatsApp avec le récap, offert quand le partage a besoin d'un
  // complément (récap partagé seul, PDF téléchargé à joindre à la main).
  const [waHref, setWaHref] = useState<string | null>(null);

  // Équipes d'effectif + « coachs disponibles » (tranché 2026-11-22) : les
  // listes sont celles du compte connecté ; la séance conserve son propre
  // snapshot d'équipe (D1), et les coachs cochés alimentent `coaches`
  // (compte) + `coach_logins` (identifiants présents).
  const [equipes, setEquipes] = useState<Equipe[]>([]);
  const [coachRefs, setCoachRefs] = useState<CoachRef[]>([]);
  const [equipesMsg, setEquipesMsg] = useState<string | null>(null);
  const [showNewEquipe, setShowNewEquipe] = useState(false);
  const [formNom, setFormNom] = useState("");
  const [formClub, setFormClub] = useState("");
  const [formCat, setFormCat] = useState("");
  const [formEffectif, setFormEffectif] = useState("");
  const [formCoachs, setFormCoachs] = useState<string[]>([]);
  // Joueurs de l'équipe (lot L3, v1.1) : « prénom + nom, un par ligne ».
  const [formJoueurs, setFormJoueurs] = useState("");
  const [formBusy, setFormBusy] = useState(false);
  // Coachs sans compte (v1.1, 2026-11-24) : ajout par nom au club.
  const [coachNom, setCoachNom] = useState("");
  const [coachClub, setCoachClub] = useState("");
  const [coachBusy, setCoachBusy] = useState(false);
  const [coachMsg, setCoachMsg] = useState<string | null>(null);

  // Présences à l’attachement (lot P5, workflows 2026-11-26) : la liste
  // complète des joueurs de l’équipe attachée (null = rien à afficher),
  // les cases par joueur (map vide = tous présents), et — quand le
  // préremplissage est en mode « groupes nommés » — la source de
  // répartition, pour qu’un joueur récoché revienne dans SON groupe.
  const [joueursEquipe, setJoueursEquipe] = useState<string[] | null>(null);
  const [presences, setPresences] = useState<Record<string, boolean>>({});
  const [groupesSource, setGroupesSource] = useState<GroupeEquipe[] | null>(
    null
  );

  useEffect(() => {
    let live = true;
    fetchTrameU8()
      .then((p) => {
        if (!live) return;
        // La trame vierge reste le point de retour ; le préremplissage (lot
        // L4) s'applique sur une copie, avec la même logique que attachEquipe.
        setInitialDraft(clonePlan(p));
        if (prefill) {
          const base = clonePlan(p);
          base.team = prefill.team;
          const groupes = base.groups ?? [];
          const groupesEquipe = prefill.groupes ?? [];
          const noms = prefill.joueurs;
          if (groupesEquipe.length > 0) {
            // Lot peaufinage C : les groupes nommés de la page « club » sont
            // mappés POSITIONNELLEMENT sur la trame — le groupe i de
            // l'équipe occupe le groupe i de la trame (nom, joueurs, compte)
            // ; les groupes de trame en reste vides. Les groupes enregistrés
            // au-delà de la trame (U8 = 2) sont ajoutés comme dans addGroup :
            // nouvel id + un slot dans chaque rotation d'ateliers (station
            // unique, atelier prérempli — `null` tolérée).
            const ex = firstUsableExercise();
            const groupesFinaux = groupes.map((g, i) => {
              const ge = groupesEquipe[i];
              if (!ge) return { ...g, players: 0, joueurs: undefined };
              const copie = {
                ...g,
                name: ge.nom,
                players: ge.joueurs.length,
              };
              copie.joueurs = ge.joueurs.length > 0 ? ge.joueurs : undefined;
              return copie;
            });
            groupesEquipe.forEach((ge, i) => {
              if (i < groupes.length) return;
              const gid = nextGroupId(groupesFinaux);
              groupesFinaux.push({
                id: gid,
                name: ge.nom,
                players: ge.joueurs.length,
                joueurs: ge.joueurs.length > 0 ? ge.joueurs : undefined,
              });
              for (const b of base.blocks ?? []) {
                if (b.kind !== "WORKSHOPS") continue;
                for (const r of b.rounds ?? []) {
                  const used = new Set(r.assignments.map((s) => s.station_id));
                  let k = r.assignments.length + 1;
                  let station = `station-${k}`;
                  while (used.has(station)) {
                    k += 1;
                    station = `station-${k}`;
                  }
                  r.assignments.push({
                    group_id: gid,
                    station_id: station,
                    variant_id: ex,
                  });
                }
              }
            });
            base.groups = groupesFinaux;
          } else if (noms.length > 0) {
            const parGroupe = roundRobinJoueurs(noms, groupes.map((g) => g.id));
            base.groups = groupes.map((g) => {
              const r = parGroupe[g.id] ?? [];
              const copie = { ...g, players: r.length };
              if (r.length > 0) copie.joueurs = r;
              else copie.joueurs = undefined;
              return copie;
            });
          } else if (prefill.team.effectif !== null) {
            const parts = repartirEffectif(prefill.team.effectif, groupes.length);
            base.groups = groupes.map((g, i) => ({
              ...g,
              players: parts[i] ?? 0,
              joueurs: undefined,
            }));
          }
          // P5 — les cases de présence suivent la même liste de joueurs
          // qu’au préremplissage ; aucune absence par défaut.
          if (groupesEquipe.length > 0) {
            // Mode nommé : l’union ordonnée des joueurs des groupes — la
            // règle serveur (un joueur au plus dans un groupe) garantit
            // qu’il n’y a pas de doublons.
            setJoueursEquipe(groupesEquipe.flatMap((ge) => ge.joueurs));
            setGroupesSource(groupesEquipe);
          } else if (noms.length > 0) {
            setJoueursEquipe(noms);
            setGroupesSource(null);
          } else {
            setJoueursEquipe(null);
            setGroupesSource(null);
          }
          setPresences({});
          base.players = (base.groups ?? []).reduce((a, x) => a + x.players, 0);
          if (prefill.coach_par_defaut) {
            base.coach_logins = [prefill.coach_par_defaut];
            base.coaches = 1;
            base.coach_principal = prefill.coach_par_defaut;
          }
          setPlan(base);
        } else {
          setPlan(p);
        }
        const d = loadDraft();
        if (d) setPendingDraft(d);
      })
      .catch((e: Error) => live && setLoadError(e.message));
    return () => {
      live = false;
    };
    // `prefill` est stable : posé par la page « club » avant l'ouverture
    // (consommation unique) — l'effet ne doit se jouer qu'à la première
    // ouverture du constructeur.
  }, []);

  // Lot 5 : listes du compte au montage (référencées par l'identité « moi »,
  // jamais d'appel sans session). L'échec se signale dans la section, jamais
  // de silence.
  useEffect(() => {
    let live = true;
    if (!moi) return;
    listerBrouillons()
      .then((l) => live && setBrouillons(l))
      .catch((e: Error) => live && setCompteMsg(e.message));
    listerPropositions()
      .then((l) => live && setPropositions(l))
      .catch((e: Error) => live && setCompteMsg(e.message));
    return () => {
      live = false;
    };
  }, [moi]);

  // Équipes du compte + liste « coachs disponibles » (tous les comptes
  // enregistrés) au montage, si connecté. L'échec se signale dans la
  // section — jamais de silence.
  useEffect(() => {
    let live = true;
    if (!moi) return;
    listerEquipes()
      .then((l) => live && setEquipes(l))
      .catch((e: Error) => live && setEquipesMsg(e.message));
    listerCoachs()
      .then((l) => live && setCoachRefs(l))
      .catch((e: Error) => live && setEquipesMsg(e.message));
    return () => {
      live = false;
    };
  }, [moi]);

  const cards: Card[] = view?.cards ?? [];
  const etatParId = useMemo(() => etatParIdDe(cards), [cards]);
  const cardById = useMemo(() => {
    const m: Record<string, Card> = {};
    for (const c of cards) m[c.id] = c;
    return m;
  }, [cards]);

  // Miroir local, recalculé à chaque changement de plan (même ordre de
  // messages que le serveur) — c'est le feedback immédiat de l'édition.
  const localCheck = useMemo(
    () => (plan ? validerLocale(plan, etatParId) : null),
    [plan, etatParId]
  );

  const min = useMemo(() => (plan ? localCheck!.minutage : null), [plan, localCheck]);

  // Mutation du plan : copie profonde, application, resynchronisation de la
  // durée totale (somme des blocs) pour rester cohérent avec le validateur.
  // Le brouillon est sauvegardé à chaud (localStorage) après chaque mutation.
  const updatePlan = (fn: (draft: SessionPlan) => void) => {
    if (!plan) return;
    const draft = clonePlan(plan);
    fn(draft);
    draft.duration_min = (draft.blocks ?? []).reduce<number>(
      (acc, b) => (typeof b.duration_min === "number" ? acc + b.duration_min : acc),
      0
    );
    setPlan(draft);
    const t = saveDraft(draft);
    if (t) setSavedAt(t);
    setServerCheck(null);
    setServerTime(null);
  };

  const firstUsableExercise = (): string | null => {
    const c = cards.find((x) => x.state !== "INCOMPLETE");
    return c ? c.id : null;
  };

  const addBlock = (kind: SessionPlan["blocks"][number]["kind"]) => {
    updatePlan((draft) => {
      const block: SessionBlock = {
        kind,
        label: KIND_LABELS[kind] ?? kind,
        duration_min: 10,
        variant_ids: [],
      };
      if (kind === "WORKSHOPS") {
        const ex = firstUsableExercise();
        block.rounds = [
          {
            work_min: 10,
            transition_min: 0,
            assignments: (draft.groups ?? []).map((g, i) => ({
              group_id: g.id,
              station_id: `station-${i + 1}`,
              variant_id: ex,
            })),
          },
        ];
      }
      draft.blocks.push(block);
    });
  };

  const removeBlock = (bi: number) =>
    updatePlan((draft) => {
      draft.blocks.splice(bi, 1);
    });

  const addRound = (bi: number) =>
    updatePlan((draft) => {
      const b = draft.blocks[bi];
      const rounds = b.rounds ?? [];
      if (rounds.length === 0) return;
      const last = rounds[rounds.length - 1];
      b.rounds = [...rounds, structuredClone(last)];
      b.duration_min = b.rounds.reduce(
        (a, r) => a + r.work_min + r.transition_min,
        0
      );
    });

  const removeRound = (bi: number, ri: number) =>
    updatePlan((draft) => {
      const b = draft.blocks[bi];
      const rounds = b.rounds;
      if (!rounds || rounds.length <= 1) return;
      rounds.splice(ri, 1);
      b.duration_min = rounds.reduce((a, r) => a + r.work_min + r.transition_min, 0);
    });

  // Groupes dynamiques : ajout/suppression de groupes ; l'effectif total est
  // la somme des groupes (recalculée à chaque mutation, jamais stockée à
  // part) et chaque rotation d'atelier reste cohérente (un slot par groupe,
  // des stations uniques dans la rotation). Toujours au moins un groupe.
  const nextGroupId = (groups: { id: string }[]): string => {
    for (const letter of "ABCDEFGHIJKLMNOPQR") {
      if (!groups.some((g) => g.id === letter)) return letter;
    }
    let n = 27;
    while (groups.some((g) => g.id === "G" + n)) n += 1;
    return "G" + n;
  };

  const addGroup = () =>
    updatePlan((draft) => {
      const gid = nextGroupId(draft.groups ?? []);
      draft.groups = [...(draft.groups ?? []), { id: gid, players: 0 }];
      draft.players = draft.groups.reduce((a, x) => a + x.players, 0);
      // Le nouveau groupe rejoint chaque rotation d'atelier avec un atelier
      // prérempli (jamais de variant_id null → pas d'« Exercice inconnu :
      // None »), la station étant unique dans la rotation.
      const ex = firstUsableExercise();
      for (const b of draft.blocks ?? []) {
        if (b.kind !== "WORKSHOPS") continue;
        for (const r of b.rounds ?? []) {
          const used = new Set(r.assignments.map((s) => s.station_id));
          let k = r.assignments.length + 1;
          let station = `station-${k}`;
          while (used.has(station)) {
            k += 1;
            station = `station-${k}`;
          }
          r.assignments.push({ group_id: gid, station_id: station, variant_id: ex });
        }
      }
    });

  const removeGroup = (gid: string) =>
    updatePlan((draft) => {
      if ((draft.groups ?? []).length <= 1) return;
      draft.groups = draft.groups.filter((g) => g.id !== gid);
      draft.players = draft.groups.reduce((a, x) => a + x.players, 0);
      for (const b of draft.blocks ?? []) {
        if (b.kind !== "WORKSHOPS") continue;
        for (const r of b.rounds ?? []) {
          r.assignments = r.assignments.filter((s) => s.group_id !== gid);
        }
        // Une rotation sans affectation n'a plus de sens : on la retire.
        const rounds = (b.rounds ?? []).filter((r) => r.assignments.length > 0);
        b.rounds = rounds.length > 0 ? rounds : (b.rounds ?? []);
        if (rounds.length > 0) {
          b.duration_min = rounds.reduce(
            (a, r) => a + r.work_min + r.transition_min,
            0
          );
        }
      }
    });

  // Équipe d'effectif : attachée à la séance comme snapshot (D1) — la séance
  // conserve son instantané ; les éditions ultérieures de l'équipe ne la
  // modifient pas.
  // Lot L3 (v1.1) : l'attachement COPIE le snapshot de l'équipe dans les
  // groupes EXISTANTS — le nombre de groupes ne change jamais (chaque
  // rotation a un slot par groupe). Joueurs nommés → répartition
  // round-robin, un nom par case ; sinon l'effectif déclaré est réparti
  // numériquement ; équipe sans effectif → groupes inchangés.
  // Lot P5 (workflows 2026-11-26) : les joueurs nommés alimentent en plus
  // la liste des cases de présence — par défaut tous cochés (aucune
  // absence) ; le mode de répartition reste plat (round-robin), le mode
  // nommé étant réservé au préremplissage « groupes ».
  const attachEquipe = (id: string) => {
    // Les cases suivent l’équipe choisie : liste complète des joueurs
    // nommés (ou null), aucune absence, mode plat.
    const eq = equipes.find((x) => x.id === id);
    const nomsEquipe = eq ? eq.joueurs ?? [] : [];
    setJoueursEquipe(nomsEquipe.length > 0 ? nomsEquipe : null);
    setGroupesSource(null);
    setPresences({});
    updatePlan((d) => {
      if (!id) {
        d.team = null;
        return;
      }
      if (!eq) return;
      d.team = {
        id: eq.id,
        nom: eq.nom,
        club: eq.club,
        categorie: eq.categorie,
        effectif: eq.effectif,
      };
      const groups = d.groups ?? [];
      const noms = eq.joueurs ?? [];
      if (noms.length > 0) {
        const parGroupe = roundRobinJoueurs(noms, groups.map((g) => g.id));
        d.groups = groups.map((g) => {
          const r = parGroupe[g.id] ?? [];
          const copie = { ...g, players: r.length };
          if (r.length > 0) copie.joueurs = r;
          else copie.joueurs = undefined;
          return copie;
        });
      } else if (eq.effectif !== null) {
        const parts = repartirEffectif(eq.effectif, groups.length);
        d.groups = groups.map((g, i) => ({
          ...g,
          players: parts[i] ?? 0,
          joueurs: undefined,
        }));
      }
      d.players = (d.groups ?? []).reduce((a, x) => a + x.players, 0);
    });
  };

  // P5 — bascule d’une case de présence : la répartition est recalculée
  // depuis la source — un joueur décoché n’est dans AUCUN groupe, un
  // joueur récoché revient dans le sien (son groupe nommé ou son slot
  // round-robin). L’effectif validé suit le compte des groupes.
  const basculerPresence = (nom: string) => {
    const suivant = basculerPresences(presences, nom);
    setPresences(suivant);
    updatePlan((d) => {
      if (!joueursEquipe) return;
      d.groups = redistribuerPresences(
        d.groups ?? [],
        joueursEquipe,
        suivant,
        groupesSource,
      );
      d.players = (d.groups ?? []).reduce((a, x) => a + x.players, 0);
    });
  };

  // Retirer un joueur nommé d'un groupe : le total du groupe suit les noms
  // (l'effectif est dérivé, jamais stocké à part). Le joueur n'est PAS
  // renvoyé dans l'équipe — la séance est une copie ; ré-attacher
  // rétablit la répartition.
  const retirerJoueur = (gid: string, nom: string) =>
    updatePlan((d) => {
      const grp = (d.groups ?? []).find((x) => x.id === gid);
      if (!grp) return;
      const rest = (grp.joueurs ?? []).filter((n) => n !== nom);
      if (rest.length === 0) {
        grp.players = 0;
        grp.joueurs = undefined;
      } else {
        grp.joueurs = rest;
        grp.players = rest.length;
      }
      d.players = (d.groups ?? []).reduce((a, x) => a + x.players, 0);
    });

  // « Utiliser les M déclarés » (bannière de divergence) : effacer les
  // noms et répartir numériquement l'effectif déclaré sur les groupes.
  const appliquerEffectifDeclare = () =>
    updatePlan((d) => {
      const m = d.team?.effectif;
      if (m === null || m === undefined) return;
      const groups = d.groups ?? [];
      const parts = repartirEffectif(m, groups.length);
      d.groups = groups.map((g, i) => ({
        ...g,
        players: parts[i] ?? 0,
        joueurs: undefined,
      }));
      d.players = (d.groups ?? []).reduce((a, x) => a + x.players, 0);
    });

  // « Coachs disponibles » : le compte d'« Éducateurs » est dérivé des
  // identifiants cochés — la consigne de validation compte les coachs, la
  // trace conserve les identifiants (login ou nom libre, v1.1).
  const toggleCoach = (identifiant: string) =>
    updatePlan((d) => {
      const cur = new Set(d.coach_logins ?? []);
      if (cur.has(identifiant)) cur.delete(identifiant);
      else cur.add(identifiant);
      d.coach_logins = [...cur];
      d.coaches = d.coach_logins.length;
    });

  const refreshCoachs = () =>
    listerCoachs().then(setCoachRefs).catch((e: Error) => setCoachMsg(e.message));

  // Ajout d'un coach sans compte par nom (v1.1, 2026-11-24).
  const addCoachParNom = async () => {
    const nom = coachNom.trim();
    if (nom.length < 2) return;
    setCoachBusy(true);
    setCoachMsg(null);
    try {
      await ajouterCoach(nom, coachClub.trim() || null);
      setCoachNom("");
      setCoachClub("");
      await refreshCoachs();
    } catch (e) {
      setCoachMsg((e as Error).message);
    } finally {
      setCoachBusy(false);
    }
  };

  // Création d'une équipe d'effectif : seule le nom est requis (modèle
  // flexible, effectifs variables selon les clubs) ; la séance est
  // automatiquement reliée à la nouvelle équipe.
  const createEquipe = async () => {
    setFormBusy(true);
    setEquipesMsg(null);
    try {
      const corps: CorpsEquipe = { nom: formNom };
      if (formClub.trim()) corps.club = formClub.trim();
      if (formCat) corps.categorie = formCat;
      if (formEffectif.trim() !== "") {
        const n = Number(formEffectif);
        if (Number.isInteger(n) && n >= 0) corps.effectif = n;
      }
      if (formCoachs.length) corps.coachs = formCoachs;
      // Joueurs (lot L3, v1.1) : lignes non vides du champ « Joueurs » —
      // le serveur dédoublonne aussi (même règle qu'ici).
      if (formJoueurs.trim() !== "") {
        const noms = parserJoueurs(formJoueurs);
        if (noms.length > 0) corps.joueurs = noms;
      }
      const eq = await creerEquipe(corps);
      setEquipes(await listerEquipes());
      setFormNom("");
      setFormClub("");
      setFormCat("");
      setFormEffectif("");
      setFormCoachs([]);
      setFormJoueurs("");
      setShowNewEquipe(false);
      attachEquipe(eq.id);
    } catch (e) {
      setEquipesMsg(e instanceof Error ? e.message : "Création de l'équipe impossible");
    } finally {
      setFormBusy(false);
    }
  };

  const groupLabel = (gid: string) => {
    const g = (plan?.groups ?? []).find((x) => x.id === gid);
    // Nom libre (lot « peaufinage ») : le label affiché est `name` s'il y en
    // a un, sinon la lettre interne — l'`id` reste la clé, jamais l'affichage.
    return g ? `Groupe ${g.name ?? g.id}` : gid;
  };

  const runServerCheck = async () => {
    if (!plan || checking) return;
    setChecking(true);
    setServerError(null);
    try {
      const res = await validerSeance(plan);
      setServerCheck(res);
      setServerTime(new Date().toLocaleTimeString("fr-FR", { hour12: false }));
    } catch (e) {
      setServerError((e as Error).message);
      setServerCheck(null);
    } finally {
      setChecking(false);
    }
  };

  // Le résultat serveur est la référence : on signale tout écart avec le
  // miroir local (normalement nul — les deux sont le même contrat).
  const serverDiverges =
    serverCheck !== null &&
    localCheck !== null &&
    JSON.stringify({
      valide: serverCheck.valide,
      erreurs: serverCheck.erreurs,
      avertissements: serverCheck.avertissements,
    }) !==
      JSON.stringify({
        valide: localCheck.valide,
        erreurs: localCheck.erreurs,
        avertissements: localCheck.avertissements,
      });

  const pickExercise = (id: string) => {
    if (!picker) return;
    updatePlan((draft) => {
      const b = draft.blocks[picker.blockIndex];
      if (picker.kind === "slot") {
        b.rounds![picker.roundIndex].assignments[picker.slotIndex].variant_id = id;
      } else if (!b.variant_ids.includes(id)) {
        b.variant_ids.push(id);
      }
    });
    setPicker(null);
    setPickerQuery("");
  };

  const pickerResults = picker
    ? selectCards(cards, { query: pickerQuery, includeIncomplete: true })
    : [];

  // --- Lot 4 : reprise / export / import / effacement du brouillon. ---

  // Applique un plan (reprise, import, trame) et remet à zéro les états
  // dépendants : résultat serveur, picker, erreur d'import.
  const applyPlan = (p: SessionPlan) => {
    setPlan(clonePlan(p));
    setServerCheck(null);
    setServerTime(null);
    setServerError(null);
    setPicker(null);
    setPickerQuery("");
  };

  const resumeDraft = () => {
    if (!pendingDraft) return;
    applyPlan(pendingDraft.plan);
    setSavedAt(pendingDraft.saved_at || null);
    setPendingDraft(null);
    setImportError(null);
  };

  // Repartir de la trame U8 : le brouillon est effacé (action explicite,
  // jamais silencieuse) et la trame de départ est réappliquée.
  const restartFromTrame = () => {
    if (!initialDraft) return;
    clearDraft();
    applyPlan(initialDraft);
    setSavedAt(null);
    setPendingDraft(null);
    setImportError(null);
  };

  // Export : le plan brut (même contrat que le validateur) en fichier JSON.
  const exportDraft = () => {
    if (!plan) return;
    const blob = new Blob([JSON.stringify(plan, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const d = new Date();
    const pad = (n: number) => String(n).padStart(2, "0");
    a.href = url;
    a.download = `seance-${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const onImportFile = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ""; // permet de ré-importer le même fichier
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const p = parseImport(String(reader.result ?? ""));
      if (!p) {
        setImportError(
          "Fichier invalide : attendu un plan de séance JSON (export de cette application)."
        );
        return;
      }
      applyPlan(p);
      const t = saveDraft(p);
      if (t) setSavedAt(t);
      setPendingDraft(null);
      setImportError(null);
    };
    reader.onerror = () => setImportError("Lecture du fichier impossible.");
    reader.readAsText(file);
  };

  // --- Lot 5 : enregistrements sur le compte (si connecté). ---

  // Upsert par identifiant de séance : le même plan remplace son brouillon,
  // sans doublon dans la liste (le serveur est la référence).
  const saveToAccount = async () => {
    if (!plan || !moi || compteBusy) return;
    setCompteBusy(true);
    setCompteMsg(null);
    setPropResult(null);
    try {
      const ref = await sauvegarderBrouillon(plan.id, plan.title, plan);
      setBrouillons((prev) =>
        [...prev.filter((b) => b.id !== ref.id), ref].sort((a, b) =>
          b.saved_at.localeCompare(a.saved_at)
        )
      );
      setCompteMsg(
        `Séance « ${plan.title} » sauvegardée sur votre compte le ${savedLabel(ref.saved_at)}.`
      );
    } catch (e) {
      setCompteMsg(
        e instanceof Error ? e.message : "Sauvegarde sur le compte impossible."
      );
    } finally {
      setCompteBusy(false);
    }
  };

  // Reprise : le plan complet du brouillon est réappliqué dans le
  // constructeur (mêmes états remis à zéro que tout autre applyPlan).
  const reprendreBrouillon = async (id: string) => {
    if (!moi || compteBusy) return;
    setCompteBusy(true);
    setCompteMsg(null);
    setPropResult(null);
    try {
      const b = await chargerBrouillon(id);
      applyPlan(b.plan);
      setSavedAt(b.saved_at);
      setCompteMsg(`Brouillon « ${b.titre} » repris dans le constructeur.`);
    } catch (e) {
      setCompteMsg(
        e instanceof Error ? e.message : "Reprise du brouillon impossible."
      );
    } finally {
      setCompteBusy(false);
    }
  };

  const supprimerDuCompte = async (id: string) => {
    if (!moi || compteBusy) return;
    setCompteBusy(true);
    setCompteMsg(null);
    try {
      await supprimerBrouillon(id);
      setBrouillons((prev) => prev.filter((b) => b.id !== id));
      setCompteMsg("Brouillon supprimé du compte.");
    } catch (e) {
      setCompteMsg(e instanceof Error ? e.message : "Suppression impossible.");
    } finally {
      setCompteBusy(false);
    }
  };

  // D1 : la proposition est un snapshot immuable — la validité, les erreurs
  // et la minutage sont figés au moment de l'enregistrement serveur.
  const enregistrerProposition = async () => {
    if (!plan || !moi || compteBusy) return;
    setCompteBusy(true);
    setCompteMsg(null);
    try {
      const p = await creerProposition(plan.title, plan);
      setPropResult(p);
      setPropositions((prev) =>
        [...prev.filter((x) => x.id !== p.id), p].sort((a, b) => b.id - a.id)
      );
    } catch (e) {
      setCompteMsg(
        e instanceof Error
          ? e.message
          : "Enregistrement de la proposition impossible."
      );
    } finally {
      setCompteBusy(false);
    }
  };

  // Lot 7 — génération + partage PDF d'une proposition validée (vue du
  // snapshot immuable, D1 lot 5). On charge la proposition complète, on
  // charge chaque fiche d'atelier référencée (via l'API existante), on
  // génère le PDF côté client (html2canvas + jsPDF), puis on ouvre la feuille
  // de partage native. Un fichier absent (supprimé du catalogue) n'empêche
  // pas la génération : il est signalé dans le PDF (« Fiche non trouvée »).
  // v1.1 L1 — l'aperçu et le partage partagent ce chargement : la matière
  // (proposition + fiches + conseils) est chargée une seule fois.
  const chargerMatiere = (id: number) =>
    chargerProposition(id).then(async (prop) => {
      const ids = atelierIdsDuPlan(prop.plan);
      const fiches: Record<string, Fiche> = {};
      // Conseils coach (data/coach-cues.json via /api/conseils) : si
      // l'endpoint est indisponible, le PDF part sans conseils — le partage
      // reste possible.
      let conseils: ConseilCoach[] = [];
      try {
        conseils = (await fetchConseils()).records;
      } catch {
        conseils = [];
      }
      await Promise.all(
        ids.map(async (idFiche) => {
          try {
            fiches[idFiche] = await fetchFiche(idFiche);
          } catch {
            // fiche manquante → le PDF l'indique, on continue.
          }
        })
      );
      return { prop, fiches, conseils };
    });

  type MatierePdf = {
    prop: Proposition;
    fiches: Record<string, Fiche>;
    conseils: ConseilCoach[];
  };

  const partagerEnPdf = async (p: PropositionRef, matiere?: MatierePdf) => {
    if (!moi || pdfBusy !== null) return;
    setPdfBusy(p.id);
    setPdfMsg(null);
    setWaHref(null);
    try {
      const m = matiere ?? (await chargerMatiere(p.id));
      const file = await generateSessionPdf(m.prop, moi, m.fiches, m.conseils);
      const recap = recapTextePlan(m.prop, m.fiches);
      const mode = await partagerPieceJointe(file, recap);
      if (mode === "shared") {
        setPdfMsg("PDF envoyé via la feuille de partage (récap joint).");
        setWaHref(null);
      } else if (mode === "text-shared") {
        setPdfMsg(
          "Récapitulatif envoyé via la feuille de partage. PDF téléchargé sur votre appareil — à joindre à votre groupe si besoin."
        );
        setWaHref(lienWhatsApp(recap));
      } else if (mode === "downloaded") {
        setPdfMsg(
          "Partage non pris en charge ici : PDF téléchargé — à joindre à votre groupe."
        );
        setWaHref(lienWhatsApp(recap));
      }
      // mode === "cancelled" : l'utilisateur a refermé la feuille, rien à dire.
    } catch (e) {
      setPdfMsg(
        "Échec de la génération du PDF : " +
          (e instanceof Error ? e.message : "erreur inconnue.")
      );
    } finally {
      setPdfBusy(null);
    }
  };

  // v1.1 L1 — aperçu WYSIWYG : on affiche les pages réelles de la pièce qui
  // sera partagée (renderSheetPages = la voie de rasterisation unique du
  // PDF). L'aperçu ne contient ni plus, ni moins, que le PDF.
  const previsualiserPdf = async (p: PropositionRef) => {
    if (!moi || pdfBusy !== null) return;
    setPdfBusy(p.id);
    try {
      const m = await chargerMatiere(p.id);
      const { pages } = await renderSheetPages(m.prop, moi, m.fiches, m.conseils);
      setPdfPreview({ p, ...m, pages });
    } catch (e) {
      setPdfMsg(
        "Échec de l'aperçu du PDF : " +
          (e instanceof Error ? e.message : "erreur inconnue.")
      );
    } finally {
      setPdfBusy(null);
    }
  };

  if (loadError) {
    return (
      <div className="empty">
        <h2>Trame de référence indisponible</h2>
        <p>{loadError}</p>
      </div>
    );
  }
  if (!plan || !localCheck || !min) {
    return (
      <>
        <div className="skeleton skeleton-line" style={{ width: "50%" }} />
        <div className="skeleton skeleton-card" />
        <div className="skeleton skeleton-card" />
      </>
    );
  }

  return (
    <div className="seance">
      {pendingDraft && (
        <div className="draft-banner" role="alert">
          <p>
            Brouillon sauvegardé
            {pendingDraft.saved_at ? ` le ${savedLabel(pendingDraft.saved_at)}` : ""} —
            le reprendre, ou repartir de la trame U8 ?
          </p>
          <div className="draft-banner-actions">
            <button className="apply-btn" onClick={resumeDraft}>
              Reprendre le brouillon
            </button>
            <button className="reset-btn" onClick={restartFromTrame}>
              Repartir de la trame U8
            </button>
          </div>
        </div>
      )}
      <section className="seance-head">
        <label className="field">
          <span className="field-label">Titre de la séance</span>
          <input
            className="text-input"
            type="text"
            value={plan.title}
            onChange={(e) => updatePlan((d) => void (d.title = e.target.value))}
          />
        </label>
        <div className="field-row">
          <label className="field">
            <span className="field-label">Créneau (min)</span>
            <input
              className="num-input"
              type="number"
              inputMode="numeric"
              min={0}
              step={5}
              value={plan.creneau_min}
              onChange={(e) =>
                updatePlan((d) => {
                  d.creneau_min = Number.isInteger(+e.target.value) ? +e.target.value : 0;
                })
              }
            />
          </label>
          {moi ? (
            <div className="field">
              <span className="field-label">Coachs disponibles</span>
              {coachRefs.length > 0 && (
                <div className="coach-list">
                  {coachRefs.map((c) => (
                    <label className="coach-row" key={(c.login ? "c:" : "n:") + c.nom}>
                      <input
                        type="checkbox"
                        aria-label={`Coach ${c.nom}`}
                        checked={(plan.coach_logins ?? []).includes(c.nom)}
                        onChange={() => toggleCoach(c.nom)}
                      />
                      <span className="coach-name">{c.nom}</span>
                      {c.club ? <span className="coach-club">{c.club}</span> : null}
                    </label>
                  ))}
                </div>
              )}
              {/* Ajout d'un coach sans compte par nom (v1.1, 2026-11-24). */}
              <div className="coach-add-row">
                <input
                  type="text"
                  aria-label="Nom du coach à ajouter"
                  placeholder="Nom du coach (ex. Marie Dupont)"
                  value={coachNom}
                  onChange={(e) => setCoachNom(e.target.value)}
                />
                <input
                  type="text"
                  aria-label="Club du coach (facultatif)"
                  placeholder="Club (facultatif)"
                  value={coachClub}
                  onChange={(e) => setCoachClub(e.target.value)}
                />
                <button
                  type="button"
                  className="apply-btn"
                  disabled={coachBusy || coachNom.trim().length < 2}
                  onClick={() => void addCoachParNom()}
                >
                  {coachBusy ? "Ajout…" : "Ajouter"}
                </button>
              </div>
              {coachMsg ? <p className="form-error">{coachMsg}</p> : null}
              <label className="field" style={{ marginTop: 8 }}>
                <span className="field-label">Coach principal de la séance</span>
                <select
                  className="select-input"
                  aria-label="Coach principal de la séance"
                  value={plan.coach_principal ?? ""}
                  onChange={(e) =>
                    updatePlan((d) => {
                      d.coach_principal = e.target.value || null;
                    })
                  }
                >
                  <option value="">— non défini —</option>
                  {coachRefs.map((c) => (
                    <option key={(c.login ? "c:" : "n:") + c.nom} value={c.nom}>
                      {c.nom}
                      {c.club ? ` (${c.club})` : ""}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          ) : (
            <label className="field">
              <span className="field-label">Éducateurs</span>
              <input
                className="num-input"
                type="number"
                inputMode="numeric"
                min={0}
                step={1}
                value={plan.coaches ?? 0}
                onChange={(e) =>
                  updatePlan((d) => {
                    d.coaches = Number.isInteger(+e.target.value) ? +e.target.value : 0;
                  })
                }
              />
            </label>
          )}
        </div>
        <div className="field-row groups-row" role="group" aria-label="Effectifs par groupe">
          {(plan.groups ?? []).map((g) => (
            <div className="field group-cell" key={g.id}>
              <span className="field-label">Groupe {g.name ?? g.id} (joueurs)</span>
              {/* Nom libre (lot « peaufinage ») : défaut = la lettre interne ;
                  un nom vidé retourne à la lettre (champ supprimé du plan). */}
              <input
                className="group-name-input"
                type="text"
                placeholder={`Groupe ${g.id}`}
                aria-label={`Nom libre du groupe (défaut : ${g.id})`}
                value={g.name ?? ""}
                maxLength={30}
                onChange={(e) =>
                  updatePlan((d) => {
                    const grp = d.groups.find((x) => x.id === g.id);
                    if (!grp) return;
                    const v = e.target.value.trim();
                    if (v) grp.name = v;
                    else delete grp.name;
                  })
                }
              />
              <div className="group-cell-row">
                <input
                  className="num-input"
                  type="number"
                  inputMode="numeric"
                  min={0}
                  step={1}
                  aria-label={`Effectif du groupe ${g.name ?? g.id}`}
                  value={g.players}
                  disabled={(g.joueurs?.length ?? 0) > 0}
                  title={
                    (g.joueurs?.length ?? 0) > 0
                      ? "Effectif dérivé des joueurs nommés (lot L3)"
                      : undefined
                  }
                  onChange={(e) =>
                    updatePlan((d) => {
                      const grp = d.groups.find((x) => x.id === g.id);
                      if (!grp) return;
                      grp.players = Number.isInteger(+e.target.value) ? +e.target.value : 0;
                      d.players = d.groups.reduce((a, x) => a + x.players, 0);
                    })
                  }
                />
                {plan.groups.length > 1 && (
                  <button
                    className="group-delete"
                    aria-label={`Supprimer le groupe ${g.name ?? g.id}`}
                    onClick={() => removeGroup(g.id)}
                  >
                    ×
                  </button>
                )}
              </div>
              {(g.joueurs?.length ?? 0) > 0 && (
                <div className="group-joueurs">
                  {(g.joueurs ?? []).map((nom) => (
                    <span className="assigned-chip" key={nom}>
                      {nom}
                      <button
                        className="chip-x"
                        aria-label={`Retirer ${nom} du groupe ${g.name ?? g.id}`}
                        onClick={() => retirerJoueur(g.id, nom)}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
          <label className="field">
            <span className="field-label">Total</span>
            <span className="total-players" aria-live="polite">{plan.players}</span>
          </label>
        </div>
        <button className="add-round-btn groups-add" onClick={() => addGroup()}>
          + Groupe
        </button>
        {moi && (
          <div className="team-block">
            <span className="field-label">Équipe (effectif enregistré)</span>
            <div className="team-row">
              <select
                className="select-input"
                aria-label="Équipe d'effectif"
                value={plan.team?.id ?? ""}
                onChange={(e) => attachEquipe(e.target.value)}
              >
                <option value="">— Aucune équipe —</option>
                {equipes.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.nom}
                    {e.categorie ? ` (${e.categorie})` : ""}
                  </option>
                ))}
              </select>
              <button
                className="link-btn"
                onClick={() => setShowNewEquipe((v) => !v)}
              >
                {showNewEquipe ? "Fermer" : "+ Nouvelle équipe"}
              </button>
            </div>
            {equipesMsg && <p className="form-error">{equipesMsg}</p>}
            {plan.team && (
              <p className="team-snapshot">
                {plan.team.nom}
                {plan.team.club ? ` — ${plan.team.club}` : ""}
                {plan.team.categorie ? ` — ${plan.team.categorie}` : ""}
                {plan.team.effectif !== null ? ` — ${plan.team.effectif} joueurs` : ""}
              </p>
            )}
            {(() => {
              // P5 — présence à l’attachement : une case par joueur de
              // l’équipe (cochée par défaut) ; seuls les joueurs cochés
              // sont répartis dans les groupes.
              if (!joueursEquipe || joueursEquipe.length === 0) return null;
              const presents = joueursCoches(joueursEquipe, presences);
              return (
                <div className="presence-block">
                  <span className="field-label" aria-live="polite">
                    Présences — {presents.length}/{joueursEquipe.length} présents
                  </span>
                  <div className="presence-list">
                    {joueursEquipe.map((nom) => (
                      <label className="presence-item" key={nom}>
                        <input
                          type="checkbox"
                          aria-label={`Présence de ${nom}`}
                          checked={presences[nom] !== false}
                          onChange={() => basculerPresence(nom)}
                        />
                        {nom}
                      </label>
                    ))}
                  </div>
                </div>
              );
            })()}
            {(() => {
              // Divergence lot L3 : joueurs nommés ≠ effectif déclaré.
              // L'effectif validé reste le compte des groupes (plan.players) ;
              // la bannière signale l'écart et propose le ramener à l'effectif.
              const m = plan.team?.effectif ?? null;
              const n = (plan.groups ?? []).reduce(
                (a, g) => a + (g.joueurs?.length ?? 0),
                0
              );
              if (m === null || n === 0 || n === m) return null;
              return (
                <div className="divergence-banner" role="status">
                  <span>
                    {n} joueurs nommés pour {m} joueurs déclarés —
                    l'effectif validé compte {plan.players}.
                  </span>
                  <button
                    className="link-btn"
                    onClick={appliquerEffectifDeclare}
                  >
                    Utiliser les {m} déclarés
                  </button>
                </div>
              );
            })()}
            {showNewEquipe && (
              <div className="team-form">
                <label className="field">
                  <span className="field-label">Nom (requis)</span>
                  <input
                    className="text-input"
                    type="text"
                    value={formNom}
                    onChange={(e) => setFormNom(e.target.value)}
                  />
                </label>
                <div className="field-row">
                  <label className="field">
                    <span className="field-label">Club</span>
                    <input
                      className="text-input"
                      type="text"
                      value={formClub}
                      onChange={(e) => setFormClub(e.target.value)}
                    />
                  </label>
                  <label className="field">
                    <span className="field-label">Catégorie</span>
                    <select
                      className="select-input"
                      value={formCat}
                      onChange={(e) => setFormCat(e.target.value)}
                    >
                      <option value="">—</option>
                      {CATEGORIES_UI.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span className="field-label">Effectif</span>
                    <input
                      className="num-input"
                      type="number"
                      inputMode="numeric"
                      min={0}
                      step={1}
                      value={formEffectif}
                      onChange={(e) => setFormEffectif(e.target.value)}
                    />
                  </label>
                </div>
                <label className="field">
                  <span className="field-label">
                    Joueurs (prénom + nom, un par ligne)
                  </span>
                  <textarea
                    className="text-input players-textarea"
                    rows={4}
                    value={formJoueurs}
                    placeholder={"Léa Martin\nNoah Dupont"}
                    onChange={(e) => setFormJoueurs(e.target.value)}
                  />
                </label>
                {coachRefs.length > 0 && (
                  <div className="field">
                    <span className="field-label">Coachs rattachés</span>
                    <div className="coach-list">
                      {coachRefs.map((c) => (
                        <label className="coach-row" key={(c.login ? "c:" : "n:") + c.nom}>
                          <input
                            type="checkbox"
                            aria-label={`Rattacher ${c.nom}`}
                            checked={formCoachs.includes(c.nom)}
                            onChange={() =>
                              setFormCoachs((l) =>
                                l.includes(c.nom)
                                  ? l.filter((x) => x !== c.nom)
                                  : [...l, c.nom]
                              )
                            }
                          />
                          <span className="coach-name">{c.nom}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}
                <button
                  className="apply-btn"
                  disabled={formBusy || formNom.trim().length === 0}
                  onClick={() => void createEquipe()}
                >
                  {formBusy ? "Création…" : "Créer l'équipe"}
                </button>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Minutage dérivée — jamais stockée, recalculée à chaque frappe. */}
      <div className="seance-stats" aria-live="polite">
        <div className="stat-tile">
          <span className="stat-value">{min.creneau_min}</span>
          <span className="stat-label">Créneau (min)</span>
        </div>
        <div className="stat-tile">
          <span className="stat-value">
            {min.planifie_min}
            {min.partiel && <span className="stat-hint"> (partiel)</span>}
          </span>
          <span className="stat-label">Planifié (min)</span>
        </div>
        <div className={"stat-tile" + (min.marge_min < 0 ? " stat-neg" : "")}>
          <span className="stat-value">{min.marge_min}</span>
          <span className="stat-label">{min.marge_min < 0 ? "Dépassement (min)" : "Marge (min)"}</span>
        </div>
        <div className="stat-tile">
          <span className="stat-value">{min.opposition_min}</span>
          <span className="stat-label">Opposition (min)</span>
        </div>
      </div>

      <section className="seance-blocks">
        <h2>Blocs de la séance</h2>
        <ol className="timeline">
          {plan.blocks.map((b, bi) => (
            <li className="seance-block" key={bi}>
              <div className="seance-block-head">
                <span className={"kind-badge kind-" + b.kind}>{KIND_LABELS[b.kind] ?? b.kind}</span>
                <input
                  className="block-label"
                  type="text"
                  aria-label="Libellé du bloc"
                  value={b.label}
                  onChange={(e) =>
                    updatePlan((d) => void (d.blocks[bi].label = e.target.value))
                  }
                />
                <button
                  className="block-delete"
                  aria-label={`Supprimer le bloc ${b.label}`}
                  onClick={() => removeBlock(bi)}
                >
                  ×
                </button>
              </div>

              {/* Coach en charge du bloc (v1.1, 2026-11-24) : ligne dédiée,
                  mobile-first. */}
              {moi && coachRefs.length > 0 && (
                <label className="seance-block-coach field">
                  <span className="field-label">En charge</span>
                  <select
                    className="select-input"
                    aria-label={`Coach en charge du bloc ${b.label}`}
                    value={b.coach ?? ""}
                    onChange={(e) =>
                      updatePlan((d) => {
                        d.blocks[bi].coach = e.target.value || null;
                      })
                    }
                  >
                    <option value="">— non attribué —</option>
                    {coachRefs.map((c) => (
                      <option key={(c.login ? "c:" : "n:") + c.nom} value={c.nom}>
                        {c.nom}
                        {c.club ? ` (${c.club})` : ""}
                      </option>
                    ))}
                  </select>
                </label>
              )}

              {b.kind === "WORKSHOPS" ? (
                <div className="workshops">
                  {(b.rounds ?? []).map((r, ri) => (
                    <div className="rotation" key={ri}>
                      <div className="rotation-head">
                        <span className="rotation-title">Rotation {ri + 1}</span>
                        {(b.rounds ?? []).length > 1 && (
                          <button
                            className="block-delete"
                            aria-label={`Supprimer la rotation ${ri + 1}`}
                            onClick={() => removeRound(bi, ri)}
                          >
                            ×
                          </button>
                        )}
                      </div>
                      <div className="field-row">
                        <label className="field">
                          <span className="field-label">Travail (min)</span>
                          <input
                            className="num-input"
                            type="number"
                            inputMode="numeric"
                            min={1}
                            step={1}
                            value={r.work_min}
                            onChange={(e) =>
                              updatePlan((d) => {
                                const blk = d.blocks[bi];
                                const rnd = blk.rounds![ri];
                                const v = Number.isInteger(+e.target.value) ? +e.target.value : 0;
                                rnd.work_min = v;
                                blk.duration_min = blk.rounds!.reduce(
                                  (a, x) => a + x.work_min + x.transition_min,
                                  0
                                );
                              })
                            }
                          />
                        </label>
                        <label className="field">
                          <span className="field-label">Transition (min)</span>
                          <input
                            className="num-input"
                            type="number"
                            inputMode="numeric"
                            min={0}
                            step={1}
                            value={r.transition_min}
                            onChange={(e) =>
                              updatePlan((d) => {
                                const blk = d.blocks[bi];
                                const rnd = blk.rounds![ri];
                                const v = Number.isInteger(+e.target.value) ? +e.target.value : 0;
                                rnd.transition_min = v;
                                blk.duration_min = blk.rounds!.reduce(
                                  (a, x) => a + x.work_min + x.transition_min,
                                  0
                                );
                              })
                            }
                          />
                        </label>
                      </div>
                      {r.assignments.map((s, si) => (
                        <button
                          className="slot-row"
                          key={si}
                          onClick={() =>
                            setPicker({ kind: "slot", blockIndex: bi, roundIndex: ri, slotIndex: si })
                          }
                        >
                          <span className="slot-who">
                            {groupLabel(s.group_id)} → {s.station_id}
                          </span>
                          <span className="slot-exercise">
                            {s.variant_id ? cardById[s.variant_id]?.title ?? s.variant_id : "Choisir un exercice…"}
                          </span>
                        </button>
                      ))}
                    </div>
                  ))}
                  <div className="rotation-foot">
                    <span className="stat-label">
                      Durée du bloc : {b.duration_min} min (somme des rotations)
                    </span>
                    <button className="add-round-btn" onClick={() => addRound(bi)}>
                      + Rotation
                    </button>
                  </div>
                </div>
              ) : (
                <div className="simple-block">
                  <label className="field">
                    <span className="field-label">Durée (min)</span>
                    <input
                      className="num-input"
                      type="number"
                      inputMode="numeric"
                      min={1}
                      step={1}
                      value={b.duration_min ?? ""}
                      onChange={(e) =>
                        updatePlan((d) => {
                          // n4 : champ vide → durée non saisie (null, « total partiel »
                          // honnête) plutôt que 0 (bloc « 0 min » trompeur).
                          d.blocks[bi].duration_min =
                            e.target.value === ""
                              ? null
                              : Number.isInteger(+e.target.value)
                                ? +e.target.value
                                : 0;
                        })
                      }
                    />
                  </label>
                  {b.variant_ids.length > 0 && (
                    <div className="assigned-row">
                      {b.variant_ids.map((id, i) => (
                        <button
                          className="chip assigned-chip"
                          key={id + "-" + i}
                          title="Retirer de ce bloc"
                          onClick={() =>
                            updatePlan((d) => {
                              d.blocks[bi].variant_ids.splice(i, 1);
                            })
                          }
                        >
                          {cardById[id]?.title ?? id} <span className="chip-x">×</span>
                        </button>
                      ))}
                    </div>
                  )}
                  <button className="add-round-btn" onClick={() => setPicker({ kind: "block", blockIndex: bi })}>
                    + Exercice
                  </button>
                </div>
              )}
            </li>
          ))}
        </ol>

        <h3 className="add-block-title">Ajouter un bloc</h3>
        <div className="add-block-row">
          {(Object.keys(KIND_LABELS) as SessionPlan["blocks"][number]["kind"][]).map((k) => (
            <button key={k} className="add-block-btn" onClick={() => addBlock(k)}>
              + {KIND_LABELS[k]}
            </button>
          ))}
        </div>
      </section>

      {(plan.pending_decisions?.length || plan.note) && (
        <section className="seance-notes">
          <h2>À confirmer (gabarit)</h2>
          {plan.note && <p className="note-text">{plan.note}</p>}
          {plan.pending_decisions?.length ? (
            <ul>
              {plan.pending_decisions.map((d, i) => (
                <li key={i}>{d}</li>
              ))}
            </ul>
          ) : null}
        </section>
      )}

      <section className="seance-check">
        <h2>Contrôles structurels</h2>
        {localCheck.valide ? (
          <p className="check-ok">Séance cohérente : aucun contrôle bloquant.</p>
        ) : (
          <ul className="check-errs">
            {localCheck.erreurs.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        )}
        {localCheck.avertissements.length > 0 && (
          <ul className="check-warns">
            {localCheck.avertissements.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        )}
        <div className="check-actions">
          <button className="apply-btn" onClick={runServerCheck} disabled={checking}>
            {checking ? "Vérification en cours…" : "Vérifier (serveur)"}
          </button>
        </div>
        {serverError && <p className="check-err-text">Vérification serveur impossible : {serverError}</p>}
        {serverCheck && serverTime && (
          <div className="seance-server-result">
            <p className={"check-ok " + (serverDiverges ? "check-diverge" : "")}>
              Serveur, {serverTime} : {serverCheck.valide ? "valide" : "non valide"} —{" "}
              {serverCheck.erreurs.length} erreur{serverCheck.erreurs.length > 1 ? "s" : ""},{" "}
              {serverCheck.avertissements.length} avertissement
              {serverCheck.avertissements.length > 1 ? "s" : ""}.
            </p>
            {serverDiverges && (
              <p>
                Résultat serveur différent du calcul local (le serveur fait foi) :
              </p>
            )}
            {serverDiverges && (
              <>
                {serverCheck.erreurs.map((e, i) => (
                  <p className="check-err-text" key={"e" + i}>{e}</p>
                ))}
                {serverCheck.avertissements.map((a, i) => (
                  <p className="check-warn-text" key={"a" + i}>{a}</p>
                ))}
              </>
            )}
          </div>
        )}
      </section>

      <section className="seance-save">
        <h2>Sauvegarde et reprise</h2>
        <p className="save-status" aria-live="polite">
          {savedAt
            ? `Brouillon sauvegardé le ${savedLabel(savedAt)} (ce navigateur).`
            : "Aucun brouillon sauvegardé pour l'instant."}
        </p>
        <div className="check-actions">
          <button className="apply-btn" onClick={exportDraft}>
            ⬇ Exporter (JSON)
          </button>
          <button className="reset-btn" onClick={() => fileRef.current?.click()}>
            ⬆ Importer (JSON)
          </button>
          <button className="reset-btn" onClick={restartFromTrame}>
            Effacer et repartir de la trame U8
          </button>
        </div>
        <input
          ref={fileRef}
          type="file"
          accept="application/json,.json"
          hidden
          onChange={onImportFile}
        />
        {importError && <p className="check-err-text">{importError}</p>}

        {moi ? (
          <div className="compte-seance">
            <h3>Sur votre compte</h3>
            <p className="save-status" aria-live="polite">
              {compteMsg ??
                `Connecté en tant que ${moi.login} : vos brouillons et vos propositions restent sur ce compte, sur tous vos appareils.`}
            </p>
            <div className="check-actions">
              <button
                className="apply-btn"
                onClick={() => void saveToAccount()}
                disabled={compteBusy}
              >
                {compteBusy ? "…" : "💾 Sauvegarder sur mon compte"}
              </button>
              <button
                className="reset-btn"
                onClick={() => void enregistrerProposition()}
                disabled={compteBusy}
              >
                Enregistrer comme proposition
              </button>
            </div>
            {brouillons.length > 0 && (
              <div className="compte-liste">
                <h4>Mes brouillons</h4>
                {brouillons.map((b) => (
                  <div className="compte-ligne" key={b.id}>
                    <span className="compte-ligne-titre">
                      {b.titre}
                      <small>{savedLabel(b.saved_at)}</small>
                    </span>
                    <span className="compte-ligne-actions">
                      <button
                        onClick={() => void reprendreBrouillon(b.id)}
                        disabled={compteBusy}
                      >
                        Reprendre
                      </button>
                      <button
                        className="danger"
                        onClick={() => void supprimerDuCompte(b.id)}
                        disabled={compteBusy}
                      >
                        Supprimer
                      </button>
                    </span>
                  </div>
                ))}
              </div>
            )}
            {propositions.length > 0 && (
              <div className="compte-liste">
                <h4>Mes propositions</h4>
                {pdfMsg && (
                  <p className="save-status" aria-live="polite">
                    {pdfMsg}
                  </p>
                )}
                {waHref && (
                  <a
                    className="share-link"
                    href={waHref}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Ouvrir WhatsApp avec le récapitulatif
                  </a>
                )}
                {propositions.map((p) => (
                  <div className="compte-ligne" key={p.id}>
                    <span className="compte-ligne-titre">
                      {p.titre}{" "}
                      {p.valide ? (
                        <span className="badge badge-green">valide</span>
                      ) : (
                        <span className="badge badge-red">non valide</span>
                      )}
                      <small>{savedLabel(p.saved_at)}</small>
                    </span>
                    {p.valide && (
                      <span className="compte-ligne-actions">
                        <button
                          onClick={() => void previsualiserPdf(p)}
                          disabled={pdfBusy === p.id || compteBusy}
                        >
                          Aperçu
                        </button>
                        <button
                          onClick={() => void partagerEnPdf(p)}
                          disabled={pdfBusy === p.id || compteBusy}
                        >
                          {pdfBusy === p.id ? "Génération…" : "Partager en PDF"}
                        </button>
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
            {propResult && (
              <div className="seance-server-result">
                <p className="check-ok">
                  Proposition n°{propResult.id} enregistrée —{" "}
                  {propResult.valide ? "valide" : "non valide"} :{" "}
                  {propResult.erreurs.length} erreur
                  {propResult.erreurs.length > 1 ? "s" : ""},{" "}
                  {propResult.avertissements.length} avertissement
                  {propResult.avertissements.length > 1 ? "s" : ""}.
                </p>
                {propResult.erreurs.map((e, i) => (
                  <p className="check-err-text" key={"e" + i}>
                    {e}
                  </p>
                ))}
              </div>
            )}
          </div>
        ) : (
          <p className="compte-invite">
            <a href="/connexion">Connectez-vous</a> pour garder vos brouillons
            et vos propositions sur votre compte, accessibles depuis tout
            appareil.
          </p>
        )}
      </section>

      {picker && (
        <>
          <div className="sheet-backdrop" onClick={() => setPicker(null)} />
          <div className="sheet" role="dialog" aria-modal="true" aria-label="Choisir un exercice">
            <div className="sheet-handle" aria-hidden="true" />
            <h2>Choisir un exercice</h2>
            <input
              className="search-input"
              type="search"
              placeholder="Rechercher (titre, résumé, titre original)…"
              aria-label="Rechercher un exercice"
              value={pickerQuery}
              onChange={(e) => setPickerQuery(e.target.value)}
            />
            <div className="picker-list">
              {pickerResults.length === 0 && <p className="picker-empty">Aucun exercice ne correspond.</p>}
              {pickerResults.map((c) => (
                <button
                  key={c.id}
                  className="picker-row"
                  onClick={() => pickExercise(c.id)}
                >
                  <span className="card-title">{c.title}</span>
                  <span className="picker-meta">
                    {BADGE_LABELS[c.state] && (
                      <span className={"badge " + BADGE_CLASS[c.state]}>{BADGE_LABELS[c.state]}</span>
                    )}
                    {cardDurationLabel(c.planning_min_seconds, c.planning_max_seconds, c.duration_status)}
                  </span>
                </button>
              ))}
            </div>
            <div className="sheet-footer">
              <button className="reset-btn" onClick={() => setPicker(null)}>
                Fermer
              </button>
            </div>
          </div>
        </>
      )}
      {pdfPreview && (
        <>
          <div
            className="sheet-backdrop"
            onClick={() => {
              if (pdfBusy === null) setPdfPreview(null);
            }}
          />
          <div
            className="sheet pdf-preview"
            role="dialog"
            aria-modal="true"
            aria-label="Aperçu de la fiche PDF"
          >
            <div className="sheet-handle" aria-hidden="true" />
            <h2>Aperçu — fiche PDF</h2>
            <p className="pdf-preview-note">
              Ce que vous voyez est exactement la pièce qui sera partagée
              ({pdfPreview.pages.length} page
              {pdfPreview.pages.length > 1 ? "s" : ""}), sans les noms de
              joueurs.
            </p>
            <div className="pdf-preview-pages">
              {pdfPreview.pages.map((pg, i) => (
                <img
                  key={i}
                  className="pdf-preview-page"
                  src={pg.data}
                  alt={`Page ${i + 1} de la fiche PDF`}
                />
              ))}
            </div>
            <div className="sheet-footer">
              <button className="reset-btn" onClick={() => setPdfPreview(null)}>
                Fermer
              </button>
              <button
                className="apply-btn"
                onClick={() => {
                  const m: MatierePdf = {
                    prop: pdfPreview.prop,
                    fiches: pdfPreview.fiches,
                    conseils: pdfPreview.conseils,
                  };
                  const ref = pdfPreview.p;
                  setPdfPreview(null);
                  void partagerEnPdf(ref, m);
                }}
              >
                Partager en PDF
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
