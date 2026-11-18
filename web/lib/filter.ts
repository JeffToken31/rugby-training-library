// Miroir exact de webapp.select_catalogue / webapp.fold (lui-même miroir de
// exercise_tags.select) : même sémantique all/any, mêmes champs de recherche,
// insensible aux accents. La liste est de 158 fiches : le filtrage côté client
// reste bien en deçà de l'objectif de 300 ms.

import type { Card } from "./types";

// webapp.fold : minuscules + sans accents (« é » et « e » tombent ensemble).
export function fold(text: string | null | undefined): string {
  if (!text) return "";
  return text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

// _search_match : titre, original_title ou résumé.
export function searchMatch(queryFolded: string, c: Card): boolean {
  return (
    fold(c.title).includes(queryFolded) ||
    fold(c.original_title).includes(queryFolded) ||
    fold(c.summary).includes(queryFolded)
  );
}

export interface FilterOptions {
  query?: string;
  tagIds?: string[];
  match?: "all" | "any";
  includeIncomplete?: boolean;
  usage?: string | null;
}

export function selectCards(cards: Card[], opts: FilterOptions = {}): Card[] {
  const wanted = (opts.tagIds ?? []).filter((t) => t !== "");
  const match = opts.match ?? "all";
  const qf = opts.query ? fold(opts.query) : "";
  const out: Card[] = [];
  for (const c of cards) {
    if (!opts.includeIncomplete && !c.default_visible) continue;
    if (opts.usage && !c.session_uses.includes(opts.usage)) continue;
    if (wanted.length > 0 && match === "all" && !wanted.every((t) => c.tag_ids.includes(t))) continue;
    if (wanted.length > 0 && match === "any" && !wanted.some((t) => c.tag_ids.includes(t))) continue;
    if (qf && !searchMatch(qf, c)) continue;
    out.push(c);
  }
  return out;
}
