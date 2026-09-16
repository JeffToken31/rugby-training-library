"""Vue de lecture pour l’application, sans réseau ni modification des faits sources."""
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
import catalogue_v2 as v2
import enrichments

CORE = ("objectives", "organisation", "steps", "instructions")
LABELS = {"DOCUMENTED_CORE": "Noyau documentaire présent", "PROPOSED_OBJECTIVE": "Objectif proposé à confirmer", "REPORTED_OBSERVATION": "Observation utilisateur", "INCOMPLETE": "Description insuffisante"}

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def unique(rows, key):
    result = {}
    for row in rows:
        if row[key] in result:
            raise ValueError("Identifiant répété : " + row[key])
        result[row[key]] = row
    return result

def build(db, root, config):
    root = Path(root)
    audit = read(root / config["classification"])
    families = unique(audit["families"], "id")
    assignments = unique(audit["assignments"], "variant_id")
    editorial = read(root / config["proposals"])
    proposals = unique(editorial["objectives"], "variant_id")
    overrides = unique(editorial.get("classification_overrides", []), "variant_id")
    observations = unique([read(root / p) for p in config["observations"]], "variant_id")
    items = sorted(v2.items(db), key=lambda e: e["id"])
    ids = {e["id"] for e in items}
    if set(assignments) != ids or (set(proposals) | set(observations) | set(overrides)) - ids:
        raise ValueError("Classement ou complément hors corpus")
    relations = [dict(r) for r in db.execute("SELECT * FROM duplicate_candidates ORDER BY id")]
    reviews = audit.get("pair_reviews", [])
    for r in relations + reviews:
        if r["left_id"] not in ids or r["right_id"] not in ids:
            raise ValueError("Rapprochement hors corpus")
    records = []
    for e in items:
        eid = e["id"]
        classification = copy.deepcopy(assignments[eid])
        if eid in overrides:
            change = overrides[eid]
            if eid not in observations or change["basis_observation_id"] != observations[eid]["id"]:
                raise ValueError("Reclassement sans observation correspondante")
            classification["previous_family_id"] = classification["family_id"]
            classification.update(change)
        if classification["family_id"] not in families:
            raise ValueError("Famille inconnue : " + eid)
        fields = copy.deepcopy(e["field_coverage"])
        for name in enrichments.FIELDS:
            field = fields[name]
            field.setdefault("value", e.get(name) if field["state"] == "PRESENT" else None)
            if field["state"] == "PRESENT" and field["value"] in (None, "", []):
                raise ValueError("Champ présent vide : " + eid + "/" + name)
        source_fields = copy.deepcopy(fields)
        if eid in proposals:
            p = proposals[eid]
            if fields["objectives"]["state"] == "PRESENT" or p["origin"] != "AI_INFERRED":
                raise ValueError("Proposition écrasant un objectif : " + eid)
            fields["objectives"] = {"state":"PRESENT", "value":p["value"], "origin":"AI_INFERRED", "provenance":p}
        observation = observations.get(eid)
        if observation:
            if observation["evidence_type"] != "USER_REPORTED_VIDEO_OBSERVATION":
                raise ValueError("Type d’observation inconnu")
            for field, key in (("organisation", "organisation"), ("steps", "steps"), ("instructions", "instructions_reported")):
                if fields[field]["state"] == "PRESENT":
                    raise ValueError("Observation en conflit : " + eid + "/" + field)
                fields[field] = {"state":"PRESENT", "value":observation[key], "origin":"USER_REPORTED", "provenance":{"observation_id":observation["id"], "reported_on":observation["reported_on"], "video_url":observation["video_url"]}}
        missing = [f for f in CORE if fields[f]["state"] != "PRESENT"]
        state = "INCOMPLETE" if missing else "REPORTED_OBSERVATION" if observation else "PROPOSED_OBJECTIVE" if fields["objectives"].get("origin") == "AI_INFERRED" else "DOCUMENTED_CORE"
        related = [r for r in relations if eid in (r["left_id"], r["right_id"])]
        reviewed = [r for r in reviews if eid in (r["left_id"], r["right_id"])]
        records.append({
            "id":eid, "title":e["title"], "original_title":e.get("original_title"), "summary":e.get("summary"),
            "theme":e.get("theme"), "classification":classification,
            "age_source":e.get("age_source"), "u8_adaptation":e.get("adaptation_u8"),
            "u8_proposed_settings":e.get("u8_plan"), "participants_scope":e.get("participants_scope"),
            "fields":fields, "documentary_fields":source_fields, "source":e["source"],
            "locator":e["locator"], "references":e.get("references", []), "history":e.get("enrichment_history", []),
            "observation":observation, "related_candidates":related, "comparison_reviews":reviewed,
            "quality":{"state":state, "missing_core":missing,
                "missing_fields":[f for f in enrichments.FIELDS if fields[f]["state"] != "PRESENT"],
                "core_origins":{f:fields[f].get("origin") for f in CORE},
                "coach_validated":False, "u8_suitability":"TO_REVIEW", "contact_level":"UNKNOWN",
                "default_visible":state != "INCOMPLETE"},
        })
    counts = dict(sorted(Counter(e["quality"]["state"] for e in records).items()))
    payload = {"schema_version":1, "core_fields":list(CORE), "field_names":list(enrichments.FIELDS),
        "families":list(families.values()), "exercises":records,
        "canonical_game_groups":audit.get("canonical_game_groups", []),
        "source_supplements":[read(root / path) for path in config.get("source_supplements", [])],
        "summary":{"records":len(records), "families":len(families), "readiness":counts, "unique_exercises":None},
        "policy":{"collection":"PAUSED", "unknown_values":"NULL", "automatic_merge":False,
            "note":"Présence des rubriques ≠ exhaustivité, validation terrain ou conformité U8. Les propositions et observations restent identifiées."}}
    if config.get("tags"):
        import exercise_tags
        exercise_tags.attach(payload, read(root / config["tags"]))
    payload["content_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return payload

def export(db, root, out, config):
    payload = build(db, root, config)
    out = Path(out)
    (out / "APPLICATION.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if "tag_taxonomy" in payload:
        import exercise_tags
        exercise_tags.export(payload, out)
        catalogue = out / "CATALOGUE.md"
        text = catalogue.read_text(encoding="utf-8")
        text = text.replace("# Bibliothèque rugby U8", "# Bibliothèque rugby U8\n\n[Parcourir par compétence et forme de jeu](CATEGORIES.md)", 1)
        for e in payload["exercises"]:
            labels = [t["label"] for t in payload["tag_taxonomy"]["tags"] if t["id"] in e["tag_ids"]]
            text = text.replace("## " + e["title"] + "\n", "## " + e["title"] + "\n\n**Tags proposés :** " + " · ".join(labels) + "\n", 1)
        catalogue.write_text(text, encoding="utf-8")
    lines = ["# Base destinée à la création de séances", "", "Aucune collecte supplémentaire. Rapport reconstruit depuis les données versionnées.", "", "Le nombre de fiches ne signifie pas autant de jeux uniques ni de fiches exhaustives.", ""]
    for state, count in payload["summary"]["readiness"].items():
        lines.append(f"- {LABELS[state]} : {count}.")
    lines += ["", "Les fiches incomplètes restent accessibles séparément. Toutes nécessitent une adaptation au groupe ; les paramètres inconnus ne sont pas remplacés par zéro.", "", "| Fiche | État | Champs restant inconnus |", "|---|---|---|"]
    for e in payload["exercises"]:
        lines.append(f"| [{e['title']}](fiches/{e['id']}.md) | {LABELS[e['quality']['state']]} | {', '.join(e['quality']['missing_fields']) or 'Aucun parmi les 12 champs suivis'} |")
        # Append app supplements after the documentary export, which is regenerated first.
        path = out / "fiches" / (e["id"] + ".md")
        if path.exists():
            extra = ["", "## Préparation de séance", "", "État : " + LABELS[e["quality"]["state"]] + ". Aucune validation coach implicite.", "Famille proposée : " + next(f["title"] for f in payload["families"] if f["id"] == e["classification"]["family_id"]) + "."]
            if e.get("tag_ids"):
                labels = [t["label"] for t in payload["tag_taxonomy"]["tags"] if t["id"] in e["tag_ids"]]
                extra += ["", "**Tags proposés :** " + " · ".join(labels), "Classement provisoire." if e["tagging"]["status"] == "PROVISIONAL" else "Classement éditorial ; plusieurs catégories possibles sans duplication."]
            for f in CORE:
                item = e["fields"][f]
                if item.get("origin") in ("AI_INFERRED", "USER_REPORTED") and item != e["documentary_fields"][f]:
                    value = item["value"]
                    extra += ["", f"**{f} — {item['origin']}**", "", " ; ".join(value) if isinstance(value, list) else value]
            if e["observation"]:
                extra += ["", "Incertitudes : " + " ; ".join(e["observation"]["uncertainties"]), "Environ 30 secondes rapportées : observation, pas une durée prescrite."]
            extra += ["", "Champs à préciser : " + (", ".join(e["quality"]["missing_fields"]) or "aucun parmi les champs suivis") + ".", ""]
            path.write_text(path.read_text(encoding="utf-8") + "\n".join(extra), encoding="utf-8")
    (out / "QUALITE_APPLICATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload["summary"]
