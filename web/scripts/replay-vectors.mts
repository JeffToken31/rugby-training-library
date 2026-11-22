// n3 (tranché le 2026-11-22) : rejoue tests/vectors.json côté TypeScript,
// en miroir strict de tests/test_vectors.py (Python). Même corpus, mêmes
// attentes — verrouille la leçon m1 des deux côtés (flottants entiers
// acceptés, flottants non entiers et booléens refusés) et la parité des
// messages entre web/lib/session.ts et session_plan.py.
// Lancement : npm run test:vectors depuis web/ (transpile tsc → CommonJS
// dans .vectors-build/, puis node — le Node WSL de ce dépôt est compilé
// sans support des types TypeScript).

import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

import { validerLocale } from "../lib/session";
import { selectCards } from "../lib/filter";
import type { Card } from "../lib/types";

// Exécuté depuis web/ (npm run test:vectors) : le repo est le parent.
const root = new URL("../", pathToFileURL(process.cwd() + "/"));
const vectors = JSON.parse(
  readFileSync(new URL("tests/vectors.json", root), "utf-8")
);
const payload = JSON.parse(
  readFileSync(new URL("exports/APPLICATION.json", root), "utf-8")
);

let echecs = 0;
function comparer(nom: string, attendu: unknown, obtenu: unknown, champ: string) {
  const a = JSON.stringify(attendu);
  const o = JSON.stringify(obtenu);
  if (a !== o) {
    echecs += 1;
    console.error(`ÉCHEC ${nom} (${champ}):\n  attendu ${a}\n  obtenu  ${o}`);
  }
}

// Séances : miroir de session_plan.validate + webapp.minutage_derivee.
for (const vec of vectors.sessions) {
  const check = validerLocale(vec.plan, vec.etat);
  comparer(vec.name, vec.expected, check, "séance");
}

// Filtres : miroir de webapp.select_catalogue sur le vrai APPLICATION.json.
const cards: Card[] = payload.exercises.map((e: any) => ({
  id: e.id,
  title: e.title,
  original_title: e.original_title ?? null,
  summary: e.summary ?? null,
  state: e.quality.state,
  default_visible: e.quality.default_visible,
  tag_ids: e.tag_ids ?? [],
  session_uses: e.session_uses ?? [],
  planning_min_seconds: null,
  planning_max_seconds: null,
  duration_status: null,
  media: { video: null, local_capture: null },
}));
for (const vec of vectors.filters) {
  const o = vec.opts;
  const cartes = selectCards(cards, {
    query: o.query,
    tagIds: o.tag_ids ?? [],
    match: o.match ?? "all",
    includeIncomplete: o.include_incomplete ?? true,
    usage: o.usage ?? null,
  });
  const ids = cartes.map((c) => c.id).sort();
  if ("ids" in vec.expected) {
    comparer(vec.name, vec.expected.ids.slice().sort(), ids, "ids");
  } else {
    comparer(vec.name, vec.expected.count, cartes.length, "count");
  }
}

const total = vectors.sessions.length + vectors.filters.length;
if (echecs > 0) {
  console.error(`\n${echecs} échec(s) sur ${total} vecteurs.`);
  process.exit(1);
}
console.log(`Vecteurs OK : ${vectors.sessions.length} séances + ${vectors.filters.length} filtres (miroir TS).`);
