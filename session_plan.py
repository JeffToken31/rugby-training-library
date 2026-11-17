"""Contrôles structurels des brouillons de séance ; aucune validation pédagogique.

`validate` retourne des erreurs bloquantes, sans préfixe, et des avertissements
non bloquants préfixés « Avertissement — » : dépassement du créneau (le temps
planifié peut dépasser le créneau, l'éducateur ajuste) et total partiel (une
durée de bloc manque). La marge est dérivée (créneau − planifié) et jamais
stockée.
"""

def positive(value):
    return type(value) is int and value > 0

def minutage(blocks, plan):
    """Créneau, temps planifié et total partiel (décision du 17 novembre)."""
    errors = []
    creneau = plan.get("creneau_min")
    if not positive(creneau):
        errors.append("Créneau invalide : 'creneau_min' absent ou non strictement positif.")
        creneau = None
    sans_duree = [b.get("label") or b.get("kind") for b in blocks if b.get("duration_min") is None]
    if sans_duree:
        errors.append("Avertissement — Le total est partiel : durée manquante sur " + ", ".join(sans_duree) + ".")
        return errors
    total = sum(b["duration_min"] for b in blocks)
    if total != plan.get("duration_min"):
        errors.append("Durée totale différente de la somme des blocs")
        return errors
    if creneau is not None and total > creneau:
        errors.append("Avertissement — Dépassement du créneau : %d min planifiées pour un créneau de %d min." % (total, creneau))
    return errors

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
    if not blocks:
        errors.append("Durées de blocs invalides")
    elif any(b.get("duration_min") is not None and not positive(b["duration_min"]) for b in blocks):
        errors.append("Durées de blocs invalides")
    else:
        errors.extend(minutage(blocks, plan))
    for block in blocks:
        refs = list(block.get("variant_ids", []))
        rounds = block.get("rounds", [])
        if rounds:
            duree_bloc = block.get("duration_min")
            if any(not positive(x.get("work_min")) or type(x.get("transition_min")) is not int or x["transition_min"] < 0 for x in rounds):
                errors.append("Durée de rotation invalide")
            elif duree_bloc is not None and sum(x["work_min"] + x["transition_min"] for x in rounds) != duree_bloc:
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
