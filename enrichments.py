"""Enrichissements attribués, séparés des lots historiques."""
import json
import re
import hashlib
from pathlib import Path
FIELDS=("objectives","organisation","steps","instructions","success_criteria","common_errors","coach_points","duration_min","players_min","players_max","space","material")
STATES=("PRESENT","NOT_STATED","NOT_EXTRACTED","BLOCKED","CONFLICTING")
def schema(db):
    db.execute("CREATE TABLE IF NOT EXISTS enrichments(id TEXT PRIMARY KEY, variant_id TEXT NOT NULL REFERENCES variants(id), payload_json TEXT NOT NULL CHECK(json_valid(payload_json)))")
def ingest(db,payload):
    with db:
        for record in payload["enrichments"]:
            row=db.execute("SELECT parameters_json FROM variants WHERE id=?",(record["variant_id"],)).fetchone()
            if row is None:
                raise ValueError("Variante inconnue")
            original=json.loads(row[0])
            if original["source_id"]!=record["source_id"]:
                raise ValueError("Source incohérente")
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
            if db.execute("SELECT 1 FROM enrichments WHERE variant_id=?",(record["variant_id"],)).fetchone():
                raise ValueError("Enrichissement déjà présent ; révision explicite requise")
            db.execute("INSERT INTO enrichments VALUES(?,?,?)",(record["id"],record["variant_id"],encoded))
def overlay(db,item):
    baseline={k:({"state":"PRESENT","origin":"LEGACY_UNREVIEWED"} if item.get(k) not in (None,"","Non renseigné") else {"state":"NOT_EXTRACTED"}) for k in FIELDS}
    row=db.execute("SELECT payload_json FROM enrichments WHERE variant_id=?",(item["id"],)).fetchone()
    if not row:
        item["field_coverage"]=baseline
        return item
    record=json.loads(row[0])
    item["field_coverage"]={k:record["fields"].get(k,baseline[k]) for k in FIELDS}
    item["enrichment_provenance"]={k:record[k] for k in ("source_id","actor","checked_on","locator")}
    if record.get("capture_sha256"):
        digest=record["capture_sha256"]
        item["enrichment_provenance"]["capture_sha256"]=digest
        paths=db.execute("SELECT archive_path FROM captures WHERE resource_id=? AND sha256=?",(record["source_id"],digest))
        item["enrichment_provenance"]["capture_verified_locally"]=any(Path(r[0]).is_file() and hashlib.sha256(Path(r[0]).read_bytes()).hexdigest()==digest for r in paths)
    for key,field in record["fields"].items():
        if field["state"]=="PRESENT":
            item[key]=field["value"]
    return item
