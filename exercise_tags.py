"""Classement éditorial multi-tags, indépendant des familles et des doublons."""
import argparse
import json
from pathlib import Path

def attach(payload, taxonomy):
    definitions = {t["id"]:t for t in taxonomy["tags"]}
    assignments = {a["variant_id"]:a for a in taxonomy["assignments"]}
    ids = {e["id"] for e in payload["exercises"]}
    if len(definitions) != len(taxonomy["tags"]) or len(assignments) != len(taxonomy["assignments"]):
        raise ValueError("Tag ou affectation répété")
    if set(assignments) != ids:
        raise ValueError("Couverture des tags différente du corpus")
    for e in payload["exercises"]:
        a = assignments[e["id"]]
        tags = a["tag_ids"]
        if not tags or len(tags) != len(set(tags)) or set(tags) - set(definitions):
            raise ValueError("Tags invalides : " + e["id"])
        if not any(definitions[t]["dimension"] == "skill" for t in tags):
            raise ValueError("Compétence absente : " + e["id"])
        if a["origin"] != "AI_INFERRED" or a["status"] not in ("PROVISIONAL", "EDITORIAL_REVIEWED"):
            raise ValueError("Provenance de classement invalide")
        if e["quality"]["state"] == "INCOMPLETE" and a["status"] != "PROVISIONAL":
            raise ValueError("Fiche incomplète classée sans réserve")
        e["tag_ids"] = tags
        e["tagging"] = a
    payload["tag_taxonomy"] = {k:v for k,v in taxonomy.items() if k != "assignments"}

def select(payload, tag_ids=(), match="all", include_incomplete=False):
    known = {t["id"] for t in payload["tag_taxonomy"]["tags"]}
    wanted = set(tag_ids)
    if wanted - known or match not in ("all", "any"):
        raise ValueError("Filtre inconnu")
    return [e for e in payload["exercises"]
            if (include_incomplete or e["quality"]["default_visible"])
            and (not wanted or (wanted <= set(e["tag_ids"]) if match == "all" else bool(wanted & set(e["tag_ids"]))))]

def export(payload, out):
    lines = ["# Exercices par compétence et forme de jeu", "", "Une fiche peut apparaître dans plusieurs catégories : son identifiant reste unique. Les sommes par catégorie ne s’additionnent pas pour compter les exercices.", "", "Classement éditorial proposé, sans validation coach. † = description insuffisante, classement provisoire. L’absence d’un tag ne prouve pas l’absence d’une compétence. Aucun niveau de contact n’est déduit.", ""]
    for dimension, label in (("skill", "Compétences"), ("format", "Formes de jeu")):
        lines += ["## " + label, ""]
        for tag in payload["tag_taxonomy"]["tags"]:
            if tag["dimension"] != dimension:
                continue
            matches = select(payload, [tag["id"]], include_incomplete=True)
            lines += [f"### {tag['label']} ({len(matches)})", ""]
            for e in sorted(matches, key=lambda e:e["title"]):
                flag = " †" if e["tagging"]["status"] == "PROVISIONAL" else ""
                lines.append(f"- [{e['title']}](fiches/{e['id']}.md){flag}")
            lines += [""]
    Path(out, "CATEGORIES.md").write_text("\n".join(lines), encoding="utf-8")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tags", nargs="*")
    parser.add_argument("--match", choices=("all", "any"), default="all")
    parser.add_argument("--include-incomplete", action="store_true")
    args = parser.parse_args()
    payload = json.loads((Path(__file__).resolve().parent / "exports/APPLICATION.json").read_text())
    try:
        rows = select(payload, args.tags, args.match, args.include_incomplete)
    except ValueError as error:
        parser.error(str(error))
    for e in rows:
        print(e["id"] + " — " + e["title"])
    print(str(len(rows)) + " fiche(s), sans duplication.")

if __name__ == "__main__":
    main()
