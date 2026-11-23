// Partage de la fiche de séance — PC / Android / iPhone (tranché 2026-11-22).
//
// Chaîne de canaux, du plus riche au plus sobre :
//   1. `navigator.share` avec le fichier PDF (Android, Edge/Chrome desktop
//      à jour, iPhone 16+) — la pièce jointe va directement au groupe.
//   2. `navigator.share` avec le récapitulatif texte seul (iPhone : le
//      partage de fichiers n'est pas toujours pris en charge) — le PDF est
//      téléchargé en complément sur l'appareil pour la pièce jointe.
//   3. Téléchargement du PDF (PC sans API de partage) — à joindre à la main.
// Un lien « WhatsApp avec le récap » est offert en complément, sans compte ni
// configuration : il ouvre une conversation avec le texte déjà encodé.
//
// Aucune donnée personnelle d'enfant : le récap parle de la séance (blocs,
// exercices, durées), pas de joueurs. Aucun lien public : le dépôt n'expose
// pas d'URL de séance — l'EN ATTENTE d'un partage par lien est documenté au
// rapport.

import type { Fiche, SessionPlan } from "./types";
import type { Proposition } from "./auth";

export type PartageMode = "shared" | "text-shared" | "downloaded" | "cancelled";

// --- Téléchargement de secours (PC, ou complément du partage texte). ---

export function download(file: File): void {
  const url = URL.createObjectURL(file);
  const a = document.createElement("a");
  a.href = url;
  a.download = file.name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

// --- Récapitulatif texte d'une proposition (même contenu que la tête du
// PDF : titre, équipe, éducateurs, minutage, blocs et ateliers). ---

function savedLabel(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("fr-FR", { hour12: false });
}

function titreAtelier(id: string, fiches?: Record<string, Fiche>): string {
  return fiches?.[id]?.title ?? id;
}

export function recapTextePlan(p: Proposition, fiches?: Record<string, Fiche>): string {
  const plan: SessionPlan = p.plan;
  const l: string[] = [];
  l.push(`Séance : ${p.titre || plan.title || "Séance"}`);
  if (p.saved_at) l.push(`Préparée le ${savedLabel(p.saved_at)}`);
  const team = plan.team;
  if (team) {
    l.push(
      `Équipe : ${team.nom}` +
        (team.club ? ` (${team.club})` : "") +
        (team.categorie ? ` ${team.categorie}` : "") +
        (team.effectif !== null ? ` — ${team.effectif} joueurs` : "")
    );
  }
  if (plan.coaches) l.push(`Éducateurs : ${plan.coaches}`);
  const m = p.minutage;
  l.push(
    `Créneau ${m.creneau_min} min · planifié ${m.planifie_min} min · ` +
      `marge ${m.marge_min} min · opposition ${m.opposition_min} min`
  );
  for (const b of plan.blocks ?? []) {
    const label = b.label && b.label !== b.kind ? `${b.kind} — ${b.label}` : b.kind;
    let line = `• ${label}` + (b.duration_min != null ? ` (${b.duration_min} min)` : "");
    const ids = new Set<string>();
    for (const id of b.variant_ids ?? []) if (id) ids.add(id);
    for (const r of b.rounds ?? [])
      for (const a of r.assignments ?? []) if (a.variant_id) ids.add(a.variant_id);
    if (ids.size > 0) line += " — " + [...ids].map((id) => titreAtelier(id, fiches)).join(", ");
    l.push(line);
  }
  l.push("— Rugby Training Library");
  return l.join("\n");
}

// Lien WhatsApp sans numéro de destinataire : la conversation se choisit
// dans l'app ; le texte part déjà encodé (pas d'URL de séance : aucune).
export function lienWhatsApp(texte: string): string {
  return "https://wa.me/?text=" + encodeURIComponent(texte);
}

// --- Chaîne de canaux (fichier → texte → téléchargement). ---

export function partagerPieceJointe(file: File, recap: string): Promise<PartageMode> {
  const n = navigator;
  const hasShare = typeof n.share === "function";
  const canFiles =
    hasShare && typeof n.canShare === "function" && n.canShare({ files: [file] });

  if (canFiles) {
    // Fichier + légende : Android et desktop modernes ; la légende part avec
    // la pièce jointe (groupe WhatsApp, e-mail, …).
    return n
      .share({ files: [file], text: recap, title: file.name })
      .then(() => "shared" as const)
      .catch((err: unknown) => {
        if (err && (err as { name?: string }).name === "AbortError")
          return "cancelled" as const;
        // Échec inattendu du partage de fichiers → on retombe sur le texte,
        // puis le téléchargement.
        if (hasShare) {
          return n
            .share({ text: recap })
            .then(() => "text-shared" as const)
            .catch((err2: unknown) => {
              if (err2 && (err2 as { name?: string }).name === "AbortError")
                return "cancelled" as const;
              download(file);
              return "downloaded" as const;
            });
        }
        download(file);
        return "downloaded" as const;
      });
  }
  if (hasShare) {
    // iPhone (et quelques navigateurs) : texte seul. Le PDF est téléchargé
    // en complément pour pouvoir le joindre à la main si besoin.
    return n
      .share({ text: recap })
      .then(() => {
        download(file);
        return "text-shared" as const;
      })
      .catch((err: unknown) => {
        if (err && (err as { name?: string }).name === "AbortError")
          return "cancelled" as const;
        download(file);
        return "downloaded" as const;
      });
  }
  download(file);
  return Promise.resolve("downloaded");
}
