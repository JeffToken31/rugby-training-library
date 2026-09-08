"""Import de transition vers le modèle v2, sans modifier la base historique."""
import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
import library
import enrichments

ROOT=Path(__file__).resolve().parent
def dump(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True)
def connect(path):
    db=sqlite3.connect(path)
    db.row_factory=sqlite3.Row
    db.executescript((ROOT/"schema/v2.sql").read_text())
    db.executescript("""
    CREATE TABLE IF NOT EXISTS import_snapshots(
      sha256 TEXT PRIMARY KEY, payload_json TEXT NOT NULL CHECK(json_valid(payload_json)));
    CREATE TABLE IF NOT EXISTS session_item_variants(
      item_id TEXT REFERENCES session_exercises(id), variant_id TEXT REFERENCES variants(id),
      PRIMARY KEY(item_id,variant_id));
    """)
    enrichments.schema(db)
    return db
def put(db,table,row,key="id"):
    old=db.execute("SELECT * FROM "+table+" WHERE "+key+"=?",(row[key],)).fetchone()
    if old:
        if any(old[k]!=v for k,v in row.items()):
            raise ValueError("Révision explicite nécessaire : "+table+"/"+str(row[key]))
        return
    cols=list(row)
    db.execute("INSERT INTO "+table+" ("+",".join(cols)+") VALUES ("+",".join("?" for _ in cols)+")",list(row.values()))
def occurrence(db,id,source,locator,page_start=None,page_end=None):
    put(db,"occurrences",dict(id=id,resource_id=source,locator_text=locator,page_start=page_start,page_end=page_end))
def ingest(db,payload):
    with db:
        raw=dump(payload)
        put(db,"import_snapshots",dict(sha256=hashlib.sha256(raw.encode()).hexdigest(),payload_json=raw),"sha256")
        for s in payload.get("sources",[]):
            put(db,"resources",dict(id=s["id"],url=library.canonical(s["url"]),provider_key=library.source_identity(s["url"]),title=s["title"],format=s.get("format"),metadata_json=dump(s)))
            if s.get("resource_type"):
                put(db,"qualifications",dict(id=s["id"]+":type",resource_id=s["id"],type=s["resource_type"],strategy=s.get("qualification_note"),actor="assistant",created_at=s["checked_on"]))
        for f in payload.get("families",[]):
            put(db,"families",dict(id=f["id"],title=f["title"],description=f.get("description"),metadata_json=dump({"origin":"AI_INFERRED"})))
        for e in payload.get("exercises",[]):
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*",e["id"]):
                raise ValueError("Identifiant exercice invalide")
            status="AI_PARSED" if e.get("status")=="incomplete" else "REVIEWED"
            put(db,"variants",dict(id=e["id"],family_id=e.get("family_id"),title=e["title"],origin="SOURCE",status=status,parent_variant_id=e.get("parent_variant_id"),parameters_json=dump(e)))
            occ=e["id"]+":main"
            occurrence(db,occ,e["source_id"],e["locator"],e.get("page_start"),e.get("page_end"))
            db.execute("INSERT OR IGNORE INTO exercise_sources VALUES(?,?,?,?)",(e["id"],occ,"description",None))
            for i,r in enumerate(e.get("references",[])):
                rid=e["id"]+":ref:"+str(i)
                occurrence(db,rid,r["source_id"],r["locator"])
                db.execute("INSERT OR IGNORE INTO exercise_sources VALUES(?,?,?,?)",(e["id"],rid,"related",r["summary"]))
            # Retain proposed settings on the variant; do not inflate variant count.
            for field in ("duration_min","players_min","players_max","space","bout_seconds","material","summary","title","theme","age_source","u8_plan","adaptation_u8"):
                value=e.get(field)
                if value is None:
                    continue
                origin="AI_INFERRED" if field in ("title","theme","u8_plan","adaptation_u8") else "SOURCE"
                put(db,"assertions",dict(id=e["id"]+":"+field,variant_id=e["id"],field_path=field,value_json=dump(value),origin=origin,occurrence_id=occ if origin=="SOURCE" else None,actor="assistant",created_at="2026-09-07",selected=1))
            theme=e.get("theme")
            if theme:
                tag="theme:"+theme
                put(db,"tags",dict(id=tag,category="theme",label=theme))
                db.execute("INSERT OR IGNORE INTO variant_tags VALUES(?,?)",(e["id"],tag))
        for session in payload.get("sessions",[]):
            occ=session["id"]+":source"
            occurrence(db,occ,session["source_id"],session["locator"],session.get("page_start"),session.get("page_end"))
            put(db,"sessions",dict(id=session["id"],title=session["title"],origin=session["origin"],occurrence_id=occ,parameters_json=dump(session)))
            for i,item in enumerate(session["items"]):
                id=session["id"]+":"+str(i)
                duration=item.get("duration_min")*60 if item.get("duration_min") is not None and item.get("duration_min")==item.get("duration_max") else None
                put(db,"session_exercises",dict(id=id,session_id=session["id"],position=i,kind=item["kind"],duration_seconds=duration,parameters_json=dump(item)))
                for v in item.get("variant_ids",[]):
                    db.execute("INSERT OR IGNORE INTO session_item_variants VALUES(?,?)",(id,v))
        for c in payload.get("duplicate_candidates",[]):
            put(db,"duplicate_candidates",c)
def items(db,query="",status="",theme="",age="",minutes=None,players=None,basis="source",material="",sort="title",has_fields=(),field_origin=None,provider=""):
    if basis not in ("source","proposal") or sort not in ("title","duration","players"):
        raise ValueError("Filtre inconnu")
    if any(x is not None and (type(x) is not int or x<=0) for x in (minutes,players)):
        raise ValueError("Durée et effectif doivent être des entiers positifs")
    if any(field not in enrichments.FIELDS for field in has_fields):
        raise ValueError("Champ de couverture inconnu")
    if field_origin not in (None,"SOURCE","AI_INFERRED","COACH_VALIDATED","LEGACY_UNREVIEWED"):
        raise ValueError("Origine de champ inconnue")
    if field_origin and not has_fields:
        raise ValueError("L’origine exige au moins un champ")
    result=[]
    sources={r["id"]:json.loads(r["metadata_json"]) for r in db.execute("SELECT * FROM resources")}
    for row in db.execute("SELECT * FROM variants ORDER BY id"):
        if status and row["status"]!=status:
            continue
        e=enrichments.overlay(db,json.loads(row["parameters_json"]))
        if provider and library.fold(provider) not in library.fold(sources[e["source_id"]].get("publisher", "")):
            continue
        if any(e["field_coverage"][field]["state"]!="PRESENT" or (field_origin and e["field_coverage"][field].get("origin")!=field_origin) for field in has_fields):
            continue
        haystack=" ".join(str(e.get(k) or "") for k in ("title","summary","theme","age_source","material","space","coach_points","adaptation_u8","u8_plan","objectives","organisation","steps","instructions","success_criteria","common_errors"))
        if any(w not in library.fold(haystack) for w in library.fold(query).split()):
            continue
        if theme and library.fold(e.get("theme",""))!=library.fold(theme):
            continue
        if age and library.fold(age) not in library.fold(e.get("age_source","")):
            continue
        if material and library.fold(material) not in library.fold(e.get("material") or ""):
            continue
        params=e if basis=="source" else (e.get("u8_plan") or {})
        duration=params.get("duration_min")
        low,high=params.get("players_min"),params.get("players_max")
        if minutes is not None and (duration is None or duration>minutes):
            continue
        if players is not None and (low is None or high is None or not low<=players<=high):
            continue
        e["source"]=sources[e["source_id"]]
        e["model_status"]=row["status"]
        e["material"]=e.get("material") or "Non renseigné"
        e["references"]=[dict(r,source=sources[r["source_id"]]) for r in e.get("references",[])]
        result.append(e)
    def order(e):
        params=e if basis=="source" else (e.get("u8_plan") or {})
        value=params.get("duration_min" if sort=="duration" else "players_min")
        return (value is None,value or 0,library.fold(e["title"])) if sort!="title" else (library.fold(e["title"]),)
    return sorted(result,key=order)
def export(db,out):
    out=Path(out)
    sources=[json.loads(r[0]) for r in db.execute("SELECT metadata_json FROM resources ORDER BY id")]
    result=items(db)
    library.export(None,out,items_override=result,sources_override=sources)
    lines=["# Séances sources","","Les trames ci-dessous restent distinctes de votre organisation de 90 minutes. Les pistes vidéo incomplètes sont signalées dans les fiches.",""]
    for r in db.execute("SELECT * FROM sessions ORDER BY id"):
        s=json.loads(r["parameters_json"])
        source=next(x for x in sources if x["id"]==s["source_id"])
        lines += ["## "+s["title"],"",s.get("note",""),"",f"[Source]({source['url']}) — {s['locator']}",""]
        for item in s["items"]:
            lo,hi=item.get("duration_min"),item.get("duration_max")
            lines += [f"- {item['label']} : {lo}–{hi} min."]
            for id in item.get("variant_ids",[]):
                lines += [f"  - [Fiche {id}](fiches/{id}.md)"]
        lines += [""]
    (out/"SEANCES.md").write_text("\n".join(lines)+"\n")
    selected=[e for e in result if all(e["field_coverage"][field]["state"]=="PRESENT" and e["field_coverage"][field].get("origin")=="SOURCE" for field in ("organisation","steps"))]
    selection=["# Fiches avec organisation et déroulement sourcés", "", "Cette sélection exige ces deux champs attribués à une source. Elle ne vaut pas validation terrain ni garantie de complétude. Les durées et effectifs peuvent rester inconnus.", "", str(len(selected))+" fiches.", ""]
    for e in selected:
        selection.append("- ["+e["title"]+"](fiches/"+e["id"]+".md) — "+e["theme"]+" ; "+e["source"].get("publisher", "Organisme non renseigné"))
    (out/"FICHES_DETAILLEES.md").write_text("\n".join(selection)+"\n",encoding="utf-8")
    import comparisons
    comparisons.export(db,out,result)
    return len(result)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",type=Path,default=ROOT/"data/rugby-v2.sqlite")
    sub=p.add_subparsers(dest="cmd",required=True)
    q=sub.add_parser("import"); q.add_argument("files",nargs="+",type=Path)
    q=sub.add_parser("enrich"); q.add_argument("file",type=Path)
    q=sub.add_parser("search"); q.add_argument("query",nargs="?",default=""); q.add_argument("--status",default="")
    q.add_argument("--theme",default="")
    q.add_argument("--age",default="",help="Texte dans l'âge source, pas validation U8")
    q.add_argument("--minutes",type=int,help="Durée totale maximale connue")
    q.add_argument("--players",type=int)
    q.add_argument("--basis",choices=("source","proposal"),default="source")
    q.add_argument("--material",default="")
    q.add_argument("--has-field",action="append",choices=enrichments.FIELDS,default=[],help="Champ présent requis ; répétable")
    q.add_argument("--field-origin",choices=("SOURCE","AI_INFERRED","COACH_VALIDATED","LEGACY_UNREVIEWED"),help="Origine exigée pour chacun des champs requis")
    q.add_argument("--provider",default="",help="Texte dans le nom de l’organisme principal")
    q.add_argument("--sort",choices=("title","duration","players"),default="title")
    q=sub.add_parser("export"); q.add_argument("--out",type=Path,default=ROOT/"exports")
    sub.add_parser("stats")
    a=p.parse_args()
    with connect(a.db) as db:
        if a.cmd=="import":
            for path in a.files:
                ingest(db,json.loads(path.read_text()))
            print("Import v2 terminé ; historique conservé.")
        elif a.cmd=="enrich":
            enrichments.ingest(db,json.loads(a.file.read_text()))
            print("Enrichissement conservé sans modifier les lots historiques.")
        elif a.cmd=="search":
            found=items(db,a.query,a.status,a.theme,a.age,a.minutes,a.players,a.basis,a.material,a.sort,a.has_field,a.field_origin,a.provider)
            for e in found:
                print(e["id"]+" | "+e["title"]+" | "+e["model_status"])
            print(str(len(found))+" résultat(s). Paramètres : "+a.basis+". Les inconnues sont exclues des filtres numériques.")
        elif a.cmd=="export":
            print(str(export(db,a.out))+" fiches exportées.")
        else:
            for t in ("resources","variants","sessions","occurrences","duplicate_candidates"):
                print(t,db.execute("SELECT COUNT(*) FROM "+t).fetchone()[0])
if __name__=="__main__":
    main()
