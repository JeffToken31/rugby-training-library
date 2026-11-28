// Accès à l'API JSON de webapp.py (même origine en prod : http://<hôte>:8347).

import type {
  CatalogueView,
  ConseilsPayload,
  Fiche,
  SeanceCheck,
  SessionPlan,
} from "./types";

export async function fetchCatalogue(): Promise<CatalogueView> {
  const res = await fetch("/api/catalogue", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Catalogue indisponible (HTTP ${res.status})`);
  }
  return (await res.json()) as CatalogueView;
}

export async function fetchFiche(id: string): Promise<Fiche> {
  const res = await fetch(`/api/fiches/${encodeURIComponent(id)}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Fiche introuvable (HTTP ${res.status})`);
  }
  return (await res.json()) as Fiche;
}

export async function fetchTrameU8(): Promise<SessionPlan> {
  const res = await fetch("/api/seances/trame-u8", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Trame de référence indisponible (HTTP ${res.status})`);
  }
  return (await res.json()) as SessionPlan;
}

export async function fetchConseils(): Promise<ConseilsPayload> {
  const res = await fetch("/api/conseils", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Conseils indisponibles (HTTP ${res.status})`);
  }
  return (await res.json()) as ConseilsPayload;
}

export async function validerSeance(plan: SessionPlan): Promise<SeanceCheck> {
  const res = await fetch("/api/seances/valider", {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(plan),
  });
  if (!res.ok) {
    throw new Error(`Validation impossible (HTTP ${res.status})`);
  }
  return (await res.json()) as SeanceCheck;
}
