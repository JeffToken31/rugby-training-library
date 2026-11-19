// Lot 4 — sauvegarde et reprise du brouillon de séance.
// Persistance 100 % client (localStorage) : le serveur `webapp.py` reste en
// lecture à froid, aucun appel réseau pour sauvegarder. Un seul brouillon par
// navigateur. L'export/import est du JSON brut : même contrat que
// POST /api/seances/valider (un plan est un objet, pas un wrapper).

import type { SessionPlan } from "./types";

const KEY = "rtrl-seance-draft-v1";

export type SavedDraft = {
  saved_at: string; // horodatage ISO de la dernière sauvegarde
  plan: SessionPlan;
};

// Vérification minimale de la forme d'un plan : un créneau, une durée totale,
// des groupes et des blocs typés. Plus large que le validateur (qui juge la
// cohérence au montage) : l'import n'est pas un contrôle, juste une garde
// contre les fichiers corrompus ou hétérogènes.
function isPlan(p: unknown): p is SessionPlan {
  if (typeof p !== "object" || p === null) return false;
  const o = p as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.creneau_min === "number" &&
    typeof o.duration_min === "number" &&
    Array.isArray(o.groups) &&
    Array.isArray(o.blocks) &&
    (o.blocks as unknown[]).every((b) => {
      const b2 = b as Record<string, unknown>;
      return typeof b2.kind === "string" && typeof b2.label === "string";
    })
  );
}

// Lit le brouillon sauvegardé. `null` = absent, illisible ou de forme
// invalide (on ne plante jamais l'UI sur un localStorage corrompu).
export function loadDraft(): SavedDraft | null {
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { saved_at?: unknown; plan?: unknown };
    if (!parsed || !isPlan(parsed.plan)) return null;
    return {
      saved_at: typeof parsed.saved_at === "string" ? parsed.saved_at : "",
      plan: parsed.plan,
    };
  } catch {
    return null;
  }
}

// Sauvegarde à chaud (appelée à chaque modification du plan). Renvoie
// l'horodatage ISO écrit, ou null si le stockage est indisponible/plein —
// la séance reste éditable en mémoire dans ce cas.
export function saveDraft(plan: SessionPlan): string | null {
  try {
    const value: SavedDraft = { saved_at: new Date().toISOString(), plan };
    window.localStorage.setItem(KEY, JSON.stringify(value));
    return value.saved_at;
  } catch {
    return null;
  }
}

export function clearDraft(): void {
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    // stockage indisponible : rien à retirer
  }
}

// Parse un import (fichier JSON). `null` = fichier invalide.
export function parseImport(text: string): SessionPlan | null {
  try {
    const p: unknown = JSON.parse(text);
    return isPlan(p) ? p : null;
  } catch {
    return null;
  }
}
