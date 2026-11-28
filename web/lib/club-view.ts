import type { Equipe } from "./types";

// Vue « ma catégorie » (lot P4, 2026-11-26, charter-workflows critère 4) :
// un compte portant une catégorie ouvre /club filtré sur sa catégorie, avec
// bascule « tout ». Les équipes sont des enregistrements par compte, chacun
// portant sa catégorie (équipes.categorie) — c'est donc bien le niveau de la
// catégorie qui filtre. Les coachs et joueurs restent au niveau club : les
// tables coachs et joueurs_club n'ont pas de colonne catégorie (D4 — le
// magasin joueurs est partagé au club).

/** Équipes visibles pour un compte selon la vue choisie.
 *
 * - `categorie` null ou bascule « tout » activée → toutes les équipes ;
 * - sinon, seulement celles dont la catégorie est celle du compte
 *   (comparaison exacte : la liste contrôlée des catégories ne tolère
 *   pas de variante orthographique).
 *
 * Fonction pure : le groupement en sections (ordre de la nomenclature +
 * bac « Sans catégorie ») reste du côté de la page. */
export function equipesVisibles(
  equipes: Equipe[],
  categorie: string | null,
  tout: boolean
): Equipe[] {
  if (!categorie || tout) return equipes;
  return equipes.filter((e) => e.categorie === categorie);
}
