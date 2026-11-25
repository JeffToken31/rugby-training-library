// Lot 5 — compte, brouillons et propositions rattachés au compte (B1, C1).
// Miroir du contrat webapp.py / app_store.py. Le cookie de session est
// HttpOnly : le navigateur l'envoie, le client ne le lit jamais.

import type { Equipe, GroupeEquipe, MinutageDerivee, SessionPlan } from "./types";
import type { ClubTheme } from "./theme";

export interface Moi {
  login: string;
  created_at: string;
  // Lot club (cadrage 03) : champs facultatifs, null si non renseignés.
  club: string | null;
  categorie: string | null;
  // Lot peaufinage B (2026-11-25) : identité du club (couleurs + logo),
  // commune à tous les comptes du club ; null si le club n'en a pas.
  theme: ClubTheme | null;
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

export async function inscrire(
  login: string,
  password: string,
  club?: string,
  categorie?: string
): Promise<Moi> {
  // Champs du lot club : envoyés seulement s'ils sont renseignés (le
  // serveur les gère comme optionnels).
  const corps: Record<string, string> = { login, password };
  if (club) corps.club = club;
  if (categorie) corps.categorie = categorie;
  const res = await fetch("/api/auth/inscription", {
    method: "POST",
    cache: "no-store",
    headers: JSON_HEADERS,
    body: JSON.stringify(corps),
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

// ------------------------------------------------------------ lot équipes
// Tranché 2026-11-22 : « coachs disponibles » = tous les comptes
// enregistrés ; v1.1 (2026-11-24) : + coachs sans compte ajoutés par nom.
// Les brouillons et propositions d'autrui restent strictement privés (C1).

/** Identité minimale d'un coach : un compte (login) ou un nom seul.
 * `id` = slug serveur pour un coach nommé (retrait possible), null pour
 * un compte (lot L4, 2026-11-25). */
export interface CoachRef {
  nom: string;
  login: string | null;
  club: string | null;
  categorie: string | null;
  id: string | null;
}

export async function listerCoachs(): Promise<CoachRef[]> {
  const res = await fetch("/api/coachs", { cache: "no-store" });
  if (!res.ok) await erreurDe(res, "Impossible de charger les coachs");
  const body = (await res.json()) as { coachs: CoachRef[] };
  return body.coachs;
}

/** Coach sans compte fraîchement ajouté (réponse du POST /api/coachs). */
export interface CoachAjoute {
  id: string;
  nom: string;
  club: string | null;
  saved_at: string;
}

/** Ajoute un coach sans compte par nom (v1.1, 2026-11-24) ; 409 si doublon. */
export async function ajouterCoach(
  nom: string,
  club?: string | null
): Promise<CoachAjoute> {
  const res = await fetch("/api/coachs", {
    method: "POST",
    cache: "no-store",
    headers: JSON_HEADERS,
    body: JSON.stringify({ nom, club: club || null }),
  });
  if (!res.ok) await erreurDe(res, "Ajout du coach impossible");
  return (await res.json()) as CoachAjoute;
}

/** Supprime un coach nommé du compte (404 si inconnu). */
export async function supprimerCoach(id: string): Promise<void> {
  const res = await fetch(`/api/coachs/${encodeURIComponent(id)}`, {
    method: "DELETE",
    cache: "no-store",
  });
  if (!res.ok) await erreurDe(res, "Suppression du coach impossible");
}

export async function listerEquipes(): Promise<Equipe[]> {
  const res = await fetch("/api/equipes", { cache: "no-store" });
  if (!res.ok) await erreurDe(res, "Impossible de charger vos équipes");
  const body = (await res.json()) as { equipes: Equipe[] };
  return body.equipes;
}

/** Corps de création / mise à jour d'une équipe (PUT = complète). */
export interface CorpsEquipe {
  nom: string;
  club?: string | null;
  categorie?: string | null;
  effectif?: number | null;
  coachs?: string[];
  /** Joueurs de l'équipe (prénom + nom), lot L3 — `undefined` ou liste. */
  joueurs?: string[];
  /** Groupes nommés librement de l'équipe, lot peaufinage C — `undefined`
   * ou liste ; les joueurs d'un groupe doivent appartenir à `joueurs`. */
  groupes?: GroupeEquipe[];
}

/** Crée une équipe (identifiant slug généré côté serveur si absent). */
export async function creerEquipe(corps: CorpsEquipe): Promise<Equipe> {
  const res = await fetch("/api/equipes", {
    method: "POST",
    cache: "no-store",
    headers: JSON_HEADERS,
    body: JSON.stringify(corps),
  });
  if (!res.ok) await erreurDe(res, "Création de l'équipe impossible");
  return (await res.json()) as Equipe;
}

export async function mettreAJourEquipe(
  id: string,
  corps: CorpsEquipe
): Promise<Equipe> {
  const res = await fetch(`/api/equipes/${encodeURIComponent(id)}`, {
    method: "PUT",
    cache: "no-store",
    headers: JSON_HEADERS,
    body: JSON.stringify(corps),
  });
  if (!res.ok) await erreurDe(res, "Mise à jour de l'équipe impossible");
  return (await res.json()) as Equipe;
}

export async function supprimerEquipe(id: string): Promise<void> {
  const res = await fetch(`/api/equipes/${encodeURIComponent(id)}`, {
    method: "DELETE",
    cache: "no-store",
  });
  if (!res.ok) await erreurDe(res, "Suppression de l'équipe impossible");
}

// --------------------------------------------------- lot peaufinage B (2026-11-25)
// Identité du club (v2-cadrage §3.4, option A) : couleurs + logo, commun à
// tous les comptes du club actif. Le logo est un PNG ou un SVG statique
// (≤ 500 Ko) validé côté serveur ; `logo` est sa base64, null = suppression.

/** Corps du PUT /api/club/theme. */
export interface CorpsThemeClub {
  couleurs: {
    primary: string; // #RRGGBB obligatoire
    secondary: string | null; // #RRGGBB ou null
    accent: string | null; // #RRGGBB ou null
  };
  logo: string | null; // base64 (PNG ou SVG ≤ 500 Ko), null = sans logo
}

/** Enregistre l'identité du club actif ; renvoie le thème stocké. */
export async function mettreAJourThemeClub(corps: CorpsThemeClub): Promise<ClubTheme> {
  const res = await fetch("/api/club/theme", {
    method: "PUT",
    cache: "no-store",
    headers: JSON_HEADERS,
    body: JSON.stringify(corps),
  });
  if (!res.ok) await erreurDe(res, "Mise à jour de l'identité du club impossible");
  const body = (await res.json()) as { theme: ClubTheme };
  return body.theme;
}
