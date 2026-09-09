"""Bibliothèque locale Rugby U8. Python standard uniquement."""
import argparse
import csv
import re
import json
import sqlite3
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

ROOT = Path(__file__).resolve().parent

def fold(value):
    return "".join(c for c in unicodedata.normalize("NFKD", str(value)).lower() if not unicodedata.combining(c))

def canonical(url):
    p = urlsplit(url)
    if p.scheme not in ("https", "http") or not p.netloc or p.username or p.password:
        raise ValueError("URL publique HTTP(S) requise")
    query = [(k,v) for k,v in parse_qsl(p.query) if not k.startswith("utm_") and not (p.hostname == "www.rugbycoaching.tv" and k in ("ft", "p"))]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), urlencode(sorted(query)), ""))

def source_identity(url):
    p = urlsplit(url)
    if p.hostname == "www.rugbycoaching.tv":
        match = re.search(r"/(\d{8})/?$", p.path)
        if match:
            return p.hostname + ":" + match[1]
    return canonical(url)

def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS sources(
      id TEXT PRIMARY KEY, url TEXT NOT NULL UNIQUE, data TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS exercises(
      id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(id),
      locator TEXT NOT NULL, data TEXT NOT NULL,
      UNIQUE(source_id,locator));
    CREATE TABLE IF NOT EXISTS exercise_references(
      exercise_id TEXT NOT NULL REFERENCES exercises(id),
      source_id TEXT NOT NULL REFERENCES sources(id),
      locator TEXT NOT NULL, summary TEXT NOT NULL,
      PRIMARY KEY(exercise_id,source_id,locator));
    """)
    return db

def ingest(db, payload):
    # One transaction: a bad record rolls back the entire import.
    with db:
        for source in payload["sources"]:
            for key in ("id","title","url","publisher","checked_on","access"):
                if not source.get(key):
                    raise ValueError("Source: champ manquant " + key)
            source = dict(source, url=canonical(source["url"]))
            for existing in db.execute("SELECT id,url FROM sources WHERE id != ?", (source["id"],)):
                if source_identity(existing["url"]) == source_identity(source["url"]):
                    raise ValueError("Source déjà présente sous " + existing["id"])
            db.execute("INSERT INTO sources VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET url=excluded.url,data=excluded.data",
                       (source["id"],source["url"],json.dumps(source,ensure_ascii=False)))
        for exercise in payload["exercises"]:
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", str(exercise.get("id", ""))):
                raise ValueError("Identifiant exercice invalide")
            for key in ("id","source_id","title","locator","summary","age_source","theme","review"):
                if not exercise.get(key):
                    raise ValueError("Exercice: champ manquant " + key)
            for key in ("duration_min","players_min","players_max"):
                value = exercise.get(key)
                if value is not None and (type(value) is not int or value <= 0):
                    raise ValueError(key + ": entier positif ou null requis")
            if exercise.get("status", "documented") not in ("documented", "incomplete"):
                raise ValueError("Statut inconnu")
            plan = exercise.get("u8_plan")
            if plan:
                for key in ("duration_min", "players_min", "players_max"):
                    if type(plan.get(key)) is not int or plan[key] <= 0:
                        raise ValueError("Proposition U8 : " + key + " invalide")
                if plan["players_min"] > plan["players_max"]:
                    raise ValueError("Effectif proposé incohérent")
                for key in ("setup", "steps", "coach", "easier", "harder"):
                    if not isinstance(plan.get(key), str) or not plan[key].strip():
                        raise ValueError("Proposition U8 : " + key + " manquant")
            low, high = exercise.get("players_min"), exercise.get("players_max")
            if low is not None and high is not None and low > high:
                raise ValueError("Effectif incohérent")
            db.execute("INSERT INTO exercises VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET source_id=excluded.source_id,locator=excluded.locator,data=excluded.data",
                       (exercise["id"],exercise["source_id"],exercise["locator"],json.dumps(exercise,ensure_ascii=False)))
            db.execute("DELETE FROM exercise_references WHERE exercise_id=?", (exercise["id"],))
            for ref in exercise.get("references", []):
                if not ref.get("locator") or not ref.get("summary"):
                    raise ValueError("Référence complémentaire incomplète")
                db.execute("INSERT INTO exercise_references VALUES(?,?,?,?)",
                           (exercise["id"], ref["source_id"], ref["locator"], ref["summary"]))

def search(db, query="", theme="", age="", minutes=None, players=None, basis="source", status=""):
    if basis not in ("source", "proposal"):
        raise ValueError("Base de filtrage inconnue")
    results = []
    for row in db.execute("SELECT e.data,s.data AS source FROM exercises e JOIN sources s ON s.id=e.source_id ORDER BY e.id"):
        item = json.loads(row["data"])
        item["source"] = json.loads(row["source"])
        item["references"] = [
            {"source": json.loads(r["data"]), "source_id": r["source_id"], "locator": r["locator"], "summary": r["summary"]}
            for r in db.execute("SELECT r.source_id,r.locator,r.summary,s.data FROM exercise_references r JOIN sources s ON s.id=r.source_id WHERE r.exercise_id=?", (item["id"],))
        ]
        if status and item.get("status", "documented") != status:
            continue
        parameters = item if basis == "source" else item.get("u8_plan", {})
        haystack = fold(" ".join(str(item.get(k,"")) for k in ("title","summary","theme","adaptation_u8","material","u8_plan")))
        if any(term not in haystack for term in fold(query).split()):
            continue
        if theme and fold(theme) != fold(item["theme"]):
            continue
        if age and fold(age) != fold(item["age_source"]):
            continue
        if minutes is not None and (parameters.get("duration_min") is None or parameters["duration_min"] > minutes):
            continue
        if players is not None and (parameters.get("players_min") is None or parameters.get("players_max") is None or not parameters["players_min"] <= players <= parameters["players_max"]):
            continue
        results.append(item)
    return results

def markdown(items, sources):
    lines = ["# Bibliothèque rugby U8", "", f"{len(items)} fiches · {len(sources)} sources", "",
             "Descriptions reformulées. Validation terrain à faire. Une durée de vidéo n’est pas une durée d’atelier.",
             "Les paramètres non renseignés restent inconnus. Les adaptations sont des propositions distinctes des sources.", ""]
    for e in items:
        s = e["source"]
        lines += [f"## {e['title']}", "", f"**{e['theme']} · âge source : {e['age_source']} · {e['review']}**", "",
                  e["summary"], "", "**Matériel :** " + (e.get("material") or "Non renseigné"),
                  "", "**Durée atelier :** " + (str(e.get("duration_min")) + " min" if e.get("duration_min") else "Non renseignée"),
                  "", "**Effectif :** " + (f"{e['players_min']}–{e['players_max']}" if e.get("players_min") and e.get("players_max") else "Non renseigné") + (" — "+e["participants_scope"] if e.get("participants_scope") else ""),
                  "", "**Adaptation U8 proposée :** " + (e.get("adaptation_u8") or "Aucune rédigée."),
                  "", f"[Source : {s['publisher']}]({s['url']}) — {e['locator']} · consultée le {s['checked_on']}",
                  "", "**Accès :** " + s["access"], ""]
        for key,label in (("objectives","Objectifs"),("organisation","Organisation"),("steps","Déroulement"),("instructions","Consignes"),("success_criteria","Critères de réussite"),("common_errors","Erreurs fréquentes")):
            if e.get(key):
                origin=e.get("field_coverage",{}).get(key,{}).get("origin")
                suffix=" — proposition IA" if origin=="AI_INFERRED" else ""
                provenance=e.get("field_coverage",{}).get(key,{}).get("provenance",{})
                if provenance.get("source_scope"):
                    suffix += " — "+provenance["source_scope"]
                lines += ["**"+label+suffix+" :** "+e[key], ""]
        if e.get("enrichment_provenance"):
            p=e["enrichment_provenance"]
            lines += ["Détails extraits le "+p["checked_on"]+" — "+p["locator"]+".", ""]
        if e.get("coach_points"):
            lines += ["**Points coach issus de la source :** " + e["coach_points"], ""]
        if e.get("space"):
            lines += ["**Espace source :** " + e["space"], ""]
        if e.get("bout_seconds"):
            lines += ["**Manche source :** " + str(e["bout_seconds"]) + " secondes ; durée totale inconnue.", ""]
        if e.get("source_conflicts"):
            lines += ["**Information source contradictoire :** " + "; ".join(c["note"] for c in e["source_conflicts"]), ""]
        if e.get("family_id"):
            lines += ["**Famille proposée :** " + e["family_id"], ""]
        for ref in e.get("references", []):
            lines += ["**Variante sourcée complémentaire :** " + ref["summary"], "",
                      f"[{ref['source']['publisher']}]({ref['source']['url']}) — {ref['locator']}", ""]
        if e.get("u8_plan"):
            plan = e["u8_plan"]
            lines += ["### Proposition terrain U8 — à valider", "",
                      f"{plan['duration_min']} min · {plan['players_min']} à {plan['players_max']} enfants par atelier. Ces chiffres sont proposés, pas extraits de la source.", "",
                      "**Installation :** " + plan["setup"], "", "**Déroulement :** " + plan["steps"],
                      "", "**À observer :** " + plan["coach"], "", "**Plus simple :** " + plan["easier"],
                      "", "**Plus difficile :** " + plan["harder"], ""]
    lines += ["## Répertoire des sources", ""]
    for s in sources:
        lines += [f"- [{s['title']}]({s['url']}) — {s['access']}. {s.get('note','')}"]
    return "\n".join(line.rstrip() for line in lines) + "\n"

def export(db, directory, items_override=None, sources_override=None):
    directory = Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    items = search(db) if items_override is None else items_override
    sources = [json.loads(r[0]) for r in db.execute("SELECT data FROM sources ORDER BY id")] if sources_override is None else sources_override
    (directory/"catalogue.json").write_text(json.dumps({"sources":sources,"exercises":items},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (directory/"CATALOGUE.md").write_text(markdown(items,sources),encoding="utf-8")
    cards = directory/"fiches"
    cards.mkdir(exist_ok=True)
    index = ["# Choisir un exercice", "", f"{len(items)} fiches — les propositions terrain restent à valider par le coach.", "",
             "[Catalogue complet](CATALOGUE.md) · [Séances sources](SEANCES.md) · [Séance exemple](../docs/SEANCE_EXEMPLE.md)", ""]
    for theme in sorted(set(e["theme"] for e in items)):
        index += ["## " + theme.capitalize(), "", "| Exercice | Âge source | Proposition terrain |", "|---|---|---|"]
        for e in (x for x in items if x["theme"] == theme):
            plan = e.get("u8_plan")
            detail = f"{plan['duration_min']} min / {plan['players_min']}–{plan['players_max']} enfants" if plan else ("À compléter" if e.get("status") == "incomplete" else "Documentée ; à valider")
            index += [f"| [{e['title']}](fiches/{e['id']}.md) | {e['age_source']} | {detail} |"]
            (cards/(e["id"]+".md")).write_text(markdown([e],[e["source"]]),encoding="utf-8")
        index.append("")
    (directory/"INDEX.md").write_text("\n".join(index)+"\n",encoding="utf-8")
    with (directory/"exercises.csv").open("w",encoding="utf-8-sig",newline="") as f:
        columns = ["id","title","theme","age_source","duration_min","players_min","players_max","participants_scope","summary","material","adaptation_u8","review","url","locator"]
        writer = csv.DictWriter(f,fieldnames=columns,extrasaction="ignore",lineterminator="\n")
        writer.writeheader()
        for e in items:
            row = dict(e,url=e["source"]["url"])
            for k,v in row.items():
                if isinstance(v,str) and v.startswith(("=","+","-","@")):
                    row[k] = "'" + v
            writer.writerow(row)
    return len(items)

def main():
    p = argparse.ArgumentParser(description="Bibliothèque rugby — import, recherche, export")
    p.add_argument("--db",type=Path,default=ROOT/"data/rugby.sqlite")
    sub = p.add_subparsers(dest="command",required=True)
    imp = sub.add_parser("import")
    imp.add_argument("file",type=Path)
    q = sub.add_parser("search")
    q.add_argument("query",nargs="?",default="")
    q.add_argument("--theme",default="")
    q.add_argument("--age",default="")
    q.add_argument("--minutes",type=int)
    q.add_argument("--players",type=int)
    q.add_argument("--basis",choices=("source","proposal"),default="source",help="Filtrer les chiffres source ou ceux des propositions terrain")
    q.add_argument("--status",choices=("documented","incomplete"),default="")
    out = sub.add_parser("export")
    out.add_argument("--out",type=Path,default=ROOT/"exports")
    sub.add_parser("stats")
    args = p.parse_args()
    try:
        with connect(args.db) as db:
            if args.command == "import":
                ingest(db,json.loads(args.file.read_text(encoding="utf-8")))
                print("Import terminé.")
            elif args.command == "search":
                items = search(db,args.query,args.theme,args.age,args.minutes,args.players,args.basis,args.status)
                for e in items:
                    print(e["id"]+" | "+e["title"]+" | "+e["age_source"]+"\n  "+e["source"]["url"])
                print(f"{len(items)} résultat(s). Base : {args.basis}. Les filtres excluent les valeurs inconnues.")
            elif args.command == "export":
                print(f"{export(db,args.out)} fiches exportées dans {args.out}")
            else:
                for table in ("sources","exercises"):
                    print(table + ": " + str(db.execute("SELECT COUNT(*) FROM "+table).fetchone()[0]))
    except (ValueError,KeyError,sqlite3.Error,OSError) as error:
        p.exit(1,"Erreur : "+str(error)+"\n")

if __name__ == "__main__":
    main()
