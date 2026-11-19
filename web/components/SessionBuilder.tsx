// Lot 3 — constructeur de séance (vue S6). La trame U8 70/90 est servie
// telle quelle comme gabarit de départ (POST /api/seances/valider en
// référence). Édition par blocs : titre, créneau, effectifs par groupe,
// durée, rotations des ateliers (travail / transition), exercices.
// La minutage (créneau, planifié, marge, opposition) est recalculée à
// chaque frappe — miroir exact du serveur (web/lib/session.ts) — et le
// bouton « Vérifier (serveur) » reste la référence.
// Le picker n'attribue que : un slot qui porte un exercice le conserve
// jusqu'à ce qu'on le remplace (jamais de variant_id null → pas
// d'« Exercice inconnu : None » côté serveur).
// Lot 4 : le brouillon est sauvegardé à chaud dans localStorage (un seul par
// navigateur), proposé à la réouverture dans un bandeau (reprendre / repartir
// de la trame U8) — jamais de perte silencieuse. L'export/import est du JSON
// brut, même contrat que le validateur. Aucun write serveur.

import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import type {
  Card,
  CatalogueView,
  SeanceCheck,
  SessionBlock,
  SessionPlan,
} from "../lib/types";
import { fetchTrameU8, validerSeance } from "../lib/api";
import { clearDraft, loadDraft, parseImport, saveDraft } from "../lib/draft";
import type { SavedDraft } from "../lib/draft";
import { selectCards } from "../lib/filter";
import { BADGE_LABELS, cardDurationLabel } from "../lib/format";
import { etatParIdDe, KIND_LABELS, validerLocale } from "../lib/session";

type PickerTarget =
  | { kind: "slot"; blockIndex: number; roundIndex: number; slotIndex: number }
  | { kind: "block"; blockIndex: number };

const BADGE_CLASS: Record<string, string> = {
  INCOMPLETE: "badge-red",
  PROPOSED_OBJECTIVE: "badge-amber",
  REPORTED_OBSERVATION: "badge-slate",
};

function clonePlan(plan: SessionPlan): SessionPlan {
  return structuredClone(plan);
}

// Horodatage lisible d'une sauvegarde (ISO → « 19/11/2026, 14:03 »).
function savedLabel(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("fr-FR", { hour12: false });
}

export default function SessionBuilder({ view }: { view: CatalogueView | null }) {
  const [plan, setPlan] = useState<SessionPlan | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [picker, setPicker] = useState<PickerTarget | null>(null);
  const [pickerQuery, setPickerQuery] = useState("");
  const [serverCheck, setServerCheck] = useState<SeanceCheck | null>(null);
  const [serverTime, setServerTime] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  // Lot 4 — persistance client (localStorage) : la trame de départ est
  // conservée pour pouvoir y repartir ; un brouillon existant est proposé
  // dans un bandeau avant de continuer (jamais de perte silencieuse).
  const [initialDraft, setInitialDraft] = useState<SessionPlan | null>(null);
  const [pendingDraft, setPendingDraft] = useState<SavedDraft | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let live = true;
    fetchTrameU8()
      .then((p) => {
        if (!live) return;
        setInitialDraft(clonePlan(p));
        setPlan(p);
        const d = loadDraft();
        if (d) setPendingDraft(d);
      })
      .catch((e: Error) => live && setLoadError(e.message));
    return () => {
      live = false;
    };
  }, []);

  const cards: Card[] = view?.cards ?? [];
  const etatParId = useMemo(() => etatParIdDe(cards), [cards]);
  const cardById = useMemo(() => {
    const m: Record<string, Card> = {};
    for (const c of cards) m[c.id] = c;
    return m;
  }, [cards]);

  // Miroir local, recalculé à chaque changement de plan (même ordre de
  // messages que le serveur) — c'est le feedback immédiat de l'édition.
  const localCheck = useMemo(
    () => (plan ? validerLocale(plan, etatParId) : null),
    [plan, etatParId]
  );

  const min = useMemo(() => (plan ? localCheck!.minutage : null), [plan, localCheck]);

  // Mutation du plan : copie profonde, application, resynchronisation de la
  // durée totale (somme des blocs) pour rester cohérent avec le validateur.
  // Le brouillon est sauvegardé à chaud (localStorage) après chaque mutation.
  const updatePlan = (fn: (draft: SessionPlan) => void) => {
    if (!plan) return;
    const draft = clonePlan(plan);
    fn(draft);
    draft.duration_min = (draft.blocks ?? []).reduce<number>(
      (acc, b) => (typeof b.duration_min === "number" ? acc + b.duration_min : acc),
      0
    );
    setPlan(draft);
    const t = saveDraft(draft);
    if (t) setSavedAt(t);
    setServerCheck(null);
    setServerTime(null);
  };

  const firstUsableExercise = (): string | null => {
    const c = cards.find((x) => x.state !== "INCOMPLETE");
    return c ? c.id : null;
  };

  const addBlock = (kind: SessionPlan["blocks"][number]["kind"]) => {
    updatePlan((draft) => {
      const block: SessionBlock = {
        kind,
        label: KIND_LABELS[kind] ?? kind,
        duration_min: 10,
        variant_ids: [],
      };
      if (kind === "WORKSHOPS") {
        const ex = firstUsableExercise();
        block.rounds = [
          {
            work_min: 10,
            transition_min: 0,
            assignments: (draft.groups ?? []).map((g, i) => ({
              group_id: g.id,
              station_id: `station-${i + 1}`,
              variant_id: ex,
            })),
          },
        ];
      }
      draft.blocks.push(block);
    });
  };

  const removeBlock = (bi: number) =>
    updatePlan((draft) => {
      draft.blocks.splice(bi, 1);
    });

  const addRound = (bi: number) =>
    updatePlan((draft) => {
      const b = draft.blocks[bi];
      const rounds = b.rounds ?? [];
      if (rounds.length === 0) return;
      const last = rounds[rounds.length - 1];
      b.rounds = [...rounds, structuredClone(last)];
      b.duration_min = b.rounds.reduce(
        (a, r) => a + r.work_min + r.transition_min,
        0
      );
    });

  const removeRound = (bi: number, ri: number) =>
    updatePlan((draft) => {
      const b = draft.blocks[bi];
      const rounds = b.rounds;
      if (!rounds || rounds.length <= 1) return;
      rounds.splice(ri, 1);
      b.duration_min = rounds.reduce((a, r) => a + r.work_min + r.transition_min, 0);
    });

  const groupLabel = (gid: string) => {
    const g = (plan?.groups ?? []).find((x) => x.id === gid);
    return g ? `Groupe ${g.id}` : gid;
  };

  const runServerCheck = async () => {
    if (!plan || checking) return;
    setChecking(true);
    setServerError(null);
    try {
      const res = await validerSeance(plan);
      setServerCheck(res);
      setServerTime(new Date().toLocaleTimeString("fr-FR", { hour12: false }));
    } catch (e) {
      setServerError((e as Error).message);
      setServerCheck(null);
    } finally {
      setChecking(false);
    }
  };

  // Le résultat serveur est la référence : on signale tout écart avec le
  // miroir local (normalement nul — les deux sont le même contrat).
  const serverDiverges =
    serverCheck !== null &&
    localCheck !== null &&
    JSON.stringify({
      valide: serverCheck.valide,
      erreurs: serverCheck.erreurs,
      avertissements: serverCheck.avertissements,
    }) !==
      JSON.stringify({
        valide: localCheck.valide,
        erreurs: localCheck.erreurs,
        avertissements: localCheck.avertissements,
      });

  const pickExercise = (id: string) => {
    if (!picker) return;
    updatePlan((draft) => {
      const b = draft.blocks[picker.blockIndex];
      if (picker.kind === "slot") {
        b.rounds![picker.roundIndex].assignments[picker.slotIndex].variant_id = id;
      } else if (!b.variant_ids.includes(id)) {
        b.variant_ids.push(id);
      }
    });
    setPicker(null);
    setPickerQuery("");
  };

  const pickerResults = picker
    ? selectCards(cards, { query: pickerQuery, includeIncomplete: true })
    : [];

  // --- Lot 4 : reprise / export / import / effacement du brouillon. ---

  // Applique un plan (reprise, import, trame) et remet à zéro les états
  // dépendants : résultat serveur, picker, erreur d'import.
  const applyPlan = (p: SessionPlan) => {
    setPlan(clonePlan(p));
    setServerCheck(null);
    setServerTime(null);
    setServerError(null);
    setPicker(null);
    setPickerQuery("");
  };

  const resumeDraft = () => {
    if (!pendingDraft) return;
    applyPlan(pendingDraft.plan);
    setSavedAt(pendingDraft.saved_at || null);
    setPendingDraft(null);
    setImportError(null);
  };

  // Repartir de la trame U8 : le brouillon est effacé (action explicite,
  // jamais silencieuse) et la trame de départ est réappliquée.
  const restartFromTrame = () => {
    if (!initialDraft) return;
    clearDraft();
    applyPlan(initialDraft);
    setSavedAt(null);
    setPendingDraft(null);
    setImportError(null);
  };

  // Export : le plan brut (même contrat que le validateur) en fichier JSON.
  const exportDraft = () => {
    if (!plan) return;
    const blob = new Blob([JSON.stringify(plan, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const d = new Date();
    const pad = (n: number) => String(n).padStart(2, "0");
    a.href = url;
    a.download = `seance-${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const onImportFile = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ""; // permet de ré-importer le même fichier
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const p = parseImport(String(reader.result ?? ""));
      if (!p) {
        setImportError(
          "Fichier invalide : attendu un plan de séance JSON (export de cette application)."
        );
        return;
      }
      applyPlan(p);
      const t = saveDraft(p);
      if (t) setSavedAt(t);
      setPendingDraft(null);
      setImportError(null);
    };
    reader.onerror = () => setImportError("Lecture du fichier impossible.");
    reader.readAsText(file);
  };

  if (loadError) {
    return (
      <div className="empty">
        <h2>Trame de référence indisponible</h2>
        <p>{loadError}</p>
      </div>
    );
  }
  if (!plan || !localCheck || !min) {
    return (
      <>
        <div className="skeleton skeleton-line" style={{ width: "50%" }} />
        <div className="skeleton skeleton-card" />
        <div className="skeleton skeleton-card" />
      </>
    );
  }

  return (
    <div className="seance">
      {pendingDraft && (
        <div className="draft-banner" role="alert">
          <p>
            Brouillon sauvegardé
            {pendingDraft.saved_at ? ` le ${savedLabel(pendingDraft.saved_at)}` : ""} —
            le reprendre, ou repartir de la trame U8 ?
          </p>
          <div className="draft-banner-actions">
            <button className="apply-btn" onClick={resumeDraft}>
              Reprendre le brouillon
            </button>
            <button className="reset-btn" onClick={restartFromTrame}>
              Repartir de la trame U8
            </button>
          </div>
        </div>
      )}
      <section className="seance-head">
        <label className="field">
          <span className="field-label">Titre de la séance</span>
          <input
            className="text-input"
            type="text"
            value={plan.title}
            onChange={(e) => updatePlan((d) => void (d.title = e.target.value))}
          />
        </label>
        <div className="field-row">
          <label className="field">
            <span className="field-label">Créneau (min)</span>
            <input
              className="num-input"
              type="number"
              inputMode="numeric"
              min={0}
              step={5}
              value={plan.creneau_min}
              onChange={(e) =>
                updatePlan((d) => {
                  d.creneau_min = Number.isInteger(+e.target.value) ? +e.target.value : 0;
                })
              }
            />
          </label>
          <label className="field">
            <span className="field-label">Éducateurs</span>
            <input
              className="num-input"
              type="number"
              inputMode="numeric"
              min={0}
              step={1}
              value={plan.coaches ?? 0}
              onChange={(e) =>
                updatePlan((d) => {
                  d.coaches = Number.isInteger(+e.target.value) ? +e.target.value : 0;
                })
              }
            />
          </label>
        </div>
        <div className="field-row" role="group" aria-label="Effectifs par groupe">
          {(plan.groups ?? []).map((g) => (
            <label className="field" key={g.id}>
              <span className="field-label">Groupe {g.id} (joueurs)</span>
              <input
                className="num-input"
                type="number"
                inputMode="numeric"
                min={0}
                step={1}
                value={g.players}
                onChange={(e) =>
                  updatePlan((d) => {
                    const grp = d.groups.find((x) => x.id === g.id);
                    if (!grp) return;
                    grp.players = Number.isInteger(+e.target.value) ? +e.target.value : 0;
                    d.players = d.groups.reduce((a, x) => a + x.players, 0);
                  })
                }
              />
            </label>
          ))}
          <label className="field">
            <span className="field-label">Total</span>
            <span className="total-players" aria-live="polite">{plan.players}</span>
          </label>
        </div>
      </section>

      {/* Minutage dérivée — jamais stockée, recalculée à chaque frappe. */}
      <div className="seance-stats" aria-live="polite">
        <div className="stat-tile">
          <span className="stat-value">{min.creneau_min}</span>
          <span className="stat-label">Créneau (min)</span>
        </div>
        <div className="stat-tile">
          <span className="stat-value">
            {min.planifie_min}
            {min.partiel && <span className="stat-hint"> (partiel)</span>}
          </span>
          <span className="stat-label">Planifié (min)</span>
        </div>
        <div className={"stat-tile" + (min.marge_min < 0 ? " stat-neg" : "")}>
          <span className="stat-value">{min.marge_min}</span>
          <span className="stat-label">{min.marge_min < 0 ? "Dépassement (min)" : "Marge (min)"}</span>
        </div>
        <div className="stat-tile">
          <span className="stat-value">{min.opposition_min}</span>
          <span className="stat-label">Opposition (min)</span>
        </div>
      </div>

      <section className="seance-blocks">
        <h2>Blocs de la séance</h2>
        <ol className="timeline">
          {plan.blocks.map((b, bi) => (
            <li className="seance-block" key={bi}>
              <div className="seance-block-head">
                <span className={"kind-badge kind-" + b.kind}>{KIND_LABELS[b.kind] ?? b.kind}</span>
                <input
                  className="block-label"
                  type="text"
                  aria-label="Libellé du bloc"
                  value={b.label}
                  onChange={(e) =>
                    updatePlan((d) => void (d.blocks[bi].label = e.target.value))
                  }
                />
                <button
                  className="block-delete"
                  aria-label={`Supprimer le bloc ${b.label}`}
                  onClick={() => removeBlock(bi)}
                >
                  ×
                </button>
              </div>

              {b.kind === "WORKSHOPS" ? (
                <div className="workshops">
                  {(b.rounds ?? []).map((r, ri) => (
                    <div className="rotation" key={ri}>
                      <div className="rotation-head">
                        <span className="rotation-title">Rotation {ri + 1}</span>
                        {(b.rounds ?? []).length > 1 && (
                          <button
                            className="block-delete"
                            aria-label={`Supprimer la rotation ${ri + 1}`}
                            onClick={() => removeRound(bi, ri)}
                          >
                            ×
                          </button>
                        )}
                      </div>
                      <div className="field-row">
                        <label className="field">
                          <span className="field-label">Travail (min)</span>
                          <input
                            className="num-input"
                            type="number"
                            inputMode="numeric"
                            min={1}
                            step={1}
                            value={r.work_min}
                            onChange={(e) =>
                              updatePlan((d) => {
                                const blk = d.blocks[bi];
                                const rnd = blk.rounds![ri];
                                const v = Number.isInteger(+e.target.value) ? +e.target.value : 0;
                                rnd.work_min = v;
                                blk.duration_min = blk.rounds!.reduce(
                                  (a, x) => a + x.work_min + x.transition_min,
                                  0
                                );
                              })
                            }
                          />
                        </label>
                        <label className="field">
                          <span className="field-label">Transition (min)</span>
                          <input
                            className="num-input"
                            type="number"
                            inputMode="numeric"
                            min={0}
                            step={1}
                            value={r.transition_min}
                            onChange={(e) =>
                              updatePlan((d) => {
                                const blk = d.blocks[bi];
                                const rnd = blk.rounds![ri];
                                const v = Number.isInteger(+e.target.value) ? +e.target.value : 0;
                                rnd.transition_min = v;
                                blk.duration_min = blk.rounds!.reduce(
                                  (a, x) => a + x.work_min + x.transition_min,
                                  0
                                );
                              })
                            }
                          />
                        </label>
                      </div>
                      {r.assignments.map((s, si) => (
                        <button
                          className="slot-row"
                          key={si}
                          onClick={() =>
                            setPicker({ kind: "slot", blockIndex: bi, roundIndex: ri, slotIndex: si })
                          }
                        >
                          <span className="slot-who">
                            {groupLabel(s.group_id)} → {s.station_id}
                          </span>
                          <span className="slot-exercise">
                            {s.variant_id ? cardById[s.variant_id]?.title ?? s.variant_id : "Choisir un exercice…"}
                          </span>
                        </button>
                      ))}
                    </div>
                  ))}
                  <div className="rotation-foot">
                    <span className="stat-label">
                      Durée du bloc : {b.duration_min} min (somme des rotations)
                    </span>
                    <button className="add-round-btn" onClick={() => addRound(bi)}>
                      + Rotation
                    </button>
                  </div>
                </div>
              ) : (
                <div className="simple-block">
                  <label className="field">
                    <span className="field-label">Durée (min)</span>
                    <input
                      className="num-input"
                      type="number"
                      inputMode="numeric"
                      min={1}
                      step={1}
                      value={b.duration_min ?? 0}
                      onChange={(e) =>
                        updatePlan((d) => {
                          d.blocks[bi].duration_min = Number.isInteger(+e.target.value)
                            ? +e.target.value
                            : 0;
                        })
                      }
                    />
                  </label>
                  {b.variant_ids.length > 0 && (
                    <div className="assigned-row">
                      {b.variant_ids.map((id, i) => (
                        <button
                          className="chip assigned-chip"
                          key={id + "-" + i}
                          title="Retirer de ce bloc"
                          onClick={() =>
                            updatePlan((d) => {
                              d.blocks[bi].variant_ids.splice(i, 1);
                            })
                          }
                        >
                          {cardById[id]?.title ?? id} <span className="chip-x">×</span>
                        </button>
                      ))}
                    </div>
                  )}
                  <button className="add-round-btn" onClick={() => setPicker({ kind: "block", blockIndex: bi })}>
                    + Exercice
                  </button>
                </div>
              )}
            </li>
          ))}
        </ol>

        <h3 className="add-block-title">Ajouter un bloc</h3>
        <div className="add-block-row">
          {(Object.keys(KIND_LABELS) as SessionPlan["blocks"][number]["kind"][]).map((k) => (
            <button key={k} className="add-block-btn" onClick={() => addBlock(k)}>
              + {KIND_LABELS[k]}
            </button>
          ))}
        </div>
      </section>

      {(plan.pending_decisions?.length || plan.note) && (
        <section className="seance-notes">
          <h2>À confirmer (gabarit)</h2>
          {plan.note && <p className="note-text">{plan.note}</p>}
          {plan.pending_decisions?.length ? (
            <ul>
              {plan.pending_decisions.map((d, i) => (
                <li key={i}>{d}</li>
              ))}
            </ul>
          ) : null}
        </section>
      )}

      <section className="seance-check">
        <h2>Contrôles structurels</h2>
        {localCheck.valide ? (
          <p className="check-ok">Séance cohérente : aucun contrôle bloquant.</p>
        ) : (
          <ul className="check-errs">
            {localCheck.erreurs.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        )}
        {localCheck.avertissements.length > 0 && (
          <ul className="check-warns">
            {localCheck.avertissements.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        )}
        <div className="check-actions">
          <button className="apply-btn" onClick={runServerCheck} disabled={checking}>
            {checking ? "Vérification en cours…" : "Vérifier (serveur)"}
          </button>
        </div>
        {serverError && <p className="check-err-text">Vérification serveur impossible : {serverError}</p>}
        {serverCheck && serverTime && (
          <div className="seance-server-result">
            <p className={"check-ok " + (serverDiverges ? "check-diverge" : "")}>
              Serveur, {serverTime} : {serverCheck.valide ? "valide" : "non valide"} —{" "}
              {serverCheck.erreurs.length} erreur{serverCheck.erreurs.length > 1 ? "s" : ""},{" "}
              {serverCheck.avertissements.length} avertissement
              {serverCheck.avertissements.length > 1 ? "s" : ""}.
            </p>
            {serverDiverges && (
              <p>
                Résultat serveur différent du calcul local (le serveur fait foi) :
              </p>
            )}
            {serverDiverges && (
              <>
                {serverCheck.erreurs.map((e, i) => (
                  <p className="check-err-text" key={"e" + i}>{e}</p>
                ))}
                {serverCheck.avertissements.map((a, i) => (
                  <p className="check-warn-text" key={"a" + i}>{a}</p>
                ))}
              </>
            )}
          </div>
        )}
      </section>

      <section className="seance-save">
        <h2>Sauvegarde et reprise</h2>
        <p className="save-status" aria-live="polite">
          {savedAt
            ? `Brouillon sauvegardé le ${savedLabel(savedAt)} (ce navigateur).`
            : "Aucun brouillon sauvegardé pour l'instant."}
        </p>
        <div className="check-actions">
          <button className="apply-btn" onClick={exportDraft}>
            ⬇ Exporter (JSON)
          </button>
          <button className="reset-btn" onClick={() => fileRef.current?.click()}>
            ⬆ Importer (JSON)
          </button>
          <button className="reset-btn" onClick={restartFromTrame}>
            Effacer et repartir de la trame U8
          </button>
        </div>
        <input
          ref={fileRef}
          type="file"
          accept="application/json,.json"
          hidden
          onChange={onImportFile}
        />
        {importError && <p className="check-err-text">{importError}</p>}
      </section>

      {picker && (
        <>
          <div className="sheet-backdrop" onClick={() => setPicker(null)} />
          <div className="sheet" role="dialog" aria-modal="true" aria-label="Choisir un exercice">
            <div className="sheet-handle" aria-hidden="true" />
            <h2>Choisir un exercice</h2>
            <input
              className="search-input"
              type="search"
              placeholder="Rechercher (titre, résumé, titre original)…"
              aria-label="Rechercher un exercice"
              value={pickerQuery}
              onChange={(e) => setPickerQuery(e.target.value)}
            />
            <div className="picker-list">
              {pickerResults.length === 0 && <p className="picker-empty">Aucun exercice ne correspond.</p>}
              {pickerResults.map((c) => (
                <button
                  key={c.id}
                  className="picker-row"
                  onClick={() => pickExercise(c.id)}
                >
                  <span className="card-title">{c.title}</span>
                  <span className="picker-meta">
                    {BADGE_LABELS[c.state] && (
                      <span className={"badge " + BADGE_CLASS[c.state]}>{BADGE_LABELS[c.state]}</span>
                    )}
                    {cardDurationLabel(c.planning_min_seconds, c.planning_max_seconds, c.duration_status)}
                  </span>
                </button>
              ))}
            </div>
            <div className="sheet-footer">
              <button className="reset-btn" onClick={() => setPicker(null)}>
                Fermer
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
