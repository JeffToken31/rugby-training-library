"""Repères de préparation sans altérer les rubriques documentaires."""
from pathlib import Path

LABELS = dict(objectives="Objectif", organisation="Organisation", steps="Déroulement", instructions="Consignes", success_criteria="Critères de réussite", common_errors="Erreurs fréquentes", coach_points="Points d’attention", duration_min="Durée de l’atelier", players_min="Effectif minimum", players_max="Effectif maximum", space="Espace", material="Matériel")
QUESTIONS = dict(duration_min="Choisir la durée de l’atelier ; ne pas reprendre la durée d’une vidéo.", players_min="Fixer le nombre de joueurs actifs et ceux en attente.", players_max="Vérifier la capacité du dispositif pour le groupe prévu.", space="Définir les limites et dimensions adaptées au groupe.", material="Lister et préparer le matériel nécessaire.")

def preparation(e):
    result = []
    for field, question in QUESTIONS.items():
        state = e["fields"][field]["state"]
        if state != "PRESENT":
            result.append({"field":field, "state":state, "question":question})
    return result

def export(payload, out):
    out = Path(out)
    report = ["# Améliorations des fiches", "", "Toutes les fiches disposent de questions de préparation adaptées à leurs paramètres manquants. Les rubriques inconnues restent inconnues.", "", "## Repères pédagogiques proposés", "", "Ces compléments sont des propositions IA tirées des descriptions existantes, pas des critères fédéraux ou des validations coach.", ""]
    for e in payload["exercises"]:
        path = out / "fiches" / (e["id"] + ".md")
        text = path.read_text(encoding="utf-8")
        # Replace technical field keys only on the generated missing-fields line.
        for line in text.splitlines():
            if line.startswith("Champs à préciser : "):
                readable = ", ".join(LABELS[f] for f in e["quality"]["missing_fields"])
                text = text.replace(line, "Informations encore absentes : " + (readable or "aucune parmi les rubriques suivies") + ".")
        lines = ["", "### Réglages à préparer pour ma séance", ""]
        pending = preparation(e)
        lines += ["- " + p["question"] + (" **La source est contradictoire sur ce paramètre.**" if p["state"] == "CONFLICTING" else "") for p in pending]
        if not pending:
            lines += ["Les paramètres suivis sont renseignés ; vérifier leur adéquation au groupe du jour."]
        if e["quality"]["state"] == "INCOMPLETE":
            lines += ["", "**Description encore insuffisante : ne pas utiliser cette fiche seule pour lancer l’activité.**"]
        cue = e.get("coach_cues")
        if cue:
            lines += ["", "### Repères pédagogiques proposés — à adapter par l’éducateur", "", "**Indicateur observable :** " + cue["success_indicator"], "", "**À regarder :** " + cue["coach_observation"], "", "Proposition IA fondée sur le déroulement et les consignes existants ; ne remplace pas les critères de la source."]
            report += [f"- [{e['title']}](fiches/{e['id']}.md) : {cue['success_indicator']}"]
        path.write_text(text + "\n".join(lines) + "\n", encoding="utf-8")
    (out / "AMELIORATIONS_FICHES.md").write_text("\n".join(report)+"\n", encoding="utf-8")
