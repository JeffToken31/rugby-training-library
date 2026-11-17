# Rugby Training Library

Le projet vise une application web pensée d’abord pour le téléphone des éducateurs de rugby, avec les U8 comme première cible. Le socle actuel reconstruit le catalogue et expose ses données. Deux usages guident le MVP :

1. Trouver rapidement un atelier dans le catalogue, puis consulter sa fiche et ses médias.
2. Préparer une séance par blocs, l’enregistrer en brouillon, la partager et pouvoir en proposer une variante.

La trame U8 de référence prévoit environ 70 minutes sur un créneau de 90 minutes, avec environ 50 minutes d’opposition et deux ateliers sur environ 20 minutes au total. Les quelque 20 minutes restantes constituent une marge de terrain volontaire. L’éducateur peut adapter la trame.

## Documents de référence

| Besoin | Document |
| --- | --- |
| Périmètre, catalogue et règles produit | [Périmètre produit](docs/PRODUCT_SCOPE.md) |
| Parcours et calcul du temps dans le constructeur | [Interface des séances](docs/INTERFACE_SEANCES.md) |
| Arbitrages et questions ouvertes | [Journal des décisions](docs/DECISIONS.md) |
| Données exposées et contrôles existants | [Contrat de lecture application](docs/CONTRAT_APPLICATION.md) |

En cas de contradiction avec un document historique, la documentation active référencée ici prévaut. Le périmètre et l’interface décrivent le **produit visé**. Le contrat décrit le **socle actuel** et sa représentation du créneau.

Le MVP s’arrête à la bibliothèque et à la préparation de séances. L’assistance IA est une évolution envisagée. La gestion des enfants, des parents, des clubs et de la saison est hors périmètre.

## Catalogue, travail local et historique

- [Catalogue à consulter](exports/CATALOGUE.md) et [guide de reconstruction](README.md).
- [Consignes de contribution](AGENTS.md).
- [Inventaire documentaire et archives](archive/README.md), avec l’origine et le statut des anciens documents.

Les entrées du catalogue sont ordonnées dans le [manifeste](data/manifest.json). Le catalogue Markdown et le JSON de lecture sont générés. Le manifeste et les données versionnées portent la provenance des fiches.
