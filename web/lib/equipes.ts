import type { GroupeEquipe, SessionGroup } from "./types";

/** Fonctions pures de la copie snapshot équipe → groupes (lot L3, v1.1).
 *
 * Une équipe enregistrée est une source : l'attacher à une séance COPIE
 * ses joueurs dans les groupes existants. Les validateurs (Python et TS)
 * ignorent les noms — seuls les `players` (effectifs) sont validés — ces
 * fonctions servent uniquement au préremplissage lisible du constructeur. */

/** Parse le saisi dans la zone « Joueurs » d'un formulaire d'équipe :
 * lignes non vides, trim, dans l'ordre d'écriture. Les doublons sont
 * dédoublonnés insensiblement à la casse (la casse de la première
 * occurrence est conservée) — même règle que le serveur, pour que ce que
 * l'on saisit soit ce que l'on voit après envoi. */
export function parserJoueurs(texte: string): string[] {
  const vus = new Set<string>();
  const resultats: string[] = [];
  for (const ligne of texte.split("\n")) {
    const nom = ligne.trim();
    if (nom.length === 0) continue;
    const cle = nom.toLowerCase();
    if (vus.has(cle)) continue;
    vus.add(cle);
    resultats.push(nom);
  }
  return resultats;
}

/** Répartition round-robin des noms sur les groupes EXISTANTS :
 * joueur i → groupe (i mod k). Le nombre de groupes ne change JAMAIS —
 * les rotations ont un slot par groupe, un groupe vide est un état
 * transitoire que le miroir local signale (précédent : `addGroup`). */
export function roundRobinJoueurs(
  joueurs: string[],
  groupIds: string[],
): Record<string, string[]> {
  const parGroupe: Record<string, string[]> = {};
  for (const gid of groupIds) parGroupe[gid] = [];
  if (groupIds.length === 0) return parGroupe;
  joueurs.forEach((nom, i) => {
    parGroupe[groupIds[i % groupIds.length]].push(nom);
  });
  return parGroupe;
}

/** Répartition numérique d'un effectif total sur k groupes : la base
 * est `floor(total / k)` et le reste est ajouté aux premiers groupes —
 * 13 sur 2 donne 7 + 6. `groupCount` à 0 donne []. */
export function repartirEffectif(total: number, groupCount: number): number[] {
  if (groupCount <= 0) return [];
  const base = Math.floor(total / groupCount);
  const reste = total % groupCount;
  const resultats: number[] = [];
  for (let i = 0; i < groupCount; i += 1) {
    resultats.push(base + (i < reste ? 1 : 0));
  }
  return resultats;
}

/** Présences à l’attachement (lot P5, workflows 2026-11-26) : une case à
 * cocher par joueur de l’équipe attachée. Une map vide = tous présents
 * (toutes les cases cochées par défaut) ; `false` = absent, et le joueur
 * n’est alors réparti dans aucun groupe. Le contrat de séance est
 * inchangé — les validateurs ne lisent que `players`. */
export type Presences = Record<string, boolean>;

/** Les joueurs encore répartis : ceux non marqués absents. */
export function joueursCoches(joueurs: string[], presences: Presences): string[] {
  return joueurs.filter((n) => presences[n] !== false);
}

/** Bascule immuable de la case d’un joueur : un absent récoché redevient
 * présent, un présent décoché devient absent. */
export function basculerPresences(presences: Presences, nom: string): Presences {
  const copie: Presences = { ...presences };
  copie[nom] = copie[nom] !== false;
  return copie;
}

/** Recalcule la répartition depuis la source après une bascule (P5) :
 *  - mode nommé (`groupesSource`, préremplissage page « club ») : le groupe
 *    i reçoit les joueurs du groupe i de la source, filtrés sur les cochés —
 *    le joueur absent disparaît de SON groupe seulement, et la récoche le
 *    ramène dans le sien ; les groupes ajoutés au-delà de la source (via
 *    addGroup) sont laissés intacts ;
 *  - mode plat (attachement direct) : les joueurs cochés sont redistribués
 *    en round-robin, comme à l’attachement.
 * Le nom des groupes et le reste de la structure sont préservés — seules
 * `players` et `joueurs` sont mutées. */
export function redistribuerPresences(
  groups: SessionGroup[],
  joueursEquipe: string[],
  presences: Presences,
  groupesSource: GroupeEquipe[] | null,
): SessionGroup[] {
  if (groupesSource !== null) {
    return groups.map((g, i) => {
      const ge = groupesSource[i];
      if (!ge) return g;
      const r = joueursCoches(ge.joueurs, presences);
      const copie: SessionGroup = { ...g, players: r.length };
      copie.joueurs = r.length > 0 ? r : undefined;
      return copie;
    });
  }
  const parGroupe = roundRobinJoueurs(
    joueursCoches(joueursEquipe, presences),
    groups.map((g) => g.id),
  );
  return groups.map((g) => {
    const r = parGroupe[g.id] ?? [];
    const copie: SessionGroup = { ...g, players: r.length };
    copie.joueurs = r.length > 0 ? r : undefined;
    return copie;
  });
}
