// Lot 3 — miroir client exact de session_plan.py + webapp.valider_seance.
// Le but : recalcul immédiat (live) des contrôles structurels dans l'UI,
// avec les mêmes messages et le même ordre que le serveur. Le bouton
// « Vérifier (serveur) » reste la référence (POST /api/seances/valider).

import type {
  Card,
  MinutageDerivee,
  SeanceCheck,
  SessionPlan,
} from "./types";

// Mêmes libellés de blocs que le validateur compte.
export const KIND_LABELS: Record<string, string> = {
  OPPOSITION: "Opposition",
  WORKSHOPS: "Ateliers",
  JEU: "Jeu",
  WARMUP: "Échauffement",
  PAUSE: "Pause",
};

// Miroir de session_plan.positive / entier : entier strict > 0, flottants
// entiers normalisés (7.0 → 7) — en JSON, 7.0 et 7 sont indistinguables.
// En JS, boolean n'est pas number, pas de faux positif.
function positive(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value > 0;
}

// Miroir de webapp.minutage_derivee (tous les types, jamais stockée).
export function minutageDerivee(plan: SessionPlan): MinutageDerivee {
  // m1 : durées normalisées comme session_plan.entier (flottants entiers →
  // entier strict, le reste → null) — mêmes ensets acceptés que le serveur.
  const entier = (v: unknown): number | null =>
    typeof v === "number" && Number.isInteger(v) ? (v as number) : null;
  const blocks = plan.blocks ?? [];
  const durees = blocks.map((b) => entier(b.duration_min));
  const planifie = durees.reduce<number>(
    (acc, d) => (d === null ? acc : acc + d),
    0
  );
  let creneau = entier(plan.creneau_min);
  if (creneau === null) creneau = 0;
  const opposition = blocks.reduce<number>(
    (acc, b) =>
      b.kind === "OPPOSITION" || b.kind === "JEU"
        ? acc + (entier(b.duration_min) ?? 0)
        : acc,
    0
  );
  return {
    creneau_min: creneau,
    planifie_min: planifie,
    marge_min: creneau - planifie,
    opposition_min: opposition,
    partiel: durees.some((d) => d === null),
  };
}

// Miroir de session_plan.minutage (contrôles sur le créneau/total).
function minutageContrôles(blocks: { duration_min: number | null; label: string; kind: string }[], plan: SessionPlan, errors: string[]): boolean {
  const creneau = plan.creneau_min;
  if (!positive(creneau)) {
    errors.push("Créneau invalide : 'creneau_min' absent ou non strictement positif.");
    return false;
  }
  const sansDuree = blocks
    .filter((b) => b.duration_min === null || b.duration_min === undefined)
    .map((b) => b.label || b.kind);
  if (sansDuree.length > 0) {
    errors.push(
      "Avertissement — Le total est partiel : durée manquante sur " +
        sansDuree.join(", ") +
        "."
    );
    return false;
  }
  const total = blocks.reduce((acc, b) => acc + (b.duration_min as number), 0);
  if (total !== plan.duration_min) {
    errors.push("Durée totale différente de la somme des blocs");
    return false;
  }
  if (total > creneau) {
    errors.push(
      "Avertissement — Dépassement du créneau : " +
        total +
        " min planifiées pour un créneau de " +
        creneau +
        " min."
    );
  }
  return true;
}

// Miroir de session_plan.validate : mêmes erreurs, même ordre.
// `etatParId` = état qualité (ex. "INCOMPLETE") par id de fiche.
export function validerLocale(
  plan: SessionPlan,
  etatParId: Record<string, string>
): SeanceCheck {
  const errors: string[] = [];
  const groups = plan.groups ?? [];
  const groupIds = groups.map((g) => g.id);
  if (groups.length === 0 || new Set(groupIds).size !== groupIds.length) {
    errors.push("Groupes absents ou répétés");
  }
  if (groups.some((g) => !positive(g.players))) {
    errors.push("Effectifs de groupe invalides");
  } else if (groups.reduce((a, g) => a + g.players, 0) !== plan.players) {
    errors.push("Effectif total différent de la somme des groupes");
  }
  const blocks = plan.blocks ?? [];
  if (blocks.length === 0) {
    errors.push("Durées de blocs invalides");
  } else if (
    blocks.some(
      (b) => b.duration_min !== null && b.duration_min !== undefined && !positive(b.duration_min)
    )
  ) {
    errors.push("Durées de blocs invalides");
  } else {
    minutageContrôles(blocks, plan, errors);
  }
  for (const block of blocks) {
    const refs: (string | null)[] = [...(block.variant_ids ?? [])];
    const rounds = block.rounds ?? [];
    if (rounds.length > 0) {
      const dureeBloc = block.duration_min;
      const rotationInvalide = rounds.some(
        (x) =>
          !positive(x.work_min) ||
          typeof x.transition_min !== "number" ||
          !Number.isInteger(x.transition_min) ||
          x.transition_min < 0
      );
      if (rotationInvalide) {
        errors.push("Durée de rotation invalide");
      } else if (
        dureeBloc !== null &&
        dureeBloc !== undefined &&
        rounds.reduce((a, x) => a + x.work_min + x.transition_min, 0) !== dureeBloc
      ) {
        errors.push("Durées de rotation incohérentes");
      }
      for (const rotation of rounds) {
        const slots = rotation.assignments ?? [];
        const slotGroups = slots.map((s) => s.group_id).sort();
        const planGroups = [...groupIds].sort();
        if (
          slotGroups.length !== planGroups.length ||
          slotGroups.some((v, i) => v !== planGroups[i])
        ) {
          errors.push("Chaque groupe doit être affecté une fois par rotation");
        }
        if (new Set(slots.map((s) => s.station_id)).size !== slots.length) {
          errors.push("Atelier occupé par plusieurs groupes simultanément");
        }
        refs.push(...slots.map((s) => s.variant_id));
      }
    }
    for (const eid of refs) {
      if (eid === null || eid === undefined || !(eid in etatParId)) {
        errors.push("Exercice inconnu : " + String(eid));
      } else if (etatParId[eid] === "INCOMPLETE") {
        errors.push("Exercice trop incomplet : " + String(eid));
      }
    }
  }
  const bloquantes = errors.filter((m) => !m.startsWith("Avertissement"));
  const avertissements = errors.filter((m) => m.startsWith("Avertissement"));
  return {
    valide: bloquantes.length === 0,
    erreurs: bloquantes,
    avertissements,
    minutage: minutageDerivee(plan),
  };
}

// État qualité par id, dérivé du catalogue (miroir de BY_ID côté API).
export function etatParIdDe(cards: Card[]): Record<string, string> {
  const m: Record<string, string> = {};
  for (const c of cards) m[c.id] = c.state;
  return m;
}
