// Lot L4 (2026-11-25) — préremplissage du constructeur de séance depuis la
// page « club ». Persistance 100 % client (localStorage) : la page écrit un
// snapshot, le constructeur le consomme UNE SEULE FOIS à l'ouverture — aucun
// écran intermédiaire, aucun appel réseau. Le snapshot est le même contrat
// que l'attachement d'équipe dans le constructeur (D1 : la séance conserve
// son instantané, indépendamment des éditions ultérieures de l'équipe).

import type { SessionPlan } from "./types";

const KEY = "rtrl-prefill-v1";

// Snapshot de l'équipe : même forme que `SessionPlan.team`.
export type PrefillTeam = NonNullable<SessionPlan["team"]>;

export type PrefillPayload = {
  team: PrefillTeam;
  // Joueurs de l'équipe (prénom + nom, RGPD v1.1), ordre saisi.
  joueurs: string[];
  // Coach par défaut (nom ou login) : premier coach rattaché à l'équipe,
  // sinon le compte connecté — null si aucune des deux.
  coach_par_defaut: string | null;
};

function isPrefillTeam(t: unknown): t is PrefillTeam {
  if (typeof t !== "object" || t === null) return false;
  const o = t as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.nom === "string" &&
    (o.club === null || typeof o.club === "string") &&
    (o.categorie === null || typeof o.categorie === "string") &&
    (o.effectif === null || typeof o.effectif === "number")
  );
}

function isPrefill(p: unknown): p is PrefillPayload {
  if (typeof p !== "object" || p === null) return false;
  const o = p as Record<string, unknown>;
  return (
    isPrefillTeam(o.team) &&
    Array.isArray(o.joueurs) &&
    (o.joueurs as unknown[]).every((j) => typeof j === "string") &&
    (o.coach_par_defaut === null || typeof o.coach_par_defaut === "string")
  );
}

// Écrit le snapshot avant de basculer vers le constructeur. Échec silencieux
// si le stockage est indisponible : on ouvre simplement une séance vierge.
export function ecrirePrefill(p: PrefillPayload): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(p));
  } catch {
    // stockage indisponible : rien à préremplir
  }
}

// Lit puis SUPPRIME le snapshot (consommation unique). `null` = absent,
// illisible ou de forme invalide — on ne plante jamais l'UI sur un
// localStorage corrompu.
export function consommerPrefill(): PrefillPayload | null {
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return null;
    window.localStorage.removeItem(KEY);
    const parsed: unknown = JSON.parse(raw);
    return isPrefill(parsed) ? parsed : null;
  } catch {
    return null;
  }
}
