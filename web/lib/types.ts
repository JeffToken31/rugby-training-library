// Contrats de la vue de lecture v1 (exports/APPLICATION.json) — miroir de
// webapp.py. Les formes proviennent des structures vérifiées le 2026-11-18.

export type QualityState =
  | "DOCUMENTED_CORE"
  | "PROPOSED_OBJECTIVE"
  | "REPORTED_OBSERVATION"
  | "INCOMPLETE";

export type DurationStatus =
  | "PLANNING_PROPOSAL"
  | "EXISTING_DURATION"
  | "KNOWN_ROUND_DURATION"
  | "INSUFFICIENT_DESCRIPTION";

export type FieldState =
  | "PRESENT"
  | "NOT_STATED"
  | "NOT_EXTRACTED"
  | "CONFLICTING"
  | "BLOCKED";

export interface Tag {
  id: string;
  label: string;
  dimension: "skill" | "format";
}

export interface Family {
  id: string;
  title: string;
  origin: string;
}

export interface CanonicalGameGroup {
  id: string;
  members: string[];
  origin: string;
  status: string;
  note: string;
}

export interface VideoCandidate {
  url: string;
  review_status: string | null;
}

export interface LocalCapture {
  archive: string | null;
  available: boolean;
  redistribute_pdf: boolean;
}

export interface Media {
  video: VideoCandidate | null;
  local_capture: LocalCapture | null;
}

export interface Card {
  id: string;
  title: string;
  original_title: string | null;
  summary: string | null;
  state: QualityState;
  default_visible: boolean;
  tag_ids: string[];
  session_uses: string[];
  planning_min_seconds: number | null;
  planning_max_seconds: number | null;
  duration_status: DurationStatus | null;
  media: Media;
}

export interface FieldEntry {
  origin: string | null;
  state: FieldState;
  value: string | number | null;
  provenance: Record<string, unknown> | null;
}

export interface DurationProfile {
  label: string;
  intro_seconds: number;
  round_seconds: number;
  rounds_min: number;
  rounds_max: number;
  between_seconds: number;
  outro_seconds: number;
  extension: string;
}

export interface PlanningDuration {
  variant_id: string;
  origin: string;
  status: DurationStatus;
  basis: string | null;
  profile: DurationProfile | null;
  min_seconds: number | null;
  max_seconds: number | null;
  includes_briefing: boolean;
  includes_group_transition: boolean;
}

export interface SourceEntry {
  access: string | null;
  checked_on: string | null;
  format: string | null;
  id: string;
  language: string | null;
  publisher: string | null;
  qualification_note: string | null;
  resource_type: string | null;
  title: string;
  url: string;
}

export interface PreparationQuestion {
  field: string;
  state: FieldState;
  question: string;
}

export interface WarmupUsage {
  variant_id: string;
  uses: string[];
  usage_origin: string;
  source_id: string | null;
  locator: string | null;
  stage: string | null;
  stage_origin: string | null;
  note: string | null;
}

export interface MissingReview {
  variant_id: string;
  checked_on: string | null;
  basis: string | null;
  conclusion: string | null;
}

export interface QualityDetail {
  state: QualityState;
  missing_core: string[];
  missing_fields: string[];
  core_origins: Record<string, string>;
  coach_validated: boolean;
  u8_suitability: string;
  contact_level: string;
  default_visible: boolean;
}

// Fiche complète : carte + rubriques (route /api/fiches/<id>).
export interface Fiche extends Card {
  theme: string | null;
  fields: Record<string, FieldEntry>;
  documentary_fields: Record<string, FieldEntry>;
  u8_adaptation: string | null;
  u8_proposed_settings: string | Record<string, unknown> | null;
  participants_scope: string | null;
  age_source: string | null;
  source: SourceEntry | null;
  locator: string | null;
  references: Array<Record<string, unknown>> | null;
  observation: string | Record<string, unknown> | null;
  coach_cues: string | string[] | Record<string, unknown> | null;
  source_conflicts: unknown;
  bout_seconds: number | null;
  preparation_questions: PreparationQuestion[];
  planning_duration: PlanningDuration | null;
  tagging: Record<string, unknown> | null;
  missing_review: MissingReview | null;
  duplicate_review: unknown;
  warmup_usage: WarmupUsage | null;
  quality: QualityDetail;
}

export interface Summary {
  records: number;
  families: number;
  readiness: Record<string, number>;
  unique_exercises: number | null;
}

export interface Policy {
  collection: string;
  unknown_values: string;
  automatic_merge: boolean;
  note: string;
}

export interface WarmupCollection {
  version: string;
  records: unknown;
  guidance_source_id: string;
  guidance: string;
  screening_notes: string;
}

export interface CatalogueView {
  schema_version: string | null;
  field_names: Record<string, string> | null;
  families: Family[];
  canonical_game_groups: CanonicalGameGroup[];
  summary: Summary;
  policy: Policy;
  tag_taxonomy: { version: string; policy: unknown; tags: Tag[] };
  warmup_collection: WarmupCollection;
  cards: Card[];
}

// ---------------------------------------------------------------------------
// Lot 3 — brouillon de séance (data/session-draft.example.json, webapp.py).
// Miroir du contrat de session_plan.py.
// ---------------------------------------------------------------------------

export type BlockKind = "OPPOSITION" | "WORKSHOPS" | "JEU" | "WARMUP" | "PAUSE";

export interface SessionGroup {
  id: string;
  players: number;
}

export interface SessionSlot {
  group_id: string;
  station_id: string;
  variant_id: string | null;
}

export interface SessionRound {
  work_min: number;
  transition_min: number;
  assignments: SessionSlot[];
}

export interface SessionBlock {
  kind: BlockKind;
  label: string;
  duration_min: number | null;
  variant_ids: string[];
  rounds?: SessionRound[];
}

// Équipe d'effectif enregistrée au compte (tranché 2026-11-22) : nom seul
// champ obligatoire ; club, catégorie, effectif et coachs facultatifs —
// les tailles varient d'un club à l'autre.
export interface Equipe {
  id: string;
  nom: string;
  club: string | null;
  categorie: string | null;
  effectif: number | null;
  coachs: string[];
  saved_at: string;
}

export interface SessionPlan {
  schema_version?: number;
  id: string;
  title: string;
  status?: string;
  origin?: string;
  duration_min: number | null;
  creneau_min: number;
  players: number;
  coaches?: number;
  // Tranché 2026-11-22 : coachs présents par login (liste « coachs
  // disponibles ») — `coaches` reste le compte affiché et validé.
  coach_logins?: string[];
  // Snapshot de l'équipe d'effectif choisie (D1 : la séance conserve son
  // propre instantané, indépendamment des éditions ultérieures de l'équipe).
  team?: {
    id: string;
    nom: string;
    club: string | null;
    categorie: string | null;
    effectif: number | null;
  } | null;
  groups: SessionGroup[];
  objective?: string | null;
  blocks: SessionBlock[];
  pending_decisions?: string[];
  note?: string | null;
}

export interface MinutageDerivee {
  creneau_min: number;
  planifie_min: number;
  marge_min: number;
  opposition_min: number;
  partiel: boolean;
}

export interface SeanceCheck {
  valide: boolean;
  erreurs: string[];
  avertissements: string[];
  minutage: MinutageDerivee;
}

// Conseils coach (tranché 2026-11-22) : un enregistrement par exercice,
// servi par GET /api/conseils depuis data/coach-cues.json (lu à chaque
// requête — ajouter du contenu ne demande ni code ni redémarrage).
export interface ConseilCoach {
  variant_id: string;
  origin: string;
  reviewed_on?: string | null;
  basis_fields?: string[];
  success_indicator?: string | null;
  coach_observation?: string | null;
}

export interface ConseilsPayload {
  version: number;
  scope: string;
  records: ConseilCoach[];
}
