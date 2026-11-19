// Page unique du lot 1 : catalogue (S1) + filtres (S2) + fiche (S3) +
// aucun résultat (S4) + squelettes (S5). Liste en état React (pas de
// routing client) : pas de 404 au refresh, un seul chargement initial.
// Recherche et filtres côté client — miroir exact de webapp.select_catalogue.

import { useEffect, useMemo, useState } from "react";
import type { CatalogueView, Fiche, Card } from "../lib/types";
import { fetchCatalogue, fetchFiche } from "../lib/api";
import { selectCards } from "../lib/filter";
import CatalogCard from "../components/CatalogCard";
import FicheDetail from "../components/FicheDetail";
import FiltersSheet from "../components/FiltersSheet";

const PAGE = 30; // 158 fiches : on n'affiche pas tout d'un coup (maquette).

type Theme = "light" | "dark";

export default function Home() {
  const [view, setView] = useState<CatalogueView | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [match, setMatch] = useState<"all" | "any">("all");
  const [warmupOnly, setWarmupOnly] = useState(false);
  // Défaut produit (décision coach 2026-11-18) : les fiches incomplètes sont
  // affichées avec leur badge d'état ; l'interrupteur sert à les masquer.
  const [showIncomplete, setShowIncomplete] = useState(true);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [visibleCount, setVisibleCount] = useState(PAGE);

  const [selectedCard, setSelectedCard] = useState<Card | null>(null);
  const [selectedFiche, setSelectedFiche] = useState<Fiche | null>(null);
  const [ficheError, setFicheError] = useState<string | null>(null);

  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    let live = true;
    fetchCatalogue()
      .then((v) => live && setView(v))
      .catch((e: Error) => live && setLoadError(e.message));
    return () => {
      live = false;
    };
  }, []);

  // Thème : persisté côté client, jamais de mismatch SSR.
  useEffect(() => {
    const saved = window.localStorage.getItem("rtrl-theme");
    if (saved === "dark" || saved === "light") setTheme(saved);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("rtrl-theme", theme);
  }, [theme]);

  const cards: Card[] = view?.cards ?? [];

  const tagLabels = useMemo(() => {
    const m: Record<string, string> = {};
    for (const t of view?.tag_taxonomy?.tags ?? []) m[t.id] = t.label;
    return m;
  }, [view]);

  // Couverture réelle du corpus par tag (fiches incomplètes comprises) :
  // un tag « Placage (1) » montre la vérité du catalogue, pas un filtre en panne.
  const tagCounts = useMemo(() => {
    const m: Record<string, number> = {};
    for (const c of cards) for (const t of c.tag_ids) m[t] = (m[t] ?? 0) + 1;
    return m;
  }, [cards]);

  const filtered = useMemo(
    () =>
      selectCards(cards, {
        query,
        tagIds: selectedTags,
        match,
        includeIncomplete: showIncomplete,
        usage: warmupOnly ? "WARMUP" : null,
      }),
    [cards, query, selectedTags, match, showIncomplete, warmupOnly]
  );

  // Fiches masquées uniquement par l'interrupteur « incomplètes » : sert à
  // l'état vide honnête (« 1 fiche incomplète correspond — l'afficher ? »).
  const hiddenIncomplete = useMemo(() => {
    if (showIncomplete || filtered.length > 0) return 0;
    const withAll = selectCards(cards, {
      query,
      tagIds: selectedTags,
      match,
      includeIncomplete: true,
      usage: warmupOnly ? "WARMUP" : null,
    });
    return withAll.length - filtered.length;
  }, [cards, query, selectedTags, match, showIncomplete, warmupOnly, filtered.length]);

  const shown = filtered.slice(0, visibleCount);

  const openFiche = (id: string) => {
    const card = cards.find((c) => c.id === id) ?? null;
    setSelectedCard(card);
    setSelectedFiche(null);
    setFicheError(null);
    window.scrollTo({ top: 0 });
    fetchFiche(id)
      .then((f) => setSelectedFiche(f))
      .catch((e: Error) => setFicheError(e.message));
  };

  const closeFiche = () => {
    setSelectedCard(null);
    setSelectedFiche(null);
    setFicheError(null);
  };

  const toggleTag = (id: string) =>
    setSelectedTags((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );

  const resetFilters = () => {
    setSelectedTags([]);
    setMatch("all");
    setWarmupOnly(false);
    setShowIncomplete(true); // retour au défaut produit : tout afficher
    setQuery("");
  };

  const filtersActive =
    selectedTags.length > 0 || warmupOnly || showIncomplete || query.trim() !== "";

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-title-row">
          {selectedCard && (
            <button className="back-btn" onClick={closeFiche} aria-label="Retour au catalogue">
              ←
            </button>
          )}
          <h1 className="app-title">Rugby Training Library</h1>
          <button
            className="theme-btn"
            onClick={() => setTheme((t) => (t === "light" ? "dark" : "light"))}
            aria-label={theme === "light" ? "Passer en thème sombre" : "Passer en thème clair"}
          >
            {theme === "light" ? "🌙" : "☀️"}
          </button>
        </div>

        {!selectedCard && (
          <>
            <input
              className="search-input"
              type="search"
              placeholder="Rechercher (titre, résumé, titre original)…"
              aria-label="Rechercher un exercice"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setVisibleCount(PAGE);
              }}
            />
            <div className="toolbar-row">
              <button
                className="filters-btn"
                aria-expanded={filtersOpen}
                aria-haspopup="dialog"
                onClick={() => setFiltersOpen(true)}
              >
                Filtres{selectedTags.length > 0 ? ` (${selectedTags.length})` : ""}
              </button>
              <span className="count" aria-live="polite">
                {view ? `${filtered.length} fiche${filtered.length > 1 ? "s" : ""}` : "…"}
              </span>
            </div>
          </>
        )}
      </header>

      <main className="app-main">
        {selectedCard ? (
          <FicheDetail fiche={selectedFiche} tagLabels={tagLabels} error={ficheError} />
        ) : loadError ? (
          <div className="empty">
            <h2>Catalogue indisponible</h2>
            <p>{loadError}</p>
          </div>
        ) : !view ? (
          <>
            <div className="skeleton skeleton-line" style={{ width: "60%" }} />
            <div className="skeleton skeleton-line" style={{ width: "40%" }} />
            {[0, 1, 2, 3].map((i) => (
              <div className="skeleton skeleton-card" key={i} />
            ))}
          </>
        ) : filtered.length === 0 ? (
          <div className="empty">
            <h2>Aucun résultat</h2>
            {hiddenIncomplete > 0 && (
              <>
                <p>
                  {hiddenIncomplete === 1
                    ? "1 fiche incomplète correspond à ces critères mais est masquée par l'interrupteur « Afficher les fiches incomplètes »."
                    : `${hiddenIncomplete} fiches incomplètes correspondent à ces critères mais sont masquées par l'interrupteur « Afficher les fiches incomplètes ».`}
                </p>
                <button className="load-more-btn" onClick={() => setShowIncomplete(true)}>
                  Inclure les fiches incomplètes
                </button>
              </>
            )}
            <p>
              {hiddenIncomplete === 0 &&
                (filtersActive
                  ? "Aucune fiche ne correspond à ces critères."
                  : "Le catalogue est vide.")}
            </p>
            <button className="load-more-btn" onClick={resetFilters}>
              Réinitialiser les filtres
            </button>
          </div>
        ) : (
          <>
            {shown.map((card) => (
              <CatalogCard key={card.id} card={card} tagLabels={tagLabels} onOpen={openFiche} />
            ))}
            {filtered.length > shown.length && (
              <button className="load-more-btn" onClick={() => setVisibleCount((n) => n + PAGE)}>
                Continuer ({filtered.length - shown.length} restante{filtered.length - shown.length > 1 ? "s" : ""})
              </button>
            )}
          </>
        )}
      </main>

      {filtersOpen && (
        <FiltersSheet
          tags={view?.tag_taxonomy?.tags ?? []}
          tagCounts={tagCounts}
          selectedTags={selectedTags}
          onToggleTag={toggleTag}
          warmupOnly={warmupOnly}
          onToggleWarmup={() => setWarmupOnly((v) => !v)}
          showIncomplete={showIncomplete}
          onToggleIncomplete={() => setShowIncomplete((v) => !v)}
          match={match}
          onMatch={setMatch}
          count={filtered.length}
          onReset={resetFilters}
          onApply={() => {
            setVisibleCount(PAGE);
            setFiltersOpen(false);
          }}
        />
      )}
    </div>
  );
}
