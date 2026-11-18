// Accès à l'API JSON de webapp.py (même origine en prod : http://<hôte>:8347).

import type { CatalogueView, Fiche } from "./types";

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
