"""Exécution reproductible du lot : import, enrichissement, captures, contrôles, exports."""
import argparse
import json
import time
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import urlsplit
import catalogue_v2 as v2
import capture_resources as captures
import enrichments

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))
def run(db,manifest,root,out,collect=False,limit=12):
    root=Path(root); out=Path(out)
    events=[]
    for name in manifest["data"]:
        v2.ingest(db,read(root/name))
    for name in manifest["enrichments"]:
        enrichments.ingest(db,read(root/name))
    if collect:
        blocked=set()
        cutoff=(datetime.now(timezone.utc)-timedelta(hours=24)).isoformat()
        for id in manifest.get("capture_resources",[])[:limit]:
            source=db.execute("SELECT url FROM resources WHERE id=?",(id,)).fetchone()
            if source is None:
                events.append({"resource_id":id,"state":"FAILED","error":"Ressource inconnue"})
                continue
            host=urlsplit(source[0]).netloc
            recent=db.execute("SELECT 1 FROM ingestion_runs WHERE resource_id=? AND state='BLOCKED' AND started_at>? LIMIT 1",(id,cutoff)).fetchone()
            if host in blocked or recent:
                events.append({"resource_id":id,"state":"DEFERRED","error":"Blocage récent ; autre source priorisée"})
                continue
            result=captures.capture(db,id,root/"data/raw")
            if result["state"] in ("DONE","REUSED"):
                try:
                    captures.extract_html(db,result["capture_id"])
                except (OSError,ValueError) as error:
                    result["extraction_error"]=str(error)
            if result["state"]=="BLOCKED":
                blocked.add(host)
            events.append(result)
            print(id+" : "+result["state"],flush=True)
            if result["state"]!="REUSED":
                time.sleep(0.5)
    if db.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("Références incohérentes : export annulé")
    count=v2.export(db,out)
    items=v2.items(db)
    report={
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "variants":count,
        "documented":sum(e["model_status"]=="REVIEWED" for e in items),
        "incomplete":sum(e["model_status"]=="AI_PARSED" for e in items),
        "enriched":db.execute("SELECT COUNT(*) FROM enrichments").fetchone()[0],
        "resources":db.execute("SELECT COUNT(*) FROM resources").fetchone()[0],
        "captured_resources":db.execute("SELECT COUNT(DISTINCT resource_id) FROM captures").fetchone()[0],
        "families":db.execute("SELECT COUNT(*) FROM families").fetchone()[0],
        "events":events}
    (out/"ETAT_COLLECTE.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    lines=["# État de la bibliothèque","",f"{count} fiches ; {report['documented']} documentées ; {report['incomplete']} incomplètes.",
        f"{report['enriched']} fiches enrichies ; {report['resources']} ressources ; {report['captured_resources']} ressources capturées localement.",
        "", "Une fiche documentée n'est pas nécessairement exhaustive ni validée par un coach.",
        "Les captures restent locales et ne sont pas incluses dans GitHub.","","## Couverture des champs","","| Champ | Présent | Non extrait | Non indiqué | Bloqué | Contradictoire |","|---|---:|---:|---:|---:|---:|"]
    for field in enrichments.FIELDS:
        states=[e["field_coverage"].get(field,{"state":"NOT_EXTRACTED"})["state"] for e in items]
        lines.append("| "+field+" | "+" | ".join(str(states.count(state)) for state in ("PRESENT","NOT_EXTRACTED","NOT_STATED","BLOCKED","CONFLICTING"))+" |")
    lines += ["","Les valeurs historiques présentes peuvent ne pas encore avoir été réexaminées champ par champ.","","## Tentatives de ce lot",""]
    lines += ["- "+e["resource_id"]+" : "+e["state"]+(" — "+e["error"] if e.get("error") else "") for e in events]
    if not events:
        lines+=["Reconstruction sans nouvelle collecte réseau."]
    (out/"ETAT_COLLECTE.md").write_text("\n".join(lines)+"\n")
    return report
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,default=v2.ROOT/"data/manifest.json")
    p.add_argument("--db",type=Path,default=v2.ROOT/"data/rugby-v2.sqlite")
    p.add_argument("--out",type=Path,default=v2.ROOT/"exports")
    p.add_argument("--collect",action="store_true")
    p.add_argument("--limit",type=int,default=12)
    a=p.parse_args()
    if a.limit<0:
        p.error("Limite positive ou nulle requise")
    with v2.connect(a.db) as db:
        report=run(db,read(a.manifest),v2.ROOT,a.out,a.collect,a.limit)
    print(json.dumps({k:v for k,v in report.items() if k!="events"},ensure_ascii=False))
if __name__=="__main__":
    main()
