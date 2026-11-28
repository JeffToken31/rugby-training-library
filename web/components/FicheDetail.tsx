// Fiche complète (maquette S3). Les libellés officiels du corpus sont portés
// ici (qualité, origines, états, durée) ; la carte ne porte que les courts.
// Le bloc source est replié par défaut (fermé) — risque #4 de la maquette.

import { useEffect, useState } from "react";

import type { ConseilCoach, Fiche, FieldEntry } from "../lib/types";
import { fetchConseils } from "../lib/api";
import {
  BADGE_LABELS,
  CORE_FIELDS,
  FIELD_LABELS,
  ORIGIN_LABELS,
  STATE_LABELS,
  STAGE_LABELS,
  ficheDurationText,
} from "../lib/format";

const BADGE_CLASS: Record<string, string> = {
  INCOMPLETE: "badge-red",
  PROPOSED_OBJECTIVE: "badge-amber",
  REPORTED_OBSERVATION: "badge-slate",
};

// Libellé lisible d'une clé snake_case du corpus : « duration_min » → « Duration min ».
function humanizeKey(k: string): string {
  const s = k.replace(/_/g, " ").trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// Aplatissement total et perte-zéro d'une valeur du corpus : string/number → tel
// quel ; tableau → éléments joints par « ; » ; objet → paires « clé : valeur ».
// Garantit l'absence de « Objects are not valid as a React child » même si le
// corpus stocke une valeur structurée là où une chaîne était attendue.
function valueText(v: unknown): string {
  if (v == null) return "";
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  if (Array.isArray(v)) {
    return v.map(valueText).filter(Boolean).join(" ; ");
  }
  if (typeof v === "object") {
    return Object.entries(v as Record<string, unknown>)
      .map(([k, val]) => {
        const s = valueText(val);
        return s ? `${humanizeKey(k)} : ${s}` : "";
      })
      .filter(Boolean)
      .join(" ; ");
  }
  return String(v);
}

// Rendu structuré d'une valeur riche du corpus (objet / tableau) : liste lisible
// et champs libellés, en préservant la provenance (origine, bases, incertitudes).
// Pour les scalaires, renvoie la valeur en texte.
function ValueText({ value }: { value: unknown }) {
  if (value == null || value === "") return null;
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return <>{String(value)}</>;
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return null;
    return (
      <ul className="value-list">
        {value.map((item, i) => (
          <li key={i}>
            <ValueText value={item} />
          </li>
        ))}
      </ul>
    );
  }
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>).filter(
      ([, v]) => v != null && v !== "" && !(Array.isArray(v) && v.length === 0)
    );
    if (entries.length === 0) return null;
    return (
      <dl className="value-entries">
        {entries.map(([k, v]) => (
          <div className="value-entry" key={k}>
            <dt>{humanizeKey(k)}</dt>
            <dd>
              <ValueText value={v} />
            </dd>
          </div>
        ))}
      </dl>
    );
  }
  return <>{String(value)}</>;
}

// reviewed_on (date ISO) → « 16/09/2026 » ; date illisible → telle quelle.
function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("fr-FR");
}

// Un conseil coach (data/coach-cues.json) : libellé d'origine officiel
// (proposition IA / observation utilisateur), date de relecture et base —
// la provenance reste lisible, comme sur le reste de la fiche.
function ConseilCoachCard({ c }: { c: ConseilCoach }) {
  const bases = (c.basis_fields ?? [])
    .map((bf) => FIELD_LABELS[bf.split(".").pop() ?? ""] ?? bf)
    .filter(Boolean);
  const aAffichage =
    Boolean(c.success_indicator) || Boolean(c.coach_observation);
  if (!aAffichage) return null;
  return (
    <div className="conseil">
      <p className="conseil-origin">
        <span className="origin-tag">{ORIGIN_LABELS[c.origin] ?? c.origin}</span>
        {c.reviewed_on && (
          <span className="note"> · relecture le {fmtDate(c.reviewed_on)}</span>
        )}
        {bases.length > 0 && <span className="note"> · d’après {bases.join(", ")}</span>}
      </p>
      {c.success_indicator && (
        <div className="field-value">
          <p>
            <strong>Indice de réussite :</strong> {c.success_indicator}
          </p>
        </div>
      )}
      {c.coach_observation && (
        <div className="field-value">
          <p>
            <strong>Ce que le coach peut regarder :</strong> {c.coach_observation}
          </p>
        </div>
      )}
    </div>
  );
}

interface Props {
  fiche: Fiche | null;
  tagLabels: Record<string, string>;
  error: string | null;
}

export default function FicheDetail({ fiche, tagLabels, error }: Props) {
  // Conseils coach : servis par GET /api/conseils (data/coach-cues.json, lu à
  // chaque requête côté serveur) — la section s'alimente en direct ; le
  // catalogue de fiches n'est pas modifié pour ça (provenance).
  const [conseils, setConseils] = useState<ConseilCoach[]>([]);
  useEffect(() => {
    let actif = true;
    fetchConseils()
      .then((d) => {
        if (actif) setConseils(d.records);
      })
      .catch(() => {
        // Endpoint momentanément indisponible : la section reste vide,
        // jamais bloquante.
      });
    return () => {
      actif = false;
    };
  }, []);

  if (error) {
    return <div className="fiche-error" role="alert">{error}</div>;
  }
  if (!fiche) {
    return (
      <div className="skeleton skeleton-card" aria-label="Chargement de la fiche" />
    );
  }

  const f = fiche;
  const core = CORE_FIELDS.map((k) => ({ key: k, entry: f.fields[k] })).filter(
    (x) => x.entry && x.entry.state === "PRESENT" && x.entry.value != null
  );
  const others = Object.entries(f.fields)
    .filter(([k, entry]) => !CORE_FIELDS.includes(k as (typeof CORE_FIELDS)[number]))
    .map(([k, entry]) => ({ key: k, entry }))
    .filter((x) => x.entry);
  const presentOthers = others.filter((x) => x.entry.state === "PRESENT" && x.entry.value != null);
  const unknown = others.filter((x) => !(x.entry.state === "PRESENT" && x.entry.value != null));

  const profile = f.planning_duration?.profile ?? null;

  return (
    <div className="fiche">
      <div className="card-badges" style={{ marginBottom: 0 }}>
        {f.session_uses.includes("WARMUP") && (
          <span className="badge badge-green">Échauffement</span>
        )}
        {BADGE_LABELS[f.state] && (
          <span className={`badge ${BADGE_CLASS[f.state]}`}>{BADGE_LABELS[f.state]}</span>
        )}
      </div>

      <h2 className="fiche-title">{f.title}</h2>
      {f.original_title && f.original_title !== f.title && (
        <p className="original-title">{f.original_title}</p>
      )}
      {f.summary && <p className="fiche-summary">{f.summary}</p>}
      {f.tag_ids.length > 0 && (
        <div className="card-tags">
          {f.tag_ids.map((id) => (
            <span className="tag" key={id}>{tagLabels[id] ?? id}</span>
          ))}
        </div>
      )}

      {/* Durée pour planifier l'atelier — libellé complet officiel. */}
      <section className="block" aria-label="Durée pour planifier l'atelier">
        <h3>Durée pour planifier l’atelier</h3>
        <p>{ficheDurationText(f)}</p>
        {profile && (
          <>
            <ul className="profile">
              <li>Explication et démonstration : {profile.intro_seconds} s.</li>
              <li>
                {profile.rounds_min} à {profile.rounds_max} séquences de{" "}
                {profile.round_seconds} s, avec {profile.between_seconds} s entre deux
                séquences pour récupérer, permuter ou corriger.
              </li>
              <li>Retour final : {profile.outro_seconds} s.</li>
            </ul>
            <p className="extend"><strong>Pour prolonger :</strong> {profile.extension}</p>
            <p className="note">
              Les séquences incluent les passages et l’attente éventuelle ; adapter à
              l’effectif, aux réactions des enfants et au dispositif. Ce n’est pas une
              durée d’effort continu imposée.
            </p>
          </>
        )}
      </section>

      {/* Les 4 rubriques cœur, avec origine. */}
      {core.map(({ key, entry }) => (
        <section className="block" key={key} aria-label={FIELD_LABELS[key]}>
          <h3>
            {FIELD_LABELS[key]}
            {entry.origin && <span className="origin-tag">{ORIGIN_LABELS[entry.origin] ?? entry.origin}</span>}
          </h3>
          <p className="field-value">{valueText(entry.value)}</p>
        </section>
      ))}

      {/* Les 8 autres rubriques présentes, en compact. */}
      {presentOthers.length > 0 && (
        <section className="block" aria-label="Autres rubriques documentées">
          <h3>Détails documentés</h3>
          <div className="compact-grid">
            {presentOthers.map(({ key, entry }) => (
              <div className="compact-cell" key={key}>
                <dt>{FIELD_LABELS[key] ?? key}</dt>
                <dd>{valueText(entry.value)}</dd>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Cadrage U8 et périmètre. */}
      {(f.u8_adaptation || f.u8_proposed_settings || f.participants_scope || f.age_source) && (
        <section className="block" aria-label="Cadrage U8">
          <h3>Cadrage U8 et périmètre</h3>
          {f.u8_adaptation && (
            <div className="field-value">
              <ValueText value={f.u8_adaptation} />
            </div>
          )}
          {f.u8_proposed_settings && (
            <div className="field-value">
              <ValueText value={f.u8_proposed_settings} />
            </div>
          )}
          {f.participants_scope && (
            <p className="note">Périmètre des participants : {f.participants_scope}</p>
          )}
          {f.age_source && <p className="note">Tranche d’âge : {f.age_source}</p>}
        </section>
      )}

      {/* Échauffement — stage officiel. */}
      {f.warmup_usage && (
        <section className="block" aria-label="Échauffement">
          <h3>Échauffement</h3>
          {f.warmup_usage.stage && (
            <p>
              <strong>{STAGE_LABELS[f.warmup_usage.stage] ?? f.warmup_usage.stage}</strong>
            </p>
          )}
          {f.warmup_usage.note && <p className="note">{f.warmup_usage.note}</p>}
        </section>
      )}

      {/* Médias — rattachement officiel (m8_candidates), jamais les liens bruts. */}
      <section className="block" aria-label="Médias">
        <h3>Médias</h3>
        {f.media.video ? (
          <div className="media-video">
            <p>
              <strong>Lien extrait du PDF fourni :</strong>{" "}
              <a href={f.media.video.url} target="_blank" rel="noopener noreferrer">
                vidéo candidate
              </a>
              . Association issue des annotations, visionnage non validé.
            </p>
            {f.media.video.review_status === "NOT_VIEWED" && (
              <p className="note">Statut du corpus : non visionnée.</p>
            )}
          </div>
        ) : null}
        {f.media.local_capture ? (
          <p className={f.media.local_capture.available ? "capture-ok" : "capture-no"}>
            {f.media.local_capture.available
              ? "Capture locale disponible"
              : "Capture locale non présente sur cette machine"}
            {f.media.local_capture.archive && (
              <span className="note"> — {f.media.local_capture.archive}</span>
            )}
          </p>
        ) : null}
        {!f.media.video && !f.media.local_capture && (
          <p className="no-media">Aucun média ; la fiche reste utilisable si sa description suffit.</p>
        )}
      </section>

      {/* Informations non documentées — pointillé distinctif. */}
      {unknown.length > 0 && (
        <section className="block unknown" aria-label="Informations non documentées">
          <h3>Informations non documentées</h3>
          <ul>
            {unknown.map(({ key, entry }) => (
              <li key={key}>
                <strong>{FIELD_LABELS[key] ?? key}</strong> —{" "}
                <em>{STATE_LABELS[entry.state] ?? entry.state}</em>
              </li>
            ))}
          </ul>
          <p className="note">L’éducateur tranche pour sa séance.</p>
        </section>
      )}

      {/* À décider pour la séance. */}
      {f.preparation_questions.length > 0 && (
        <section className="block" aria-label="À décider pour la séance">
          <h3>À décider pour la séance</h3>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {f.preparation_questions.map((q, i) => (
              <li key={i}>{q.question}</li>
            ))}
          </ul>
        </section>
      )}

      {/* Observation utilisateur. */}
      {f.observation && (
        <section className="block" aria-label="Observation utilisateur">
          <h3>
            Observation utilisateur <span className="origin-tag">observation utilisateur</span>
          </h3>
          <div className="field-value">
            <ValueText value={f.observation} />
          </div>
        </section>
      )}

      {/* Conseils coach (tranché 2026-11-22) : servis en direct par
          GET /api/conseils (data/coach-cues.json, lu à chaque requête) —
          ajouter un conseil ne demande ni code ni redémarrage. La rubrique
          f.coach_cues du corpus n'est plus lue ici : le catalogue n'est pas
          modifié pour l'affichage (provenance). */}
      <section className="block" aria-label="Conseils coach">
        <h3>Conseils coach</h3>
        {conseils.filter((c) => c.variant_id === f.id).map((c) => (
          <ConseilCoachCard key={c.variant_id} c={c} />
        ))}
        {conseils.every((c) => c.variant_id !== f.id) && (
          <p className="conseil-vide">
            Aucun conseil pour l’instant — l’éducateur peut ajouter les siens.
          </p>
        )}
      </section>

      {/* Relecture des lacunes (fiches incomplètes). */}
      {f.missing_review?.conclusion && (
        <section className="block unknown" aria-label="Relecture des lacunes">
          <h3>Relecture des lacunes</h3>
          <p className="field-value">{f.missing_review.conclusion}</p>
        </section>
      )}

      {/* Source et provenance — replié par défaut. */}
      <details className="source-block">
        <summary>Source et provenance</summary>
        <div className="block" style={{ marginTop: 8 }}>
          {f.source && (
            <p>
              <strong>Source principale :</strong>{" "}
              <a href={f.source.url} target="_blank" rel="noopener noreferrer">
                {f.source.title}
              </a>
              {f.source.publisher && <> — {f.source.publisher}</>}
              {f.locator && <> ; {f.locator}</>}
              {f.source.checked_on && <>. Vérification documentaire : {f.source.checked_on}.</>}
            </p>
          )}
          {f.references && f.references.length > 0 && (
            <ul style={{ margin: "8px 0 0", paddingLeft: 20 }}>
              {f.references.map((r, i) => (
                <li key={i}>
                  {String((r.title as string) ?? "Référence")}
                  {Boolean(r.url) && (
                    <> — <a href={String(r.url)} target="_blank" rel="noopener noreferrer">lien</a></>
                  )}
                </li>
              ))}
            </ul>
          )}
          <details className="source-sub">
            <summary>Provenance par rubrique</summary>
            <ul style={{ margin: "8px 0 0", paddingLeft: 20 }}>
              {Object.entries(f.fields)
                .filter(([, entry]) => (entry as FieldEntry).provenance)
                .map(([key, entry]) => {
                  const p = (entry as FieldEntry).provenance as Record<string, unknown>;
                  return (
                    <li key={key}>
                      {FIELD_LABELS[key] ?? key} — {String(p.source_id ?? "")}
                      {Boolean(p.locator) && <> ; {String(p.locator)}</>}
                      {Boolean(p.checked_on) && <> ; vérifiée le {String(p.checked_on)}</>}
                    </li>
                  );
                })}
            </ul>
          </details>
        </div>
      </details>
    </div>
  );
}
