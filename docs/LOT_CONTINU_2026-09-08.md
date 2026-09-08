# Collecte et enrichissement continu — 8 septembre 2026

## Données

70 fiches, dont 61 documentées et 9 incomplètes. 34 disposent d’au moins un champ enrichi ; 48 ressources sont référencées, 40 ont une capture locale. Le nombre de révisions n’augmente pas le nombre de fiches enrichies.

Ajouts : course autour des bases contre trois passes (Rugby Rounders) ; réception et passe, puis slalom au pied, depuis le guide FFR M8 saison 2022-2023 (pages fichier 24 et 26). Le guide est consultable par la recherche documentaire mais son archivage local est interdit par robots.txt ; aucune capture n’est revendiquée. Ce guide de validation n’est pas transformé en séance ni considéré comme un règlement actuel.

Quatre fiches de coopération et coordination sont enrichies depuis les sous-titres déjà archivés. Les progressions voisines restent séparées de la situation décrite. L’accès à Rugby Rounders, précédemment en échec, a réussi.

## Amélioration de la reprise

Une fiche peut désormais recevoir plusieurs enrichissements successifs. Chaque révision indique la précédente (`supersedes`) et un motif (`revision_reason`). Les champs absents de la révision gardent leur valeur et leur provenance antérieures. L’historique n’est jamais écrasé. Une branche concurrente ou une référence à une version qui n’est plus la dernière est refusée. Une proposition IA ne remplace pas une information source. Les corrections des données du lot historique restent refusées : elles nécessitent encore un mécanisme distinct.

Le JSON exporté expose l’historique et la provenance par champ. La première application réelle ajoute un critère de réussite au jeu de passes sur appel. Une reconstruction répétée conserve les deux versions.

35 tests couvrent notamment la conservation des anciennes versions, le refus de remplacement d’un fait source par une proposition IA et le retrait d’un critère sans ancienne valeur résiduelle à l’affichage.

## Découvertes à examiner

La série Aviva Minis de l’IRFU annonce 30 jeux vidéo. Les titres seuls ne sont pas importés comme exercices. La page du comité de l’Orne comporte un lien nommé guide M8 qui pointe en fait vers un tableur : ne pas l’ingérer comme PDF. Les pages de règlements ne sont pas comptées comme situations d’entraînement.

## Suite

Poursuivre les sources U8 exploitables et l’enrichissement ; conserver la richesse des champs et leur provenance. La bibliothèque reste partielle et l’interface coach reste à construire. L’utilisateur demande de ne solliciter que lorsqu’une intervention est nécessaire.
