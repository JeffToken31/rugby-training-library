# Enrichissement et provenance

## Résultat
Quatre fiches enrichies : premières passes en ligne, passes latérales par trois, rappel de défenseurs par couleur et quatre contre un. Objectifs, organisation, déroulement, consignes et, lorsque disponibles, erreurs ou critères de réussite sont séparés et affichés.

La base reste à 60 fiches. Quatre pages HTML sont désormais conservées localement avec leur texte extrait. Les détails éditoriaux sont issus des descriptions et sous-titres consultés ; pas d'observation vidéo ni de timestamp inventé.

## Données et code
enrichments.py conserve un complément attribué dans une table séparée, sans réécrire les lots d'origine. data/enrichment-details.json permet de le reconstruire après les imports historiques :

```sh
python3 catalogue_v2.py enrich data/enrichment-details.json
python3 catalogue_v2.py export
```

Chaque complément indique variante, source, passage, date, auteur et état par champ. PRESENT, NOT_STATED, NOT_EXTRACTED, BLOCKED et CONFLICTING sont distingués. SOURCE et AI_INFERRED sont séparés ; ce chemin ne permet pas d'attribuer une validation coach.

NOT_STATED signifie absent du texte examiné, pas nécessairement de la vidéo entière. Les champs historiques non réexaminés sont marqués LEGACY_UNREVIEWED lorsqu'ils sont présents : leur provenance précise reste à auditer.

La recherche utilise les rubriques détaillées. Les exports JSON incluent les états de couverture. Le Markdown affiche les détails et signale les critères proposés par l'IA.

## Protection et limites
Un réimport identique ne double pas les compléments. Un conflit avec une valeur historique est refusé. Une autre révision du même complément est refusée : la gestion de plusieurs révisions attribuées reste à implémenter. Aucune fusion de variantes.

Les captures locales sont indépendantes des lots éditoriaux : les relier à chaque assertion par empreinte reste à faire. Les premiers états de couverture ne signifient pas que toutes les 60 fiches sont auditées.

29 tests passent, notamment absence d'écrasement, refus des sources incohérentes, annulation d'un lot invalide, recherche des consignes et affichage de l'origine IA.
