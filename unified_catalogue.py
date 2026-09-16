"""Un seul catalogue lisible, avec fiches individuelles issues du même rendu."""
import itertools
import json
import re
from pathlib import Path
import timing
from fiche_preparation import LABELS

ORIGINS={"SOURCE":"source", "AI_INFERRED":"proposition IA", "USER_REPORTED":"observation utilisateur", "LEGACY_UNREVIEWED":"historique non réexaminé"}
STATES={"NOT_EXTRACTED":"non extrait", "NOT_STATED":"non indiqué dans le passage examiné", "BLOCKED":"accès bloqué", "CONFLICTING":"contradiction à résoudre"}
DECISIONS={"UNRESOLVED":"Rapprochement non résolu", "PROBABLE_DUPLICATE":"Doublon probable — ne pas compter comme nouveauté", "KEEP_DISTINCT_VARIANTS":"Variantes conservées séparément"}

def value(x):
    if isinstance(x,list): return "; ".join(value(i) for i in x)
    if isinstance(x,dict): return "; ".join(str(k)+" : "+value(v) for k,v in x.items())
    return str(x) if x is not None else "Non renseigné"

def attach(payload, review):
    ids={e["id"] for e in payload["exercises"]}
    for pair in review["pair_reviews"]:
        if pair["left_id"] not in ids or pair["right_id"] not in ids: raise ValueError("Comparaison hors corpus")
    checked={e["variant_id"]:e for e in review["missing_review"]}
    if set(checked)-ids: raise ValueError("Audit hors corpus")
    pairs=[]
    for a,b in itertools.combinations(payload["exercises"],2):
        x=re.sub(r"\W+"," ",value(a["fields"]["steps"].get("value"))).lower()
        y=re.sub(r"\W+"," ",value(b["fields"]["steps"].get("value"))).lower()
        if a["fields"]["steps"]["state"]==b["fields"]["steps"]["state"]=="PRESENT" and x==y:
            pairs.append([a["id"],b["id"]])
    payload["consolidation_review"]={**review,"exact_steps_pairs":pairs,"pairs_checked":len(ids)*(len(ids)-1)//2}
    for e in payload["exercises"]:
        e["duplicate_review"]=[p for p in review["pair_reviews"] if e["id"] in (p["left_id"],p["right_id"])]
        e["missing_review"]=checked.get(e["id"])

def body(e,payload,link):
    tags=[t["label"] for t in payload.get("tag_taxonomy",{}).get("tags",[]) if t["id"] in e.get("tag_ids",[])]
    family=next(f["title"] for f in payload["families"] if f["id"]==e["classification"]["family_id"])
    lines=[f"**Catégories proposées :** {' · '.join(tags)}", "", f"**Famille :** {family} · **Âge source :** {e['age_source']}", "", e.get("summary") or "", "", "**Durée pour préparer l’atelier :** "+timing.description(e), ""]
    if e["quality"]["state"]=="INCOMPLETE": lines += ["**Fiche insuffisamment décrite : à consulter comme piste, pas à lancer seule sur le terrain.**", ""]
    profile=e.get("planning_duration",{}).get("profile")
    if profile:
        lines += [f"Découpage proposé : explication {profile['intro_seconds']} s ; {profile['rounds_min']}–{profile['rounds_max']} séquences de {profile['round_seconds']} s ; {profile['between_seconds']} s entre les séquences ; retour final {profile['outro_seconds']} s.", "", "Pour prolonger : "+profile["extension"], "", "Ces séquences incluent les passages et l’attente éventuelle, pas un effort continu imposé.", ""]
    for key in ("objectives","material","players_min","players_max","space","duration_min","organisation","steps","instructions","success_criteria","common_errors","coach_points"):
        field=e["fields"][key]
        if field["state"]=="PRESENT":
            text=value(field["value"])
            label=ORIGINS.get(field.get("origin"),"origine non qualifiée")
        else:
            text=STATES.get(field["state"],field["state"]); label="information manquante"
        lines += [f"**{LABELS[key]} — {label} :** {text}", ""]
    if e.get("participants_scope"): lines += ["**Périmètre de l’effectif :** "+e["participants_scope"], ""]
    if e.get("bout_seconds"): lines += [f"**Durée d’une manche dans la source :** {e['bout_seconds']} secondes ; distincte de la durée totale.", ""]
    if e.get("source_conflicts"): lines += ["**Contradictions documentaires :** "+" ; ".join(x["note"] for x in e["source_conflicts"]), ""]
    if e.get("u8_adaptation"): lines += ["**Adaptation U8 proposée :** "+e["u8_adaptation"], ""]
    if e.get("u8_proposed_settings"):
        lines += ["**Réglages U8 historiques proposés, distincts de la source :**", "",value(e["u8_proposed_settings"]), ""]
    if e.get("coach_cues"):
        c=e["coach_cues"];lines += ["**Repères coach proposés par IA :** "+c["success_indicator"]+" "+c["coach_observation"], ""]
    if e.get("observation"):
        o=e["observation"];lines += ["**Observation utilisateur :** "+o["verification"], "", "**Incertitudes rapportées :** "+value(o["uncertainties"]), "", "**Temps observé :** "+value(o["observed_duration"])+" — ne constitue pas une durée prescrite.", "",f"[Vidéo décrite par l’utilisateur]({o['video_url']})", ""]
    if e.get("preparation_questions"):
        lines += ["**À décider pour la séance :**", ""]+["- "+x["question"] for x in e["preparation_questions"]]+[""]
    if e.get("missing_review"): lines += ["**Relecture des manques :** "+e["missing_review"]["conclusion"], ""]
    for pair in e.get("duplicate_review",[]):
        other=pair["right_id"] if pair["left_id"]==e["id"] else pair["left_id"]
        title=next(x["title"] for x in payload["exercises"] if x["id"]==other)
        lines += [f"**{DECISIONS[pair['decision']]} :** [{title}]({link(other)}). {pair['reason']}", ""]
    for pair in e.get("comparison_reviews",[]):
        other=pair["right_id"] if pair["left_id"]==e["id"] else pair["left_id"]
        lines += [f"**Comparaison éditoriale complémentaire :** [{other}]({link(other)}) — {pair['reason']}", ""]
    s=e["source"]
    lines += [f"**Source principale :** [{s['title']}]({s['url']}) — {s.get('publisher','')} ; {e['locator']}. Vérification documentaire : {s.get('checked_on','non datée')}.", ""]
    for ref in e.get("references",[]):
        lines += [f"**Référence complémentaire :** [{ref['source']['title']}]({ref['source']['url']}) — {ref['locator']}. {ref.get('summary','')}", ""]
    for supplement in payload.get("source_supplements",[]):
        video=supplement.get("m8_candidates",{}).get(e["id"])
        if video: lines += [f"**Lien extrait du PDF fourni :** [vidéo candidate]({video}). Association issue des annotations, visionnage non validé par l’assistant.", ""]
    lines += ["<details>", "<summary>Provenance par rubrique et historique</summary>", ""]
    groups={}
    for key,field in e["fields"].items():
        p=field.get("provenance")
        if p:
            sig=(p.get("source_id",p.get("observation_id","")),p.get("locator",""),p.get("checked_on",p.get("reported_on","")))
            groups.setdefault(sig,[]).append(LABELS[key])
    for (source,locator,date),fields in groups.items():
        lines += ["- "+", ".join(fields)+" : "+source+" ; "+locator+" ; "+date]
    lines += ["", f"{len(e.get('history',[]))} révision(s) conservée(s) dans les données de l’application.", "", "</details>", ""]
    return lines

def export(payload,out):
    out=Path(out);exercises=sorted(payload["exercises"],key=lambda x:x["title"].casefold())
    lines=["# Catalogue complet des exercices U8", "", "Point d’entrée unique : catégories, durées, installation, consignes, adaptations, sources, manques et rapprochements sont réunis ici.", "", f"**{len(exercises)} fiches** ; une fiche peut appartenir à plusieurs catégories sans être dupliquée. Ce total n’est pas un nombre certifié de jeux uniques. Les propositions restent distinctes des informations documentaires.", "", "[Par catégories](#categories) · [Toutes les fiches](#fiches) · [Doublons et manques](#controle)", "", '<a id="categories"></a>', "## Catégories", ""]
    for dimension,label in (("skill","Compétences"),("format","Formes de jeu")):
        lines += ["### "+label, ""]
        for tag in payload["tag_taxonomy"]["tags"]:
            if tag["dimension"]==dimension:
                matches=[e for e in exercises if tag["id"] in e["tag_ids"]]
                lines += ["**"+tag["label"]+f" ({len(matches)}) :** "+" · ".join(f"[{e['title']}](#{e['id']})" for e in matches), ""]
    review=payload["consolidation_review"]
    lines += ['<a id="controle"></a>',"## Doublons et informations manquantes", "",review["scope"], "",f"{review['pairs_checked']} paires contrôlées pour l’égalité du déroulement : {len(review['exact_steps_pairs'])} correspondance(s). Cette comparaison textuelle ne détecte pas toutes les reformulations d’un même jeu.", "", "Neuf fiches complétées en points coach après relecture des archives locales ; les neuf descriptions insuffisantes restent à part. Les autres champs absents ne sont pas déclarés introuvables : leur relecture exhaustive reste à poursuivre.", ""]
    for pair in review["pair_reviews"]:
        lines += [f"- {DECISIONS[pair['decision']]} : [{pair['left_id']}](#{pair['left_id']}) / [{pair['right_id']}](#{pair['right_id']}) — {pair['reason']}"]
    lines += ["",'<a id="fiches"></a>',"## Toutes les fiches", ""]
    for e in exercises:
        lines += [f'<a id="{e["id"]}"></a>', "## "+e["title"], ""]+body(e,payload,lambda eid:'#'+eid)+["[Retour aux catégories](#categories)", "", "---", ""]
        single=["# "+e["title"], "", "[Retour au catalogue complet](../CATALOGUE.md)", ""]+body(e,payload,lambda eid:eid+'.md')
        (out/"fiches"/(e["id"]+".md")).write_text("\n".join(single),encoding="utf-8")
    (out/"CATALOGUE.md").write_text("\n".join(lines),encoding="utf-8")
    aliases={"CATEGORIES.md":"categories","DUREES.md":"fiches","AMELIORATIONS_FICHES.md":"fiches","COMPARAISONS.md":"controle","QUALITE_APPLICATION.md":"controle","INDEX.md":"categories","FICHES_DETAILLEES.md":"fiches"}
    for name,anchor in aliases.items():
        (out/name).write_text(f"# Vue intégrée au catalogue\n\nLes informations de cette ancienne vue sont maintenant centralisées dans le [catalogue complet](CATALOGUE.md#{anchor}).\n",encoding="utf-8")
