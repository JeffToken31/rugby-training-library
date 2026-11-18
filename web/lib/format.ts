// Libellés officiels du corpus (application_data, fiche_preparation, timing,
// unified_catalogue) — reproduits à l'identique, sans approximation.

import type { Fiche, PlanningDuration } from "./types";

export const QUALITY_LABELS: Record<string, string> = {
  DOCUMENTED_CORE: "Noyau documentaire présent",
  PROPOSED_OBJECTIVE: "Objectif proposé à confirmer",
  REPORTED_OBSERVATION: "Observation utilisateur",
  INCOMPLETE: "Description insuffisante",
};

// Libellés courts des badges de carte (maquette validée) ; le libellé complet
// officiel est porté par la fiche.
export const BADGE_LABELS: Record<string, string> = {
  INCOMPLETE: "Fiche incomplète",
  PROPOSED_OBJECTIVE: "Objectif proposé",
  REPORTED_OBSERVATION: "Observation rapportée",
};

// fiche_preparation.LABELS — mêmes 12 rubriques, mêmes libellés.
export const FIELD_LABELS: Record<string, string> = {
  objectives: "Objectif",
  organisation: "Organisation",
  steps: "Déroulement",
  instructions: "Consignes",
  success_criteria: "Critères de réussite",
  common_errors: "Erreurs fréquentes",
  coach_points: "Points d'attention",
  duration_min: "Durée de l'atelier",
  players_min: "Effectif minimum",
  players_max: "Effectif maximum",
  space: "Espace",
  material: "Matériel",
};

export const CORE_FIELDS = ["objectives", "organisation", "steps", "instructions"] as const;

// unified_catalogue.ORIGINS.
export const ORIGIN_LABELS: Record<string, string> = {
  SOURCE: "source",
  AI_INFERRED: "proposition IA",
  USER_REPORTED: "observation utilisateur",
  LEGACY_UNREVIEWED: "historique non réexaminé",
};

// unified_catalogue.STATES (hors PRESENT).
export const STATE_LABELS: Record<string, string> = {
  PRESENT: "présent",
  NOT_STATED: "non indiqué dans le passage examiné",
  NOT_EXTRACTED: "non extrait de la source",
  BLOCKED: "accès bloqué",
  CONFLICTING: "contradiction à résoudre",
};

// Équivalent de timing.minutes : f"{seconds/60:g}" → virgule française.
// Les durées de l'app restent bien inférieures à l'heure : pas d'exponentielle.
export function minutes(seconds: number): string {
  return (seconds / 60).toPrecision(6).replace(/\.?0+$/, "").replace(".", ",");
}

// Libellé compact de la carte (maquette). Le libellé complet officiel est
// porté par la fiche (ficheDurationText).
export function cardDurationLabel(
  min: number | null,
  max: number | null,
  status: string | null
): string {
  switch (status) {
    case "PLANNING_PROPOSAL":
      return min != null && max != null ? `≈ ${minutes(min)}–${minutes(max)} min` : "";
    case "EXISTING_DURATION":
      return "durée documentaire";
    case "KNOWN_ROUND_DURATION":
      return "manche documentée";
    default:
      return "durée à définir";
  }
}

// Reproduction à l'identique de timing.description (fiche complète).
export function ficheDurationText(fiche: Fiche): string {
  const t: PlanningDuration | null = fiche.planning_duration;
  if (!t) return "";
  if (t.status === "INSUFFICIENT_DESCRIPTION") {
    return "Durée non estimée : déroulement insuffisamment décrit.";
  }
  if (t.status === "EXISTING_DURATION") {
    const fld = fiche.fields["duration_min"];
    if (!fld || fld.value == null) {
      return "Durée à vérifier dans la source.";
    }
    const label =
      fld.origin === "SOURCE"
        ? "durée documentaire"
        : "durée historique, périmètre à vérifier";
    return `${fld.value} min — ${label}. Temps d’explication et transitions à vérifier ; ce chiffre n’est pas une durée d’effort continu.`;
  }
  if (t.status === "KNOWN_ROUND_DURATION") {
    return `Manche documentée : ${fiche.bout_seconds} secondes. Choisir le nombre de manches, les pauses et les explications pour fixer la durée totale ; ne pas confondre manche et atelier.`;
  }
  return `Budget proposé : ${minutes(t.min_seconds ?? 0)} à ${minutes(t.max_seconds ?? 0)} min, explications et retours inclus, déplacement vers l’atelier suivant exclu. Proposition IA à ajuster par le coach.`;
}

// Libellé du stage de mise en échauffement (warmup_collection).
export const STAGE_LABELS: Record<string, string> = {
  general: "Mise en mouvement",
  mobility: "Mobilité dynamique",
  specific: "Préparation spécifique rugby",
};
