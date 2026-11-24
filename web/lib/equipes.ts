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
