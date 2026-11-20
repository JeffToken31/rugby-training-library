// Lot 5 — compte, brouillons et propositions rattachés au compte (B1, C1).
// Miroir du contrat webapp.py / app_store.py. Le cookie de session est
// HttpOnly : le navigateur l'envoie, le client ne le lit jamais.

import type { MinutageDerivee, SessionPlan } from "./types";

export interface Moi {
  login: string;
  created_at: string;
}

export interface BrouillonRef {
  id: string;
  titre: string;
  saved_at: string;
}

export interface Brouillon extends BrouillonRef {
  plan: SessionPlan;
}

export interface PropositionRef {
  id: number;
  titre: string;
  valide: boolean;
  saved_at: string;
}

export interface Proposition extends PropositionRef {
  plan: SessionPlan;
  erreurs: string[];
  avertissements: string[];
  minutage: MinutageDerivee;
}

const JSON_HEADERS = { "Content-Type": "application/json" };

async function erreurDe(res: Response, defaut: string): Promise<never> {
  let message = defaut;
  try {
    const body = (await res.json()) as { error?: string };
    if (typeof body?.error === "string" && body.error) message = body.error;
  } catch {
    // corps lisible absent : on garde le message par défaut.
  }
  throw new Error(`${message} (HTTP ${res.status})`);
}

/** Identité du compte courant, ou null si déconnecté (401). */
export async function fetchMoi(): Promise<Moi | null> {
  const res = await fetch("/api/moi", { cache: "no-store" });
  if (res.status === 401) return null;
  if (!res.ok) await erreurDe(res, "Impossible de charger votre compte");
  return (await res.json()) as Moi;
}

export async function inscrire(login: string, password: string): Promise<Moi> {
  const res = await fetch("/api/auth/inscription", {
    method: "POST",
    cache: "no-store",
    headers: JSON_HEADERS,
    body: JSON.stringify({ login, password }),
  });
  if (!res.ok) await erreurDe(res, "Inscription impossible");
  return (await res.json()) as Moi;
}

export async function connecter(login: string, password: string): Promise<Moi> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    cache: "no-store",
    headers: JSON_HEADERS,
    body: JSON.stringify({ login, password }),
  });
  if (!res.ok) await erreurDe(res, "Connexion impossible");
  return (await res.json()) as Moi;
}

export async function seDeconnecter(): Promise<void> {
  const res = await fetch("/api/auth/deconnexion", {
    method: "POST",
    cache: "no-store",
  });
  if (!res.ok) await erreurDe(res, "Déconnexion impossible");
}

export async function listerBrouillons(): Promise<BrouillonRef[]> {
  const res = await fetch("/api/brouillons", { cache: "no-store" });
  if (!res.ok) await erreurDe(res, "Impossible de charger vos brouillons");
  const body = (await res.json()) as { brouillons: BrouillonRef[] };
  return body.brouillons;
}

export async function chargerBrouillon(id: string): Promise<Brouillon> {
  const res = await fetch(`/api/brouillons/${encodeURIComponent(id)}`, {
    cache: "no-store",
  });
  if (!res.ok) await erreurDe(res, "Brouillon introuvable");
  return (await res.json()) as Brouillon;
}

/** Enregistre (ou remplace) le brouillon ; renvoie {id, titre, saved_at}. */
export async function sauvegarderBrouillon(
  id: string,
  titre: string,
  plan: SessionPlan
): Promise<BrouillonRef> {
  const res = await fetch(`/api/brouillons/${encodeURIComponent(id)}`, {
    method: "PUT",
    cache: "no-store",
    headers: JSON_HEADERS,
    body: JSON.stringify({ titre, plan }),
  });
  if (!res.ok) await erreurDe(res, "Sauvegarde impossible");
  return (await res.json()) as BrouillonRef;
}

export async function supprimerBrouillon(id: string): Promise<void> {
  const res = await fetch(`/api/brouillons/${encodeURIComponent(id)}`, {
    method: "DELETE",
    cache: "no-store",
  });
  if (!res.ok) await erreurDe(res, "Suppression impossible");
}

export async function listerPropositions(): Promise<PropositionRef[]> {
  const res = await fetch("/api/propositions", { cache: "no-store" });
  if (!res.ok) await erreurDe(res, "Impossible de charger vos propositions");
  const body = (await res.json()) as { propositions: PropositionRef[] };
  return body.propositions;
}

/**
 * Enregistre le snapshot immuable de la séance courante (D1) avec le
 * résultat de validation calculé au moment de l'enregistrement.
 */
export async function creerProposition(
  titre: string,
  plan: SessionPlan
): Promise<Proposition> {
  const res = await fetch("/api/propositions", {
    method: "POST",
    cache: "no-store",
    headers: JSON_HEADERS,
    body: JSON.stringify({ titre, plan }),
  });
  if (!res.ok) await erreurDe(res, "Enregistrement de la proposition impossible");
  return (await res.json()) as Proposition;
}

export async function chargerProposition(id: number): Promise<Proposition> {
  const res = await fetch(`/api/propositions/${encodeURIComponent(id)}`, {
    cache: "no-store",
  });
  if (!res.ok) await erreurDe(res, "Proposition introuvable");
  return (await res.json()) as Proposition;
}
