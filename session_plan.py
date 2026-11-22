"""Contrôles structurels des brouillons de séance ; aucune validation pédagogique.

`validate` retourne des erreurs bloquantes, sans préfixe, et des avertissements
non bloquants préfixés « Avertissement — » : dépassement du créneau (le temps
planifié peut dépasser le créneau, l'éducateur ajuste) et total partiel (une
durée de bloc manque). La marge est dérivée (créneau − planifié) et jamais
stockée.

Un brouillon malformé (champ manquant côté plan : un groupe sans « id », une
affectation sans « group_id »…) lève `PlanMalforme` avec un message lisible ;
l'API le transforme en 400, jamais en 500.
"""


class PlanMalforme(ValueError):
    """Brouillon malformé (champ manquant côté plan) : message lisible, à
    transformer en 400 côté API (jamais 500)."""


def entier(value):
    """Normalise en `int` strict : entier accepté, flottant entier normalisé
    (7.0 → 7 — en JSON, 7.0 et 7 sont indistinguables), le reste (bool compris)
    → `None`. Miroir front : `Number.isInteger` (voir web/lib/session.ts)."""
    if type(value) is bool:
        return None
    if type(value) is int:
        return value
    if type(value) is float and value.is_integer():
        return int(value)
    return None


def positive(value):
    valeur = entier(value)
    return valeur is not None and valeur > 0


def clef_obligatoire(objet, clef, libelle):
    """Valeur de `clef` dans `objet`, ou `PlanMalforme` lisible si absente.

    `libelle` = ce que l'objet est dans le brouillon (« Groupe », « Affectation »).
    """
    if clef not in objet:
        raise PlanMalforme(libelle + " sans '" + clef + "'")
    return objet[clef]


def rotation_invalide(rotation):
    """Travail entier positif + transition entière ≥ 0 (flottants entiers
    normalisés par `entier`, comme côté front)."""
    transition = entier(rotation.get("transition_min"))
    return not positive(rotation.get("work_min")) or transition is None or transition < 0


def minutage(blocks, plan):
    """Créneau, temps planifié et total partiel (décision du 17 novembre)."""
    errors = []
    creneau = entier(plan.get("creneau_min"))
    if creneau is None or creneau <= 0:
        errors.append("Créneau invalide : 'creneau_min' absent ou non strictement positif.")
        creneau = None
    sans_duree = [b.get("label") or b.get("kind") for b in blocks if b.get("duration_min") is None]
    if sans_duree:
        errors.append("Avertissement — Le total est partiel : durée manquante sur " + ", ".join(sans_duree) + ".")
        return errors
    total = sum(entier(b["duration_min"]) for b in blocks)
    if total != entier(plan.get("duration_min")):
        errors.append("Durée totale différente de la somme des blocs")
        return errors
    if creneau is not None and total > creneau:
        errors.append("Avertissement — Dépassement du créneau : %d min planifiées pour un créneau de %d min." % (total, creneau))
    return errors


def validate(plan, catalogue):
    errors = []
    records = {e["id"]:e for e in catalogue["exercises"]}
    groups = plan.get("groups", [])
    group_ids = [clef_obligatoire(g, "id", "Groupe") for g in groups]
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
            if any(rotation_invalide(x) for x in rounds):
                errors.append("Durée de rotation invalide")
            elif duree_bloc is not None and sum(x["work_min"] + x["transition_min"] for x in rounds) != duree_bloc:
                errors.append("Durées de rotation incohérentes")
            for rotation in rounds:
                slots = rotation.get("assignments", [])
                if sorted(clef_obligatoire(s, "group_id", "Affectation") for s in slots) != sorted(group_ids):
                    errors.append("Chaque groupe doit être affecté une fois par rotation")
                if len({clef_obligatoire(s, "station_id", "Affectation") for s in slots}) != len(slots):
                    errors.append("Atelier occupé par plusieurs groupes simultanément")
                refs += [clef_obligatoire(s, "variant_id", "Affectation") for s in slots]
        for eid in refs:
            if eid not in records:
                errors.append("Exercice inconnu : " + str(eid))
            elif records[eid]["quality"]["state"] == "INCOMPLETE":
                errors.append("Exercice trop incomplet : " + str(eid))
    return errors
