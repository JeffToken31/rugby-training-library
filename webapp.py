"""Lot 1 — Catalogue mobile : API JSON + service du front statique.

Socle : Python standard (wsgiref), aucune dépendance externe.

Lecture seule sur `exports/APPLICATION.json` (vue de lecture v1) : le fichier
est lu à froid une fois au démarrage, jamais réécrit. Les adaptations de
durée / effectif / organisation restent dans la séance (lots suivants).

Routes :
  GET /api/catalogue          → vue complète (fiches + taxonomie + familles
                                + échauffements + politique inconnus)
  GET /api/recherche?q=...    → même liste de fiches, filtrée (titre,
                                original_title, résumé ; insensible aux
                                accents) ; paramètres optionnels :
                                tags=<id,id>, match=all|any,
                                include_incomplete=true, usage=WARMUP
                                (sémantique identique à exercise_tags.select)
  GET /api/fiches/<id>        → fiche complète (404 si absente)
  GET /*                      → front statique (web/out/), fallback index.html
"""

import json
import os
import socket
import unicodedata
from http import HTTPStatus
from urllib.parse import parse_qs, unquote

from wsgiref.simple_server import make_server

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(APP_DIR, "exports", "APPLICATION.json")
STATIC_DIR = os.path.join(APP_DIR, "web", "out")
HOST = "0.0.0.0"
PORT = 8347

CORE_FIELDS = ("objectives", "organisation", "steps", "instructions")
CORE_FR = {
    "objectives": "Objectifs",
    "organisation": "Organisation",
    "steps": "Déroulement",
    "instructions": "Consignes",
}


def _load_payload():
    with open(DATA_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


PAYLOAD = _load_payload()
EXERCISES = PAYLOAD["exercises"]
BY_ID = {e["id"]: e for e in EXERCISES}


def fold(text):
    """Minuscules + sans accents : « é » et « e » tombent ensemble."""
    if not text:
        return ""
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii").lower()


def _search_match(query_folded, e):
    """La requête doit apparaître dans au moins un champ : titre,
    original_title ou résumé (critère 3 du charter)."""
    return (
        query_folded in fold(e.get("title", ""))
        or query_folded in fold(e.get("original_title", ""))
        or query_folded in fold(e.get("summary", ""))
    )


def select_catalogue(query=None, tag_ids=(), match="all", include_incomplete=True, usage=None):
    """Filtrer la vue catalogue.

    La sémantique des tags est identique à exercise_tags.select :
    « all » = tous les tags demandés présents ; « any » = au moins un ;
    les fiches incomplètes sont affichées par défaut (défaut produit :
    tout le catalogue, avec badge d'état) ; usage = « WARMUP » restreint
    à session_uses.
    """
    wanted = [t for t in tag_ids if t]
    qf = fold(query) if query else ""
    out = []
    for e in EXERCISES:
        if not include_incomplete and not e["quality"]["default_visible"]:
            continue
        if usage is not None and usage not in e.get("session_uses", []):
            continue
        if wanted and match == "all" and not set(wanted) <= set(e.get("tag_ids", [])):
            continue
        if wanted and match == "any" and not (set(wanted) & set(e.get("tag_ids", []))):
            continue
        if qf and not _search_match(qf, e):
            continue
        out.append(card_for(e))
    return out


def card_for(e):
    """Carte de liste : l'essentiel de la fiche, sans les rubriques longues."""
    pd = e.get("planning_duration") or {}
    return {
        "id": e["id"],
        "title": e["title"],
        "original_title": e.get("original_title"),
        "summary": e.get("summary"),
        "state": e["quality"]["state"],
        "default_visible": e["quality"]["default_visible"],
        "tag_ids": e.get("tag_ids", []),
        "session_uses": e.get("session_uses", []),
        "planning_min_seconds": pd.get("min_seconds"),
        "planning_max_seconds": pd.get("max_seconds"),
        "duration_status": pd.get("status"),
        "media": media_for(e),
    }


def media_for(e):
    """Médias d'une fiche, selon le rattachement officiel du catalogue.

    Le rattachement fiche → supplément est `m8_candidates` (unified_catalogue) :
    une vidéo candidate au plus par fiche, jamais les liens bruts du PDF.
    Libellé officiel : « Lien extrait du PDF fourni : vidéo candidate.
    Association issue des annotations, visionnage non validé. »
    La « capture locale » = l'archive PDF du supplément, indiquée seulement
    si elle est réellement présente sur la machine (indicateur, pas une copie).
    """
    result = {"video": None, "local_capture": None}
    for sup in PAYLOAD.get("source_supplements", []):
        url = (sup.get("m8_candidates") or {}).get(e["id"])
        if url is None:
            continue
        archive = sup.get("local_archive")
        result["video"] = {
            "url": url,
            "review_status": sup.get("video_review_status"),
        }
        result["local_capture"] = {
            "archive": archive,
            "available": _archive_present(archive),
            "redistribute_pdf": sup.get("redistribute_pdf", False),
        }
        break
    return result


def _archive_present(path):
    """L'archive est-elle sur la machine ? (indicateur, jamais une copie)."""
    if not path:
        return False
    full = os.path.join(APP_DIR, path) if not os.path.isabs(path) else path
    return os.path.isfile(full)


def fiche_for(eid):
    e = BY_ID.get(eid)
    if e is None:
        return None
    out = card_for(e)
    out.update({
        "theme": e.get("theme"),
        "fields": e.get("fields", {}),
        "documentary_fields": e.get("documentary_fields", {}),
        "u8_adaptation": e.get("u8_adaptation"),
        "u8_proposed_settings": e.get("u8_proposed_settings"),
        "participants_scope": e.get("participants_scope"),
        "age_source": e.get("age_source"),
        "source": e.get("source"),
        "locator": e.get("locator"),
        "references": e.get("references"),
        "observation": e.get("observation"),
        "coach_cues": e.get("coach_cues"),
        "source_conflicts": e.get("source_conflicts"),
        "bout_seconds": e.get("bout_seconds"),
        "preparation_questions": e.get("preparation_questions"),
        "planning_duration": e.get("planning_duration"),
        "tagging": e.get("tagging"),
        "missing_review": e.get("missing_review"),
        "duplicate_review": e.get("duplicate_review"),
        "session_uses": e.get("session_uses", []),
        "warmup_usage": e.get("warmup_usage"),
        "quality": e["quality"],
    })
    return out


def catalogue_view():
    return {
        "schema_version": PAYLOAD.get("schema_version"),
        "field_names": PAYLOAD.get("field_names"),
        "families": PAYLOAD.get("families"),
        "canonical_game_groups": PAYLOAD.get("canonical_game_groups"),
        "summary": PAYLOAD.get("summary"),
        "policy": PAYLOAD.get("policy"),
        "tag_taxonomy": PAYLOAD.get("tag_taxonomy"),
        "warmup_collection": PAYLOAD.get("warmup_collection"),
        # Le catalogue complet (fiches non visibles par défaut comprises) :
        # le front réapplique la même sélection que select_catalogue (miroir
        # testé dans web/lib/filter.ts) et pilote lui-même l'interrupteur
        # « incomplètes ». Livrer seulement les visibles rendrait cet
        # interrupteur hors d'usage côté client.
        "cards": select_catalogue(include_incomplete=True),
    }


# ---------------------------------------------------------------------------
# WSGI
# ---------------------------------------------------------------------------

def _json_response(status, body):
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    return (
        f"{status.value} {status.phrase}",
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(payload))),
            ("Cache-Control", "no-store"),
        ],
        [payload],
    )


def _static_response(path):
    """Servir web/out/<path> avec garde anti path traversal + fallback SPA."""
    if path in ("", "/"):
        path = "/index.html"
    candidate = os.path.realpath(os.path.join(STATIC_DIR, path.lstrip("/")))
    if not candidate.startswith(os.path.realpath(STATIC_DIR) + os.sep) and \
       candidate != os.path.realpath(os.path.join(STATIC_DIR, "index.html")):
        return _error(404)
    if not os.path.isfile(candidate):
        index = os.path.join(STATIC_DIR, "index.html")
        if not os.path.isfile(index):
            return _error(404)
        candidate = index
    with open(candidate, "rb") as fh:
        data = fh.read()
    ctype = {
        ".html": "text/html; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".ico": "image/x-icon",
        ".txt": "text/plain; charset=utf-8",
    }.get(os.path.splitext(candidate)[1], "application/octet-stream")
    status = HTTPStatus.OK
    return (
        f"{status.value} {status.phrase}",
        [
            ("Content-Type", ctype),
            ("Content-Length", str(len(data))),
            ("Cache-Control", "no-cache" if candidate.endswith("index.html") else "public, max-age=300"),
        ],
        [data],
    )


def _error(code):
    status = HTTPStatus(code)
    payload = json.dumps({"error": status.description or "erreur"}, ensure_ascii=False).encode("utf-8")
    return (
        f"{status.value} {status.phrase}",
        [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(payload)))],
        [payload],
    )


def application(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET")

    if path == "/api/catalogue":
        status, headers, body = _json_response(HTTPStatus.OK, catalogue_view())
    elif path == "/api/recherche":
        qs = parse_qs(environ.get("QUERY_STRING", ""))
        query = (qs.get("q") or [""])[0].strip()
        tags = [t for t in (qs.get("tags") or [""])[0].split(",") if t]
        raw_match = (qs.get("match") or ["all"])[0]
        match = raw_match if raw_match in ("all", "any") else "all"
        # Défaut produit : les fiches incomplètes sont affichées (avec leur
        # badge d'état). `include_incomplete=false` les masque.
        include_incomplete = (qs.get("include_incomplete") or ["true"])[0].lower() not in ("0", "false", "non")
        raw_usage = (qs.get("usage") or [""])[0]
        usage = raw_usage or None
        results = select_catalogue(query=query, tag_ids=tags, match=match,
                                   include_incomplete=include_incomplete, usage=usage)
        status, headers, body = _json_response(HTTPStatus.OK, {"count": len(results), "cards": results})
    elif path.startswith("/api/fiches/"):
        eid = unquote(path[len("/api/fiches/"):]).strip("/")
        fiche = fiche_for(eid) if eid else None
        if fiche is None:
            status, headers, body = _json_response(HTTPStatus.NOT_FOUND, {"error": "fiche introuvable", "id": eid})
        else:
            status, headers, body = _json_response(HTTPStatus.OK, fiche)
    elif method == "GET" or method == "HEAD":
        status, headers, body = _static_response(path)
    else:
        status, headers, body = _error(405)

    start_response(status, headers)
    if method == "HEAD":
        return [b""]
    return body


def main():
    server = make_server(HOST, PORT, application)
    print(f"Lot 1 — Rugby Training Library : http://{HOST}:{PORT}")
    print(f"Vue catalogue : {len(EXERCISES)} fiches ; front statique : {STATIC_DIR}")
    try:
        server.serve_forever()
    except (KeyboardInterrupt, socket.error):
        print("\nArrêt du serveur.")


if __name__ == "__main__":
    main()
