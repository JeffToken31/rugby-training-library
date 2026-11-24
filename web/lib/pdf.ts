// Lot 7 — « fiche de séance terrain » générée en PDF côté client (téléphone
// du coach), puis partagée via la feuille de partage native (navigator.share).
//
// Choix tranchés (cadrage 04, D1=A / D2=A) : génération locale dans le
// navigateur → PDF A4 rasterisé (html2canvas + jsPDF) → vrai File →
// navigator.share. Zéro changement Python, zéro nouvel endpoint : le contenu
// est déjà servi par les API existantes (proposition + fiches).
//
// Le contenu est une VUE du snapshot immuable de la proposition (D1 lot 5) :
// titre, minutage, blocs et, pour chaque atelier référencé, ses rubriques
// documentées. L'état (ex. INCOMPLETE) et la provenance restent lisibles —
// le PDF affiche, il n'autorise rien.
//
// Aucune donnée personnelle d'enfant : une séance parle d'exercices et de
// durées, pas de noms de joueurs.

import type { ConseilCoach, Fiche, FieldEntry, SessionPlan } from "./types";
import type { Moi, Proposition } from "./auth";
import { BADGE_LABELS, CORE_FIELDS, FIELD_LABELS } from "./format";
import { KIND_LABELS } from "./session";

// ---------------------------------------------------------------------------
// Aplat d'une valeur de rubrique (miroir de valueText dans FicheDetail) : une
// valeur est string | number | null ; un tableau/objet devient du texte lisible
// sans perte. Le PDF ne porte que du texte.
// ---------------------------------------------------------------------------
function flat(v: unknown): string {
  if (v == null) return "";
  if (typeof v === "string") return v;
  if (typeof v === "number") return String(v);
  if (Array.isArray(v)) return v.map((x) => flat(x)).filter(Boolean).join(" ; ");
  if (typeof v === "object") {
    return Object.entries(v as Record<string, unknown>)
      .map(([k, x]) => `${k} : ${flat(x)}`)
      .filter((s) => s.length > 3)
      .join(" ; ");
  }
  return String(v);
}

// Les ids d'exercice référencés par un plan (variant_ids des blocs + affectations
// des rotations), sans doublon, en ordre d'apparition.
export function atelierIdsDuPlan(plan: SessionPlan): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  const add = (id: string | null | undefined) => {
    if (id && !seen.has(id)) {
      seen.add(id);
      out.push(id);
    }
  };
  for (const b of plan.blocks ?? []) {
    for (const id of b.variant_ids ?? []) add(id);
    for (const r of b.rounds ?? []) for (const a of r.assignments ?? []) add(a.variant_id);
  }
  return out;
}

// Rubriques d'une fiche, en texte : les 4 rubriques cœur d'abord (Objectif,
// Organisation, Déroulement, Consignes), puis le reste des rubriques présentes
// (en compact), dans l'ordre du corpus.
function ficheRows(f: Fiche): { label: string; value: string; core: boolean }[] {
  const present = (e: FieldEntry | undefined): e is FieldEntry =>
    !!e && e.state === "PRESENT" && e.value != null;
  const rows: { label: string; value: string; core: boolean }[] = [];
  for (const k of CORE_FIELDS) {
    const e = f.fields[k];
    if (present(e)) rows.push({ label: FIELD_LABELS[k], value: flat(e.value), core: true });
  }
  const core = new Set<string>(CORE_FIELDS as unknown as string[]);
  for (const [k, e] of Object.entries(f.fields)) {
    if (core.has(k)) continue;
    if (present(e)) rows.push({ label: FIELD_LABELS[k] ?? k, value: flat(e.value), core: false });
  }
  return rows;
}

// --- Construction du DOM de la feuille (couleurs explicites en clair : le PDF
// doit rester lisible et clair quelle que soit la thème de l'app sur le
// téléphone ; les classes .pdf-* sont définies dans globals.css). ---

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className: string | null,
  text: string | null
): HTMLElement {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function buildSheet(
  p: Proposition,
  moi: Moi,
  fiches: Record<string, Fiche>,
  conseils: ConseilCoach[] = []
): HTMLElement {
  const sheet = el("div", "pdf-sheet", null);

  // En-tête : titre, coach (login + club + catégorie), date du snapshot.
  const titre = p.titre || p.plan.title || "Séance";
  sheet.appendChild(el("h1", "pdf-title", titre));
  const meta = el("div", "pdf-meta", null);
  const coach =
    `Coach : ${moi.login}` +
    (moi.club ? ` · ${moi.club}` : "") +
    (moi.categorie ? ` · ${moi.categorie}` : "");
  meta.appendChild(el("span", null, coach));
  // Équipe d'effectif (snapshot de la séance, tranché 2026-11-22) : le nom
  // et les éléments connus (club, catégorie, effectif) — jamais les noms de
  // joueurs.
  const team = p.plan.team;
  if (team) {
    meta.appendChild(
      el(
        "span",
        null,
        `Équipe : ${team.nom}` +
          (team.club ? ` · ${team.club}` : "") +
          (team.categorie ? ` · ${team.categorie}` : "") +
          (team.effectif !== null ? ` · ${team.effectif} joueurs` : "")
      )
    );
  }
  if (p.plan.coaches)
    meta.appendChild(el("span", null, `Éducateurs : ${p.plan.coaches}`));
  if (p.saved_at) meta.appendChild(el("span", null, savedLabel(p.saved_at)));
  sheet.appendChild(meta);

  // Minutage (créneau / planifié / marge / opposition).
  const m = p.minutage;
  const min = el("div", "pdf-minut", null);
  const cell = (label: string, value: number | null) => {
    const d = el("div", null, null);
    d.appendChild(el("b", null, value != null ? String(value) : "—"));
    d.appendChild(el("span", null, label));
    min.appendChild(d);
  };
  cell("créneau", m.creneau_min);
  cell("planifié", m.planifie_min);
  cell("marge", m.marge_min);
  cell("opposition", m.opposition_min);
  sheet.appendChild(min);

  // Blocs à la suite.
  const blocksWrap = el("div", "pdf-blocks", null);
  const plan = p.plan;
  for (const b of plan.blocks ?? []) {
    const block = el("section", "pdf-block", null);
    const kind = (KIND_LABELS as Record<string, string>)[b.kind] ?? b.kind;
    let head = kind + (b.label && b.label !== kind ? ` — ${b.label}` : "");
    if (b.duration_min != null) head += ` · ${b.duration_min} min`;
    block.appendChild(el("h3", "pdf-block-head", head));

    // Rotations (travail / transition) si présentes.
    if (b.rounds && b.rounds.length > 0) {
      const rot = el("p", "pdf-rotations", null);
      const parts = b.rounds.map(
        (r, i) =>
          `Rotation ${i + 1} : ${r.work_min ?? "?"} min de travail` +
          (r.transition_min ? ` + ${r.transition_min} min de transition` : "")
      );
      rot.textContent = parts.join("  ·  ");
      block.appendChild(rot);
    }

    // Ateliers référencés dans ce bloc (fiches chargées via l'API).
    const ids = new Set<string>();
    for (const id of b.variant_ids ?? []) if (id) ids.add(id);
    for (const r of b.rounds ?? []) for (const a of r.assignments ?? [])
      if (a.variant_id) ids.add(a.variant_id);
    for (const id of ids)
      block.appendChild(
        buildAtelier(id, fiches[id], conseils.filter((c) => c.variant_id === id))
      );

    blocksWrap.appendChild(block);
  }
  sheet.appendChild(blocksWrap);

  // Pied de page : provenance / statut du snapshot.
  const foot = el("div", "pdf-foot", null);
  foot.textContent =
    `Proposition n°${p.id} — ${p.valide ? "validée" : "non validée"}` +
    ` · fiche générée depuis Rugby Training Library (vue du snapshot immuable).`;
  sheet.appendChild(foot);

  return sheet;
}

function buildAtelier(
  id: string,
  fiche: Fiche | undefined,
  conseils: ConseilCoach[] = []
): HTMLElement {
  if (!fiche) {
    const wrap = el("div", "pdf-atelier", null);
    wrap.appendChild(el("h4", "pdf-atelier-title", id));
    wrap.appendChild(el("p", "pdf-atelier-missing", "Fiche non trouvée dans le catalogue."));
    return wrap;
  }
  const wrap = el("div", "pdf-atelier", null);
  const title = el("h4", "pdf-atelier-title", fiche.title);
  if (fiche.state === "INCOMPLETE") {
    title.appendChild(el("span", "pdf-atelier-incomplete", BADGE_LABELS.INCOMPLETE));
  }
  wrap.appendChild(title);

  const rows = ficheRows(fiche);
  for (const r of rows.filter((x) => x.core)) {
    const field = el("div", "pdf-field", null);
    field.appendChild(el("h5", null, r.label));
    field.appendChild(el("p", null, r.value));
    wrap.appendChild(field);
  }
  const others = rows.filter((x) => !x.core);
  if (others.length > 0) {
    const dl = el("div", "pdf-details", null);
    for (const r of others) {
      const line = el("div", null, null);
      const b = el("b", null, r.label + " : ");
      line.appendChild(b);
      line.appendChild(document.createTextNode(r.value));
      dl.appendChild(line);
    }
    wrap.appendChild(dl);
  }

  // Conseils coach (data/coach-cues.json via GET /api/conseils) : l'origine
  // reste lisible sur le papier, comme dans l'app.
  for (const c of conseils) {
    if (!c.success_indicator && !c.coach_observation) continue;
    const origine =
      c.origin === "AI_INFERRED"
        ? "proposition IA"
        : c.origin === "USER_REPORTED"
          ? "observation utilisateur"
          : c.origin;
    const cue = el("div", "pdf-cue", null);
    cue.appendChild(el("h5", null, `Conseil coach — ${origine}`));
    if (c.success_indicator)
      cue.appendChild(el("p", null, `Indice de réussite : ${c.success_indicator}`));
    if (c.coach_observation)
      cue.appendChild(el("p", null, `À observer : ${c.coach_observation}`));
    wrap.appendChild(cue);
  }
  return wrap;
}

// Horodatage lisible (ISO → « 19/11/2026, 14:03 ») — même format que l'app.
function savedLabel(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("fr-FR", { hour12: false });
}

// Nom de fichier lisible (slug du titre), pour la pièce jointe WhatsApp.
function filenameFrom(titre: string): string {
  const slug = (titre || "seance")
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase()
    .slice(0, 60) || "seance";
  return `${slug}.pdf`;
}

// --- Génération : on rend le DOM hors écran, on le capture, on le découpe en
// pages A4, on produit un vrai File. ---

// Aperçu (v1.1 L1) : les pages de la fiche, en images, exactement telles
// qu'elles seront partagées — même DOM (buildSheet), même capture
// (html2canvas, scale 2), même découpage (sliceA4) que generateSessionPdf.
// L'aperçu est la pièce elle-même : rien n'est ajouté ni retiré pour l'écran.
export async function renderSheetPages(
  p: Proposition,
  moi: Moi,
  fiches: Record<string, Fiche>,
  conseils: ConseilCoach[] = []
): Promise<{ pages: { data: string; hPx: number }[]; pageH: number }> {
  // Import dynamique : la lib (lourde) ne se charge qu'ici, jamais côté
  // serveur (composant client).
  const h2c = await import("html2canvas");
  const html2canvas = h2c.default;

  const holder = document.createElement("div");
  holder.className = "pdf-holder";
  const sheet = buildSheet(p, moi, fiches, conseils);
  holder.appendChild(sheet);
  document.body.appendChild(holder);
  try {
    // Un frame pour laisser le navigateur disposer le contenu hors écran.
    await new Promise((r) => requestAnimationFrame(() => r(null)));
    const canvas = await html2canvas(sheet, {
      scale: 2,
      backgroundColor: "#ffffff",
      logging: false,
    });
    return {
      pages: sliceA4(canvas),
      pageH: Math.round((canvas.width * 297) / 210),
    };
  } finally {
    holder.remove();
  }
}

// Découpe d'un canvas (ratio A4) en tranches de la hauteur d'une page A4.
function sliceA4(canvas: HTMLCanvasElement): { data: string; hPx: number }[] {
  const pageH = Math.round((canvas.width * 297) / 210); // px de hauteur d'une page A4
  const pages: { data: string; hPx: number }[] = [];
  let y = 0;
  while (y < canvas.height) {
    const h = Math.min(pageH, canvas.height - y);
    const slice = document.createElement("canvas");
    slice.width = canvas.width;
    slice.height = h;
    const ctx = slice.getContext("2d");
    if (!ctx) break;
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, slice.width, slice.height);
    ctx.drawImage(canvas, 0, y, canvas.width, h, 0, 0, canvas.width, h);
    pages.push({ data: slice.toDataURL("image/jpeg", 0.92), hPx: h });
    y += h;
  }
  return pages;
}

export async function generateSessionPdf(
  p: Proposition,
  moi: Moi,
  fiches: Record<string, Fiche>,
  conseils: ConseilCoach[] = []
): Promise<File> {
  // Import dynamique : la lib (lourde) ne se charge qu'au moment du
  // partage, et jamais côté serveur (composant client).
  const { jsPDF } = await import("jspdf");
  // Une seule voie de rasterisation : aperçu et pièce partagée sont le
  // même rendu (v1.1 L1).
  const { pages, pageH } = await renderSheetPages(p, moi, fiches, conseils);
  const pdf = new jsPDF({ unit: "mm", format: "a4", orientation: "portrait" });
  pages.forEach((pg, i) => {
    const hMm = (pg.hPx / pageH) * 297;
    if (i > 0) pdf.addPage();
    pdf.addImage(pg.data, "JPEG", 0, 0, 210, hMm);
  });
  const blob = pdf.output("blob");
  return new File([blob], filenameFrom(p.titre || p.plan.title), {
    type: "application/pdf",
  });
}

// Le partage lui-même (fichier → texte → téléchargement + lien WhatsApp)
// vit dans ./share — ce module ne produit que le PDF.
