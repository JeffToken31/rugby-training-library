// Feuille de filtres (maquette S2) : compétences (17) / formes de jeu (9) /
// Échauffements / interrupteur « incomplètes » / mode de combinaison all/any.
// « Voir N fiche(s) » toujours visible avant de quitter.
// Chaque tag affiche son compteur : nombre de fiches du catalogue portant ce
// tag (fiches incomplètes comprises) — un tag à (1) n'a pas l'allure d'un
// filtre en panne, c'est la couverture réelle du corpus.

import type { Tag } from "../lib/types";

interface Props {
  tags: Tag[];
  tagCounts: Record<string, number>;
  selectedTags: string[];
  onToggleTag: (id: string) => void;
  warmupOnly: boolean;
  onToggleWarmup: () => void;
  showIncomplete: boolean;
  onToggleIncomplete: () => void;
  match: "all" | "any";
  onMatch: (m: "all" | "any") => void;
  count: number;
  onReset: () => void;
  onApply: () => void;
}

export default function FiltersSheet({
  tags,
  tagCounts,
  selectedTags,
  onToggleTag,
  warmupOnly,
  onToggleWarmup,
  showIncomplete,
  onToggleIncomplete,
  match,
  onMatch,
  count,
  onReset,
  onApply,
}: Props) {
  const skills = tags.filter((t) => t.dimension === "skill");
  const formats = tags.filter((t) => t.dimension === "format");

  const chip = (t: Tag) => (
    <button
      key={t.id}
      className="chip"
      aria-pressed={selectedTags.includes(t.id)}
      onClick={() => onToggleTag(t.id)}
    >
      {t.label} <span className="chip-count">{tagCounts[t.id] ?? 0}</span>
    </button>
  );

  return (
    <>
      <div className="sheet-backdrop" onClick={onApply} />
      <div className="sheet" role="dialog" aria-modal="true" aria-label="Filtres du catalogue">
        <div className="sheet-handle" aria-hidden="true" />
        <h2>Filtres</h2>

        <fieldset>
          <legend>Compétence ({skills.length})</legend>
          <div className="chips">{skills.map(chip)}</div>
        </fieldset>

        <fieldset>
          <legend>Forme de jeu ({formats.length})</legend>
          <div className="chips">{formats.map(chip)}</div>
        </fieldset>

        <button className="switch-row" role="switch" aria-checked={warmupOnly} onClick={onToggleWarmup}>
          <span className="switch-label">Échauffements uniquement</span>
          <span className="switch-track"><span className="switch-thumb" /></span>
        </button>

        <button className="switch-row" role="switch" aria-checked={showIncomplete} onClick={onToggleIncomplete}>
          <span className="switch-label">Afficher les fiches incomplètes</span>
          <span className="switch-track"><span className="switch-thumb" /></span>
        </button>

        <div className="match-row">
          <span>Compétences cochées :</span>
          <div className="match-group" role="group" aria-label="Combinaison des filtres">
            <button className="match-btn" aria-pressed={match === "all"} onClick={() => onMatch("all")}>
              toutes doivent être présentes
            </button>
            <button className="match-btn" aria-pressed={match === "any"} onClick={() => onMatch("any")}>
              au moins une
            </button>
          </div>
        </div>

        <div className="sheet-footer">
          <button className="reset-btn" onClick={onReset}>Réinitialiser</button>
          <button className="apply-btn" onClick={onApply}>
            Voir {count} fiche{count > 1 ? "s" : ""}
          </button>
        </div>
      </div>
    </>
  );
}
