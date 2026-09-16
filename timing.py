"""Budgets de planification séparés des durées documentaires."""
from pathlib import Path

def total(profile, rounds):
    return profile["intro_seconds"] + rounds * profile["round_seconds"] + max(0, rounds - 1) * profile["between_seconds"] + profile["outro_seconds"]

def attach(payload, config):
    records = {r["variant_id"]:r for r in config["records"]}
    if len(records) != len(config["records"]) or set(records) != {e["id"] for e in payload["exercises"]}:
        raise ValueError("Couverture des durées invalide")
    for e in payload["exercises"]:
        entry = dict(records[e["id"]])
        profile_id = entry["profile_id"]
        if profile_id:
            if e["quality"]["state"] == "INCOMPLETE":
                raise ValueError("Durée proposée sur description insuffisante")
            p = dict(config["profiles"][profile_id])
            if any(type(p[k]) is not int or p[k] <= 0 for k in ("intro_seconds", "round_seconds", "rounds_min", "rounds_max", "between_seconds", "outro_seconds")) or p["rounds_max"] < p["rounds_min"]:
                raise ValueError("Profil temporel invalide")
            entry.update(profile=p, min_seconds=total(p,p["rounds_min"]), max_seconds=total(p,p["rounds_max"]), includes_briefing=True, includes_group_transition=False)
        e["planning_duration"] = entry

def minutes(seconds):
    return f"{seconds / 60:g}".replace(".", ",")

def description(e):
    timing=e["planning_duration"]
    if timing["status"] == "INSUFFICIENT_DESCRIPTION":
        return "Durée non estimée : déroulement insuffisamment décrit."
    if timing["status"] == "EXISTING_DURATION":
        f=e["fields"]["duration_min"]
        label="durée documentaire" if f.get("origin")=="SOURCE" else "durée historique, périmètre à vérifier"
        return f"{f['value']} min — {label}. Temps d’explication et transitions à vérifier ; ce chiffre n’est pas une durée d’effort continu."
    if timing["status"] == "KNOWN_ROUND_DURATION":
        return f"Manche documentée : {e['bout_seconds']} secondes. Choisir le nombre de manches, les pauses et les explications pour fixer la durée totale ; ne pas confondre manche et atelier."
    return f"Budget proposé : {minutes(timing['min_seconds'])} à {minutes(timing['max_seconds'])} min, explications et retours inclus, déplacement vers l’atelier suivant exclu. Proposition IA à ajuster par le coach."

def export(payload,out):
    out=Path(out)
    lines=["# Durées pour préparer les ateliers", "", "Les budgets proposés sont des hypothèses de planification, pas des mesures ni des prescriptions d’effort. Les temps de séquence comprennent les passages et l’attente éventuelle ; ils ne garantissent pas le temps actif de chaque enfant.", "", "| Exercice | Durée et statut |", "|---|---|"]
    catalogue=(out/"CATALOGUE.md").read_text()
    for e in payload["exercises"]:
        summary=description(e)
        lines.append(f"| [{e['title']}](fiches/{e['id']}.md) | {summary} |")
        path=out/"fiches"/(e["id"]+".md")
        extra=["", "### Durée pour planifier l’atelier", "", summary]
        p=e["planning_duration"].get("profile")
        if p:
            extra += ["", f"- Explication et démonstration : {p['intro_seconds']} s.", f"- {p['rounds_min']} à {p['rounds_max']} séquences de {p['round_seconds']} s, avec {p['between_seconds']} s entre deux séquences pour récupérer, permuter ou corriger.", f"- Retour final : {p['outro_seconds']} s.", "", "**Pour prolonger :** "+p["extension"], "", "Les séquences incluent les passages et l’attente éventuelle ; adapter à l’effectif, aux réactions des enfants et au dispositif. Ce n’est pas une durée d’effort continu imposée."]
        path.write_text(path.read_text()+"\n".join(extra)+"\n")
        catalogue=catalogue.replace("## "+e["title"]+"\n", "## "+e["title"]+"\n\n**Planifier l’atelier :** "+summary+"\n",1)
    (out/"CATALOGUE.md").write_text(catalogue)
    (out/"DUREES.md").write_text("\n".join(lines)+"\n")
