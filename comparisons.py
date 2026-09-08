"""Comparaisons documentaires consultables, sans fusion de variantes."""
import json
from pathlib import Path

def cell(value):
    if value is None or value == "":
        return "Non renseigné"
    if not isinstance(value,str):
        value=json.dumps(value,ensure_ascii=False)
    return value.replace("|", "&#124;").replace("\r", " ").replace("\n", "<br>")

def export(db,out,items):
    by_id={item["id"]:item for item in items}
    lines=["# Comparer les exercices proches", "",
        "Ces rapprochements documentaires sont des pistes de classement. Ils ne fusionnent aucune fiche et ne constituent pas une validation pédagogique.", ""]
    rows=list(db.execute("SELECT * FROM duplicate_candidates ORDER BY id"))
    labels={"UNDECIDED":"À examiner", "SAME_FAMILY":"Même famille proposée", "SAME_VARIANT":"Même variante proposée", "DIFFERENT_VARIANT":"Variantes distinctes proposées", "DIFFERENT_EXERCISE":"Exercices distincts proposés"}
    for row in rows:
        left,right=by_id[row["left_id"]],by_id[row["right_id"]]
        lines += ["## "+left["title"]+" / "+right["title"], "",
            labels[row["relation"]]+". "+row["explanation"], "",
            "| Information | ["+cell(left["title"])+"](fiches/"+left["id"]+".md) | ["+cell(right["title"])+"](fiches/"+right["id"]+".md) |",
            "|---|---|---|"]
        for key,label in (("summary","Principe"),("organisation","Organisation"),("steps","Déroulement"),("instructions","Consignes"),("age_source","Âge indiqué"),("locator","Passage source")):
            lines.append("| "+label+" | "+cell(left.get(key))+" | "+cell(right.get(key))+" |")
        lines += ["", "Les compléments attribués et les liens d’origine sont accessibles dans chaque fiche.", ""]
    if not rows:
        lines += ["Aucun rapprochement enregistré.", ""]
    Path(out,"COMPARAISONS.md").write_text("\n".join(lines).rstrip()+"\n",encoding="utf-8")
    return len(rows)
