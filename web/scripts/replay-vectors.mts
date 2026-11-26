// n3 (tranché le 2026-11-22) : rejoue tests/vectors.json côté TypeScript,
// en miroir strict de tests/test_vectors.py (Python). Même corpus, mêmes
// attentes — verrouille la leçon m1 des deux côtés (flottants entiers
// acceptés, flottants non entiers et booléens refusés) et la parité des
// messages entre web/lib/session.ts et session_plan.py.
// Lot P4 (2026-11-26) : en fin de fichier, un « snapshot front » de la
// fonction pure `equipesVisibles` (vue « ma catégorie » sur /club,
// charter-workflows critère 4) — testée hors miroir 15+8, qui reste
// strictement identique.
// Lancement : npm run test:vectors depuis web/ (transpile tsc → CommonJS
// dans .vectors-build/, puis node — le Node WSL de ce dépôt est compilé
// sans support des types TypeScript).

import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

import { validerLocale } from "../lib/session";
import { selectCards } from "../lib/filter";
import type { Card, Equipe, GroupeEquipe, SessionGroup } from "../lib/types";
import { equipesVisibles } from "../lib/club-view";
import { basculerPresences, redistribuerPresences } from "../lib/equipes";

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

// Lot P4 (2026-11-26) — vue « ma catégorie » : snapshot de la fonction
// pure `equipesVisibles` (web/lib/club-view.ts), hors miroir 15+8.
function equipe(nom: string, categorie: string | null): Equipe {
  return {
    id: nom,
    nom,
    club: "RC Test",
    categorie,
    effectif: null,
    coachs: [],
    joueurs: [],
    groupes: [],
    saved_at: "2026-11-26T00:00:00Z",
  };
}
const eqU8a = equipe("U8 A", "U8");
const eqU8b = equipe("U8 B", "U8");
const eqU10 = equipe("U10", "U10");
const eqSans = equipe("Mixte", null);
const toutes = [eqU8a, eqU8b, eqU10, eqSans];
comparer("p4: compte U8, vue sa catégorie", [eqU8a, eqU8b], equipesVisibles(toutes, "U8", false), "équipes");
comparer("p4: compte U8, bascule « tout »", toutes, equipesVisibles(toutes, "U8", true), "équipes");
comparer("p4: compte sans catégorie, vue par défaut", toutes, equipesVisibles(toutes, null, false), "équipes");
comparer("p4: compte sans catégorie, bascule sans effet", toutes, equipesVisibles(toutes, null, true), "équipes");
comparer("p4: équipe sans catégorie exclue de la vue catégorie", [], equipesVisibles([eqSans], "U8", false), "équipes");

// Lot P5 (2026-11-26) — cases de présence à l’attachement : snapshot des
// fonctions pures (web/lib/equipes.ts), hors miroir 15+8. Le contrat de
// séance est inchangé : les validateurs ne lisent que `players`.
function grp(id: string, joueurs: string[], name?: string): SessionGroup {
  const g: SessionGroup = { id, players: joueurs.length };
  if (name !== undefined) g.name = name;
  if (joueurs.length > 0) g.joueurs = joueurs;
  return g;
}
const plats: SessionGroup[] = [grp("g1", []), grp("g2", [])];
const nommés: SessionGroup[] = [
  grp("g1", ["Ada", "Ben"], "Groupe A"),
  grp("g2", ["Chloé", "Dan"], "Groupe B"),
];
const sourceNommée: GroupeEquipe[] = [
  { nom: "Groupe A", joueurs: ["Ada", "Ben"] },
  { nom: "Groupe B", joueurs: ["Chloé", "Dan"] },
];
comparer(
  "p5: mode plat, aucune absence → chaque joueur réparti exactement une fois",
  [grp("g1", ["Ada", "Chloé"]), grp("g2", ["Ben", "Dan"])],
  redistribuerPresences(plats, ["Ada", "Ben", "Chloé", "Dan"], {}, null),
  "groupes",
);
comparer(
  "p5: joueur décoché n’apparaît dans aucun groupe",
  [grp("g1", ["Ada", "Dan"]), grp("g2", ["Chloé"])],
  redistribuerPresences(plats, ["Ada", "Ben", "Chloé", "Dan"], { Ben: false }, null),
  "groupes",
);
comparer(
  "p5: récoche → le joueur revient dans son slot d’origine (déterminisme)",
  [grp("g1", ["Ada", "Chloé"]), grp("g2", ["Ben", "Dan"])],
  redistribuerPresences(
    plats,
    ["Ada", "Ben", "Chloé", "Dan"],
    basculerPresences(basculerPresences({}, "Ben"), "Ben"),
    null,
  ),
  "groupes",
);
comparer(
  "p5: mode nommé → l’absent est retiré de SON groupe seulement",
  [grp("g1", ["Ada"], "Groupe A"), grp("g2", ["Chloé", "Dan"], "Groupe B")],
  redistribuerPresences(nommés, ["Ada", "Ben", "Chloé", "Dan"], { Ben: false }, sourceNommée),
  "groupes",
);
comparer(
  "p5: mode nommé → le groupe ajouté au-delà de la source est inchangé",
  [
    grp("g1", ["Ada"], "Groupe A"),
    grp("g2", ["Chloé", "Dan"], "Groupe B"),
    grp("g3", ["Eli", "Fan"], "Groupe C"),
  ],
  redistribuerPresences(
    [nommés[0], nommés[1], grp("g3", ["Eli", "Fan"], "Groupe C")],
    ["Ada", "Ben", "Chloé", "Dan"],
    { Ben: false },
    sourceNommée,
  ),
  "groupes",
);

const total = vectors.sessions.length + vectors.filters.length;
if (echecs > 0) {
  console.error(`\n${echecs} échec(s) sur ${total} vecteurs.`);
  process.exit(1);
}
console.log(`Vecteurs OK : ${vectors.sessions.length} séances + ${vectors.filters.length} filtres (miroir TS).`);
