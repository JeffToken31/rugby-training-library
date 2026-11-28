// Carte de liste (maquette S1) : état → titre → résumé 2 lignes → tags
// (max 4 + « +n ») → métadonnées. Badges courts ; libellés complets en fiche.

import type { Card } from "../lib/types";
import { BADGE_LABELS, cardDurationLabel } from "../lib/format";

export interface CardTagLabels {
  [id: string]: string;
}

const BADGE_CLASS: Record<string, string> = {
  INCOMPLETE: "badge-red",
  PROPOSED_OBJECTIVE: "badge-amber",
  REPORTED_OBSERVATION: "badge-slate",
};

interface Props {
  card: Card;
  tagLabels: CardTagLabels;
  onOpen: (id: string) => void;
}

export default function CatalogCard({ card, tagLabels, onOpen }: Props) {
  const badge = BADGE_LABELS[card.state];
  const tags = card.tag_ids;
  const shown = tags.slice(0, 4);
  const extra = tags.length - shown.length;
  const dur = cardDurationLabel(
    card.planning_min_seconds,
    card.planning_max_seconds,
    card.duration_status
  );

  return (
    <button className="card" onClick={() => onOpen(card.id)} aria-label={`Ouvrir la fiche ${card.title}`}>
      <span className="card-badges">
        {card.session_uses.includes("WARMUP") && (
          <span className="badge badge-green">Échauffement</span>
        )}
        {badge && <span className={`badge ${BADGE_CLASS[card.state]}`}>{badge}</span>}
      </span>
      <span className="card-title">{card.title}</span>
      {card.summary && <span className="card-summary">{card.summary}</span>}
      {tags.length > 0 && (
        <span className="card-tags">
          {shown.map((id) => (
            <span className="tag" key={id}>{tagLabels[id] ?? id}</span>
          ))}
          {extra > 0 && <span className="tag">+{extra}</span>}
        </span>
      )}
      <span className="card-meta">
        {dur && <span>{dur}</span>}
        {dur && card.media.video && <span className="meta-dot">vidéo</span>}
        {card.media.local_capture?.available && <span className="meta-dot">capture locale</span>}
      </span>
    </button>
  );
}
