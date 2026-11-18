// Fiche complète (maquette S3). Les libellés officiels du corpus sont portés
// ici (qualité, origines, états, durée) ; la carte ne porte que les courts.
// Le bloc source est replié par défaut (fermé) — risque #4 de la maquette.

import type { Fiche, FieldEntry } from "../lib/types";
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

function valueText(v: string | number | null): string {
  return v == null ? "" : String(v);
}

interface Props {
  fiche: Fiche | null;
  tagLabels: Record<string, string>;
  error: string | null;
}

export default function FicheDetail({ fiche, tagLabels, error }: Props) {
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
          {f.u8_adaptation && <p>{f.u8_adaptation}</p>}
          {f.u8_proposed_settings && <p>{f.u8_proposed_settings}</p>}
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
          <p className="field-value">{f.observation}</p>
        </section>
      )}

      {/* Consignes coach (si présentes dans le corpus). */}
      {f.coach_cues && (
        <section className="block" aria-label="Consignes coach">
          <h3>Consignes coach</h3>
          <p className="field-value">
            {Array.isArray(f.coach_cues) ? f.coach_cues.join(" ") : f.coach_cues}
          </p>
        </section>
      )}

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
