"""Bibliothèque locale Rugby U8. Python standard uniquement."""
import argparse
import csv
import html
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
    query = [(k,v) for k,v in parse_qsl(p.query) if not k.startswith("utm_") and k not in ("ft", "p")]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), urlencode(sorted(query)), ""))

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
            db.execute("INSERT INTO sources VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET url=excluded.url,data=excluded.data",
                       (source["id"],source["url"],json.dumps(source,ensure_ascii=False)))
        for exercise in payload["exercises"]:
            for key in ("id","source_id","title","locator","summary","age_source","theme","review"):
                if not exercise.get(key):
                    raise ValueError("Exercice: champ manquant " + key)
            for key in ("duration_min","players_min","players_max"):
                value = exercise.get(key)
                if value is not None and (type(value) is not int or value <= 0):
                    raise ValueError(key + ": entier positif ou null requis")
            low, high = exercise.get("players_min"), exercise.get("players_max")
            if low is not None and high is not None and low > high:
                raise ValueError("Effectif incohérent")
            db.execute("INSERT INTO exercises VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET source_id=excluded.source_id,locator=excluded.locator,data=excluded.data",
                       (exercise["id"],exercise["source_id"],exercise["locator"],json.dumps(exercise,ensure_ascii=False)))

def search(db, query="", theme="", age="", minutes=None, players=None):
    results = []
    for row in db.execute("SELECT e.data,s.data AS source FROM exercises e JOIN sources s ON s.id=e.source_id ORDER BY e.id"):
        item = json.loads(row["data"])
        item["source"] = json.loads(row["source"])
        haystack = fold(" ".join(str(item.get(k,"")) for k in ("title","summary","theme","adaptation_u8","material")))
        if any(term not in haystack for term in fold(query).split()):
            continue
        if theme and fold(theme) != fold(item["theme"]):
            continue
        if age and fold(age) != fold(item["age_source"]):
            continue
        if minutes is not None and (item.get("duration_min") is None or item["duration_min"] > minutes):
            continue
        if players is not None and (item.get("players_min") is None or item.get("players_max") is None or not item["players_min"] <= players <= item["players_max"]):
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
                  e["summary"], "", "**Matériel :** " + e.get("material","Non renseigné"),
                  "", "**Durée atelier :** " + (str(e.get("duration_min")) + " min" if e.get("duration_min") else "Non renseignée"),
                  "", "**Effectif :** " + (f"{e['players_min']}–{e['players_max']}" if e.get("players_min") and e.get("players_max") else "Non renseigné"),
                  "", "**Adaptation U8 proposée :** " + (e.get("adaptation_u8") or "Aucune rédigée."),
                  "", f"[Source : {s['publisher']}]({s['url']}) — {e['locator']} · consultée le {s['checked_on']}",
                  "", "**Accès :** " + s["access"], ""]
    lines += ["## Répertoire des sources", ""]
    for s in sources:
        lines += [f"- [{s['title']}]({s['url']}) — {s['access']}. {s.get('note','')}"]
    return "\n".join(lines) + "\n"

def export(db, directory):
    directory = Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    items = search(db)
    sources = [json.loads(r[0]) for r in db.execute("SELECT data FROM sources ORDER BY id")]
    (directory/"catalogue.json").write_text(json.dumps({"sources":sources,"exercises":items},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (directory/"CATALOGUE.md").write_text(markdown(items,sources),encoding="utf-8")
    with (directory/"exercises.csv").open("w",encoding="utf-8-sig",newline="") as f:
        columns = ["id","title","theme","age_source","duration_min","players_min","players_max","summary","material","adaptation_u8","review","url","locator"]
        writer = csv.DictWriter(f,fieldnames=columns,extrasaction="ignore")
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
                items = search(db,args.query,args.theme,args.age,args.minutes,args.players)
                for e in items:
                    print(e["id"]+" | "+e["title"]+" | "+e["age_source"]+"\n  "+e["source"]["url"])
                print(f"{len(items)} résultat(s). Les filtres durée/effectif excluent les valeurs inconnues.")
            elif args.command == "export":
                print(f"{export(db,args.out)} fiches exportées dans {args.out}")
            else:
                for table in ("sources","exercises"):
                    print(table + ": " + str(db.execute("SELECT COUNT(*) FROM "+table).fetchone()[0]))
    except (ValueError,KeyError,sqlite3.Error,OSError) as error:
        p.exit(1,"Erreur : "+str(error)+"\n")

if __name__ == "__main__":
    main()
