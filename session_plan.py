"""Contrôles structurels des brouillons de séance ; aucune validation pédagogique."""

def positive(value):
    return type(value) is int and value > 0

def validate(plan, catalogue):
    errors = []
    records = {e["id"]:e for e in catalogue["exercises"]}
    groups = plan.get("groups", [])
    group_ids = [g["id"] for g in groups]
    if not groups or len(set(group_ids)) != len(group_ids):
        errors.append("Groupes absents ou répétés")
    if any(not positive(g.get("players")) for g in groups):
        errors.append("Effectifs de groupe invalides")
    elif sum(g["players"] for g in groups) != plan.get("players"):
        errors.append("Effectif total différent de la somme des groupes")
    blocks = plan.get("blocks", [])
    if not blocks or any(not positive(b.get("duration_min")) for b in blocks):
        errors.append("Durées de blocs invalides")
    elif sum(b["duration_min"] for b in blocks) != plan.get("duration_min"):
        errors.append("Durée totale différente de la somme des blocs")
    for block in blocks:
        refs = list(block.get("variant_ids", []))
        rounds = block.get("rounds", [])
        if rounds:
            if any(not positive(x.get("work_min")) or type(x.get("transition_min")) is not int or x["transition_min"] < 0 for x in rounds):
                errors.append("Durée de rotation invalide")
            elif sum(x["work_min"] + x["transition_min"] for x in rounds) != block["duration_min"]:
                errors.append("Durées de rotation incohérentes")
            for rotation in rounds:
                slots = rotation.get("assignments", [])
                if sorted(s["group_id"] for s in slots) != sorted(group_ids):
                    errors.append("Chaque groupe doit être affecté une fois par rotation")
                if len({s["station_id"] for s in slots}) != len(slots):
                    errors.append("Atelier occupé par plusieurs groupes simultanément")
                refs += [s["variant_id"] for s in slots]
        for eid in refs:
            if eid not in records:
                errors.append("Exercice inconnu : " + eid)
            elif records[eid]["quality"]["state"] == "INCOMPLETE":
                errors.append("Exercice trop incomplet : " + eid)
    return errors
