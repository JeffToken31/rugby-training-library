"""Enrichissements attribués, séparés des lots historiques."""
import json
import re
import hashlib
from pathlib import Path
FIELDS=("objectives","organisation","steps","instructions","success_criteria","common_errors","coach_points","duration_min","players_min","players_max","space","material")
STATES=("PRESENT","NOT_STATED","NOT_EXTRACTED","BLOCKED","CONFLICTING")
def schema(db):
    db.execute("CREATE TABLE IF NOT EXISTS enrichments(id TEXT PRIMARY KEY, variant_id TEXT NOT NULL REFERENCES variants(id), payload_json TEXT NOT NULL CHECK(json_valid(payload_json)))")
    db.execute("CREATE INDEX IF NOT EXISTS enrichment_variant ON enrichments(variant_id)")
def history(db,variant_id):
    records={r["id"]:json.loads(r["payload_json"]) for r in db.execute("SELECT * FROM enrichments WHERE variant_id=?",(variant_id,))}
    if not records:
        return []
    parents={r.get("supersedes") for r in records.values() if r.get("supersedes")}
    heads=set(records)-parents
    if len(heads)!=1:
        raise ValueError("Historique ambigu")
    chain=[]; key=heads.pop(); seen=set()
    while key:
        if key in seen or key not in records:
            raise ValueError("Historique invalide")
        seen.add(key); record=records[key]; chain.append(record); key=record.get("supersedes")
    if len(seen)!=len(records):
        raise ValueError("Historique incomplet")
    return list(reversed(chain))

def ingest(db,payload):
    with db:
        for record in payload["enrichments"]:
            row=db.execute("SELECT parameters_json FROM variants WHERE id=?",(record["variant_id"],)).fetchone()
            if row is None:
                raise ValueError("Variante inconnue")
            original=json.loads(row[0])
            if original["source_id"]!=record["source_id"]:
                occurrence_id=record.get("occurrence_id")
                linked=db.execute("SELECT 1 FROM exercise_sources es JOIN occurrences o ON o.id=es.occurrence_id WHERE es.variant_id=? AND o.id=? AND o.resource_id=?",(record["variant_id"],occurrence_id,record["source_id"])).fetchone()
                if not linked or not record.get("source_scope"):
                    raise ValueError("Source secondaire non liée ou périmètre absent")
            if not record.get("actor") or not record.get("checked_on") or not record.get("locator"):
                raise ValueError("Attribution incomplète")
            if record.get("capture_sha256") and not re.fullmatch(r"[0-9a-f]{64}",record["capture_sha256"]):
                raise ValueError("Empreinte de capture invalide")
            for key,field in record["fields"].items():
                if key not in FIELDS or field["state"] not in STATES:
                    raise ValueError("Champ ou état inconnu")
                if field["state"]=="PRESENT":
                    if field.get("value") is None or field.get("origin") not in ("SOURCE","AI_INFERRED","COACH_VALIDATED"):
                        raise ValueError("Valeur et origine requises")
                    if field["origin"]=="COACH_VALIDATED":
                        raise ValueError("Validation coach : workflow dédié requis")
                    if original.get(key) not in (None,"","Non renseigné") and original[key]!=field["value"]:
                        raise ValueError("Conflit avec le lot historique : "+key)
            encoded=json.dumps(record,ensure_ascii=False,sort_keys=True)
            old=db.execute("SELECT payload_json FROM enrichments WHERE id=?",(record["id"],)).fetchone()
            if old:
                if old[0]!=encoded:
                    raise ValueError("Révision explicite nécessaire")
                continue
            chain=history(db,record["variant_id"])
            if chain:
                if record.get("supersedes")!=chain[-1]["id"] or not record.get("revision_reason"):
                    raise ValueError("Révision explicite de la dernière version et motif requis")
                previous={}
                for revision in chain:
                    previous.update(revision["fields"])
                for key,field in record["fields"].items():
                    prior=previous.get(key,{})
                    if prior.get("origin")=="SOURCE" and field.get("origin")=="AI_INFERRED":
                        raise ValueError("Une proposition IA ne remplace pas un fait source")
            elif record.get("supersedes"):
                raise ValueError("Version précédente absente ou appartenant à une autre variante")
            db.execute("INSERT INTO enrichments VALUES(?,?,?)",(record["id"],record["variant_id"],encoded))
def provenance(db,record):
    result={k:record[k] for k in ("source_id","actor","checked_on","locator")}
    result["revision_id"]=record["id"]
    for key in ("occurrence_id","source_scope"):
        if record.get(key):
            result[key]=record[key]
    if record.get("capture_sha256"):
        digest=record["capture_sha256"]
        result["capture_sha256"]=digest
        paths=db.execute("SELECT archive_path FROM captures WHERE resource_id=? AND sha256=?",(record["source_id"],digest))
        result["capture_verified_locally"]=any(Path(r[0]).is_file() and hashlib.sha256(Path(r[0]).read_bytes()).hexdigest()==digest for r in paths)
    return result

def overlay(db,item):
    coverage={k:({"state":"PRESENT","origin":"LEGACY_UNREVIEWED"} if item.get(k) not in (None,"","Non renseigné") else {"state":"NOT_EXTRACTED"}) for k in FIELDS}
    chain=history(db,item["id"])
    for record in chain:
        source=provenance(db,record)
        for key,field in record["fields"].items():
            coverage[key]={**field,"provenance":source}
            item[key]=field["value"] if field["state"]=="PRESENT" else None
    item["field_coverage"]=coverage
    if chain:
        item["enrichment_provenance"]=provenance(db,chain[-1])
        item["enrichment_history"]=[{"id":r["id"],"supersedes":r.get("supersedes"),"checked_on":r["checked_on"],"reason":r.get("revision_reason")} for r in chain]
    return item
