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
  GET /api/seances/trame-u8   → trame de référence U8 70/90, préremplie
                                (data/session-draft.example.json)
  POST /api/seances/valider   → validation d'un brouillon de séance (JSON) :
                                erreurs bloquantes, avertissements non
                                bloquants, minutage dérivée (marge, total
                                d'opposition)
  POST /api/auth/inscription  → création de compte (lot 5, A1 : comptes
                                locaux hors-ligne) ; 201 + cookie de session
  POST /api/auth/login        → connexion ; 401 à message unique (compte
                                inconnu / mot de passe erroné indistincts)
  POST /api/auth/deconnexion  → fin de session (cookie purgé)
  GET  /api/moi               → compte courant ; 401 sans session
  GET|PUT|DELETE
     /api/brouillons[/id]     → brouillons du compte (lot 5, B1) ; 404, pas
                                403, sur les brouillons d'autrui (C1)
  GET|POST
     /api/propositions[/<id>] → propositions de séance du compte (lot 5, D1 :
                                snapshot immuable + résultat de validation)
  GET|POST
     /api/coachs[/<id>]       → coachs disponibles : union des comptes et
                                des coachs sans compte ajoutés par nom
                                (v1.1, 2026-11-24) ; POST {nom, club?} →
                                409 si doublon, DELETE → 404 ; 401 sans
                                session. Brouillons et propositions restent
                                strictement privés (C1)
  GET|POST
     /api/equipes[/<id>]      → équipes d'effectif du compte (nom requis,
                                club, catégorie, effectif et coachs
                                rattachés facultatifs — tailles flexibles) ;
                                PUT = mise à jour complète ; 404, pas 403,
                                sur les équipes d'autrui (C1)
  GET /api/conseils           → conseils coach (data/coach-cues.json, lu à
                                chaque requête ; fichier absent →
                                {"records": []} — le contenu s'ajoute sans
                                code ni redémarrage)
  PUT /api/club/theme         → identité du club actif (couleurs
                                hexadécimales + logo PNG/SVG en base64, lot
                                peaufinage B 2026-11-25, v2-cadrage §3.4) ;
                                commun au club, servi dans GET /api/moi
  GET /*                      → front statique (web/out/), fallback index.html

Tous les POST acceptent un corps JSON plafonné à 2 Mo (413 au-delà).
"""

import base64
import json
import os
import re
import socket
import socketserver
import unicodedata
from http import HTTPStatus
from urllib.parse import parse_qs, unquote

from wsgiref.simple_server import WSGIServer, make_server

import app_store
import session_plan


# M2 : un client malhonnête (longueur mentière sous le plafond) ne bloque plus
# la file — un thread par connexion (SQLite ouvert par requête).
# `ThreadingWSGIServer` a disparu de wsgiref en Python 3.14 : copie locale
# fidèle de l'ancienne classe stdlib.
class ThreadingWSGIServer(socketserver.ThreadingMixIn, WSGIServer):
    """WSGIServer threadé (un thread par connexion)."""

    daemon_threads = True

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(APP_DIR, "exports", "APPLICATION.json")
DRAFT_PATH = os.path.join(APP_DIR, "data", "session-draft.example.json")
# Conseils coach (tranché 2026-11-22) : lus à chaque requête — ajouter du
# contenu (data/coach-cues.json) ne demande aucun code ni redémarrage.
CUES_PATH = os.path.join(APP_DIR, "data", "coach-cues.json")
STATIC_DIR = os.path.join(APP_DIR, "web", "out")
HOST = "0.0.0.0"
PORT = 8347

# Lot 5 — plafond de corps commun à tous les POST (413 au-delà) ; la base
# d'état est dédiée (data/app.sqlite, gitignorée) et ouverte par requête.
MAX_BODY = 2 * 1000 * 1000


def app_db_path():
    """Chemin de la base d'état, lu à chaque appel.

    Fonction (pas constante) : les tests fixent RTRL_APP_DB vers un fichier
    temporaire après l'import du module.
    """
    return os.environ.get("RTRL_APP_DB") or os.path.join(APP_DIR, "data", "app.sqlite")

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


def _load_draft():
    """Trame de référence U8 (brouillon 70/90), lue à froid au démarrage.

    Le brouillon est un gabarit de départ pour la vue « Nouvelle séance »,
    pas une séance validée ni prête à lancer : les réglages (durées,
    effectifs, organisation) restent à ajuster dans la séance (lot 3).
    """
    with open(DRAFT_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


TRAME_U8 = _load_draft()


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

    La sémantique des tags est identique à exercise_tags.select
    (« all » = tous les tags demandés présents ; « any » = au moins un),
    sauf un écart délibéré : un tag inconnu donne 0 carte ici (le filtre
    est permissif, l'API répond 200 avec une liste vide) là où
    exercise_tags.select lève ValueError (« Filtre inconnu ») — la vue
    utilisateur n'a pas à connaître le taxon en avance, le validateur
    catalogue oui. Les fiches incomplètes sont affichées par défaut
    (défaut produit : tout le catalogue, avec badge d'état) ; usage =
    « WARMUP » restreint à session_uses.
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
        "video_link": media_link_for(e),
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


def media_link_for(e):
    """Lien vidéo attaché à la fiche lors de la relecture (172 fiches, 2026-11-22).

    Provenance : data/media-links-20261122.json, contrôlée à la charge
    (application_data.build). Trois états possibles :
    - url + is_variant False : l'exercice filmé (source documentaire ou
      recherche) ;
    - url + is_variant True : variante filmée, l'écart est annoncé dans
      variant_note ;
    - url None : pas de lien, pas de variante — déclaré tel quel.
    Distinct de media_for (suppléments PDF) ; les deux restent visibles.
    """
    link = PAYLOAD.get("media_links", {}).get(e["id"])
    if not link or not link.get("url"):
        return None
    return {
        "url": link["url"],
        "title": link.get("title"),
        "is_variant": link["is_variant"],
        "variant_note": link.get("variant_note"),
        "origin": link["origin"],
    }


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


def valider_seance(plan):
    """Valider un brouillon de séance et retourner le détail pour l'UI.

    `session_plan.validate` renvoie une liste mélangée d'erreurs bloquantes
    (sans préfixe) et d'avertissements (préfixe « Avertissement — »). On les
    sépare ici : les avertissements sont informatifs (dépassement du créneau,
    total partiel) et n'empêchent pas la séance ; les erreurs bloquantes
    l'empêchent. On ajoute la minutage dérivée (marge, opposition).
    """
    try:
        erreurs = session_plan.validate(plan, PAYLOAD)
    except session_plan.PlanMalforme:
        raise
    except (KeyError, TypeError, AttributeError) as exc:
        # Filet M1 : un champ manquant/inattendu côté brouillon est une erreur
        # utilisateur → 400 lisible (« Plan malformé »), jamais 500.
        raise session_plan.PlanMalforme(str(exc))
    bloquantes = [m for m in erreurs if not m.startswith("Avertissement")]
    avertissements = [m for m in erreurs if m.startswith("Avertissement")]
    return {
        "valide": not bloquantes,
        "erreurs": bloquantes,
        "avertissements": avertissements,
        "minutage": minutage_derivee(plan),
    }


def minutage_derivee(plan):
    """Minutage dérivée pour l'affichage, jamais stockée.

    - `creneau_min` : la fenêtre totale (90 min).
    - `planifie_min` : somme des durées de blocs connues.
    - `marge_min` : créneau − planifié (peut être négative → dépassement).
    - `opposition_min` : somme des blocs d'opposition (Jeu inclus, la
      trame compte « opposition » comme tout bloc de Jeu/Atelier en
      condition d'opposition).
    """
    blocks = plan.get("blocks", [])
    # m1 : durées normalisées par session_plan.entier (flottants entiers →
    # entier strict), identiques au miroir front (Number.isInteger) — l'ancien
    # code comptait 7.0 dans opposition mais pas dans planifie (incohérence).
    durees = [session_plan.entier(b.get("duration_min")) for b in blocks]
    planifie = sum(d for d in durees if d is not None)
    creneau = session_plan.entier(plan.get("creneau_min")) or 0
    opposition = sum(
        session_plan.entier(b.get("duration_min")) or 0
        for b in blocks
        if b.get("kind") in ("OPPOSITION", "JEU")
    )
    return {
        "creneau_min": creneau,
        "planifie_min": planifie,
        "marge_min": creneau - planifie,
        "opposition_min": opposition,
        "partiel": any(d is None for d in durees),
    }


# ---------------------------------------------------------------------------
# WSGI
# ---------------------------------------------------------------------------

def _json_response(status, body, set_cookie=None):
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(payload))),
        ("Cache-Control", "no-store"),
    ]
    if set_cookie is not None:
        headers.append(("Set-Cookie", set_cookie))
    return f"{status.value} {status.phrase}", headers, [payload]


def _static_response(path):
    """Servir web/out/<path> avec garde anti path traversal + fallback SPA."""
    if path in ("", "/"):
        path = "/index.html"
    candidate = os.path.realpath(os.path.join(STATIC_DIR, path.lstrip("/")))
    # URL propre (ex. /connexion) → résolution vers connexion.html. Sans ce test,
    # le fichier « connexion » (sans extension) n'existant pas, le fallback SPA
    # renvoyait index.html (le catalogue) au lieu du formulaire de connexion.
    if not os.path.isfile(candidate) and os.path.isfile(candidate + ".html"):
        candidate = candidate + ".html"
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


# ---------------------------------------------------------------------------
# Lot 5 — authentification et état applicatif (app_store)
# ---------------------------------------------------------------------------

def _cookie_value(environ, name):
    """Valeur du cookie `name` dans HTTP_COOKIE, ou None."""
    for part in environ.get("HTTP_COOKIE", "").split(";"):
        key, _, value = part.strip().partition("=")
        if key == name:
            return value
    return None


def _session_cookie(token):
    """Cookie de session : HttpOnly (jamais lisible par le front), SameSite=Lax."""
    return (
        f"{app_store.COOKIE_NAME}={token}; HttpOnly; Path=/; "
        f"SameSite=Lax; Max-Age={app_store.SESSION_SECONDS}"
    )


def _clear_session_cookie():
    return f"{app_store.COOKIE_NAME}=; HttpOnly; Path=/; SameSite=Lax; Max-Age=0"


def _require_account(environ, store):
    """Compte (dict) si le cookie de session est valide, sinon None."""
    account_id = store.check_session_token(_cookie_value(environ, app_store.COOKIE_NAME))
    if account_id is None:
        return None
    return store.get_account(account_id)


def _read_json_body(environ):
    """Corps JSON borné : (HTTPStatus, {"error": …}) en cas d'échec,
    (None, valeur) sinon. Plafond commun à tous les POST (2 Mo)."""
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        length = 0
    if length > MAX_BODY:
        return HTTPStatus(413), {"error": "Corps de requête trop volumineux (2 Mo maximum)."}
    if length < 0:
        # M2 : une longueur négative bloquait le read tant que la connexion
        # restait ouverte ; refusée d'abord, 400 lisible.
        return HTTPStatus.BAD_REQUEST, {"error": "Longueur de requête invalide."}
    raw = environ["wsgi.input"].read(length) if length else b""
    if not raw:
        return HTTPStatus.BAD_REQUEST, {"error": "Corps de requête vide."}
    try:
        return None, json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return HTTPStatus.BAD_REQUEST, {"error": "Corps JSON invalide."}


def _route_inscription(environ):
    """POST /api/auth/inscription → 201 + cookie de session (A1)."""
    err, data = _read_json_body(environ)
    if err is not None:
        return _json_response(err, data)
    if not isinstance(data, dict):
        return _json_response(HTTPStatus.BAD_REQUEST, {"error": "Identifiant et mot de passe requis."})
    login = data.get("login")
    password = data.get("password")
    try:
        app_store.normalize_login(login)
    except ValueError:
        return _json_response(
            HTTPStatus.BAD_REQUEST,
            {"error": "Identifiant invalide (2 à 32 caractères : lettres, chiffres, « . _ - », sans espace ni accent)."},
        )
    if not app_store.password_ok(password):
        return _json_response(
            HTTPStatus.BAD_REQUEST,
            {"error": "Mot de passe invalide (8 caractères minimum, 128 maximum)."},
        )
    # Lot club (cadrage 03, A/A/A/A) : deux champs facultatifs, validés.
    club = data.get("club")
    if club is not None and isinstance(club, str) and not club.strip():
        club = None  # «   » → absent
    if not app_store.club_ok(club):
        return _json_response(
            HTTPStatus.BAD_REQUEST,
            {"error": "Club invalide (texte de 80 caractères maximum, ou champ absent)."},
        )
    categorie = data.get("categorie")
    if not app_store.categorie_ok(categorie):
        return _json_response(
            HTTPStatus.BAD_REQUEST,
            {"error": "Catégorie invalide (liste : " + ", ".join(app_store.CATEGORIES) + ", ou champ absent)."},
        )
    with app_store.AppStore(app_db_path()) as store:
        try:
            compte = store.create_account(login, password, club, categorie)
        except app_store.AccountExists:
            return _json_response(HTTPStatus.CONFLICT, {"error": "Cet identifiant est déjà utilisé."})
        token = store.make_session_token(compte["id"])
    return _json_response(
        HTTPStatus.CREATED,
        {
            "login": compte["login"],
            "created_at": compte["created_at"],
            "club": compte["club"],
            "categorie": compte["categorie"],
        },
        _session_cookie(token),
    )


def _route_login(environ):
    """POST /api/auth/login → 200 + cookie, ou 401 à message unique
    (compte inconnu / mot de passe erroné indistincts, anti-énumération)."""
    err, data = _read_json_body(environ)
    if err is not None:
        return _json_response(err, data)
    if not isinstance(data, dict):
        return _json_response(HTTPStatus.BAD_REQUEST, {"error": "Identifiant et mot de passe requis."})
    with app_store.AppStore(app_db_path()) as store:
        compte = store.authenticate(data.get("login"), data.get("password"))
        if compte is None:
            return _json_response(HTTPStatus.UNAUTHORIZED, {"error": "Identifiant ou mot de passe incorrect."})
        token = store.make_session_token(compte["id"])
    return _json_response(HTTPStatus.OK, {"login": compte["login"]}, _session_cookie(token))


def _route_deconnexion(environ):
    """POST /api/auth/deconnexion → purge du cookie (déconnexion = retrait)."""
    return _json_response(HTTPStatus.OK, {"ok": True}, _clear_session_cookie())


def _route_moi(environ):
    """GET /api/moi → compte courant (login, club et catégorie facultatifs,
    + identité du club actif — lot peaufinage B ; null si le club n'en a
    pas), ou 401 sans session."""
    with app_store.AppStore(app_db_path()) as store:
        compte = _require_account(environ, store)
        if compte is None:
            return _json_response(HTTPStatus.UNAUTHORIZED, {"error": "Authentification requise."})
        theme = store.get_club_theme(compte["club"]) if compte["club"] else None
    return _json_response(
        HTTPStatus.OK,
        {
            "login": compte["login"],
            "created_at": compte["created_at"],
            "club": compte["club"],
            "categorie": compte["categorie"],
            "theme": theme,
        },
    )


def _route_club_theme(environ):
    """PUT /api/club/theme → identité du club actif (lot peaufinage B,
    2026-11-25 ; v2-cadrage §3.4, option A). Corps :
    {"couleurs": {"primary": "#0b5d3b", "secondary": "#..." | null,
    "accent": "#..." | null}, "logo": base64 | null} — logo null/absent
    supprime l'ancien. L'identité est commune au club (clé = nom du club) ;
    elle est servie par GET /api/moi, qui applique le thème à toute la
    surface de l'app côté client (web/lib/theme.ts)."""
    err, data = _read_json_body(environ)
    if err is not None:
        return _json_response(err, data)
    if not isinstance(data, dict):
        return _json_response(HTTPStatus.BAD_REQUEST, {"error": "Identité du club JSON attendue."})
    with app_store.AppStore(app_db_path()) as store:
        compte = _require_account(environ, store)
        if compte is None:
            return _json_response(HTTPStatus.UNAUTHORIZED, {"error": "Authentification requise."})
        if not compte["club"]:
            return _json_response(
                HTTPStatus.BAD_REQUEST,
                {"error": "Impossible de définir une identité sans club renseigné."},
            )
        couleurs = data.get("couleurs")
        if not isinstance(couleurs, dict):
            return _json_response(HTTPStatus.BAD_REQUEST, {"error": "Couleurs attendues (hexadécimales #RRGGBB)."})
        primary = couleurs.get("primary")
        if primary is None or not app_store.couleur_ok(primary):
            return _json_response(HTTPStatus.BAD_REQUEST, {"error": "La couleur principale est requise (hexadécimale #RRGGBB)."})
        secondaire = couleurs.get("secondary")
        accent = couleurs.get("accent")
        if secondaire in ("", "null"):
            secondaire = None
        if accent in ("", "null"):
            accent = None
        for cle, valeur in (("secondaire", secondaire), ("accent", accent)):
            if valeur is not None and not app_store.couleur_ok(valeur):
                return _json_response(HTTPStatus.BAD_REQUEST, {"error": "Couleur %s invalide (hexadécimale #RRGGBB attendue)." % cle})
        logo_raw = data.get("logo")
        logo = None
        logo_mime = None
        if logo_raw not in (None, ""):
            if not isinstance(logo_raw, str):
                return _json_response(HTTPStatus.BAD_REQUEST, {"error": "Logo invalide (base64 attendu)."})
            try:
                logo = base64.b64decode(logo_raw, validate=True)
            except (ValueError, TypeError):
                return _json_response(HTTPStatus.BAD_REQUEST, {"error": "Logo invalide (base64 illisible)."})
            logo_mime = app_store.mime_logo(logo)
            if logo_mime is None or not app_store.logo_ok(logo, logo_mime):
                return _json_response(HTTPStatus.BAD_REQUEST, {"error": "Logo refusé (PNG ou SVG statique, 500 Ko maximum)."})
        theme = store.set_club_theme(
            compte["club"],
            {"primary": primary, "secondary": secondaire, "accent": accent},
            logo,
            logo_mime,
        )
    return _json_response(HTTPStatus.OK, {"theme": theme})


def _route_brouillons(environ):
    """GET /api/brouillons ; GET|PUT|DELETE /api/brouillons/<id> (B1, C1)."""
    method = environ.get("REQUEST_METHOD", "GET")
    parts = [unquote(p) for p in environ["PATH_INFO"].split("/") if p]
    with app_store.AppStore(app_db_path()) as store:
        compte = _require_account(environ, store)
        if compte is None:
            return _json_response(HTTPStatus.UNAUTHORIZED, {"error": "Authentification requise."})
        if len(parts) == 2:
            if method != "GET":
                return _error(405)
            return _json_response(HTTPStatus.OK, {"brouillons": store.list_drafts(compte["id"])})
        if len(parts) != 3:
            return _json_response(HTTPStatus.BAD_REQUEST, {"error": "Identifiant de brouillon invalide."})
        draft_id = parts[2]
        if not app_store.draft_id_ok(draft_id):
            return _json_response(HTTPStatus.BAD_REQUEST, {"error": "Identifiant de brouillon invalide."})
        if method == "GET":
            brouillon = store.get_draft(compte["id"], draft_id)
            if brouillon is None:
                return _json_response(HTTPStatus.NOT_FOUND, {"error": "Brouillon introuvable."})
            return _json_response(HTTPStatus.OK, brouillon)
        if method == "PUT":
            err, data = _read_json_body(environ)
            if err is not None:
                return _json_response(err, data)
            if not isinstance(data, dict) or not isinstance(data.get("plan"), dict):
                return _json_response(HTTPStatus.BAD_REQUEST, {"error": "Plan de séance requis (objet JSON)."})
            titre = data.get("titre")
            if not (isinstance(titre, str) and titre.strip()):
                existing = store.get_draft(compte["id"], draft_id)
                plan_title = data["plan"].get("title")
                if existing is not None:
                    titre = existing["titre"]
                elif isinstance(plan_title, str) and plan_title.strip():
                    titre = plan_title
                else:
                    titre = "Séance"
            return _json_response(
                HTTPStatus.OK,
                store.upsert_draft(compte["id"], draft_id, titre.strip(), data["plan"]),
            )
        if method == "DELETE":
            store.delete_draft(compte["id"], draft_id)
            return _json_response(HTTPStatus.OK, {"ok": True})
        return _error(405)


def _route_propositions(environ):
    """GET|POST /api/propositions ; GET /api/propositions/<id> (B1, D1)."""
    method = environ.get("REQUEST_METHOD", "GET")
    parts = [unquote(p) for p in environ["PATH_INFO"].split("/") if p]
    with app_store.AppStore(app_db_path()) as store:
        compte = _require_account(environ, store)
        if compte is None:
            return _json_response(HTTPStatus.UNAUTHORIZED, {"error": "Authentification requise."})
        if len(parts) == 2:
            if method == "GET":
                return _json_response(HTTPStatus.OK, {"propositions": store.list_proposals(compte["id"])})
            if method == "POST":
                err, data = _read_json_body(environ)
                if err is not None:
                    return _json_response(err, data)
                if not isinstance(data, dict) or not isinstance(data.get("plan"), dict):
                    return _json_response(HTTPStatus.BAD_REQUEST, {"error": "Plan de séance requis (objet JSON)."})
                titre = data.get("titre")
                if not (isinstance(titre, str) and titre.strip()):
                    plan_title = data["plan"].get("title")
                    titre = plan_title if isinstance(plan_title, str) and plan_title.strip() else "Séance"
                try:
                    check = valider_seance(data["plan"])
                except session_plan.PlanMalforme as exc:
                    # Brouillon malformé → 400 lisible, proposition non sauvegardée.
                    return _json_response(
                        HTTPStatus.BAD_REQUEST, {"error": "Plan malformé : " + str(exc)}
                    )
                res = store.save_proposal(compte["id"], titre.strip(), data["plan"], check)
                return _json_response(
                    HTTPStatus.CREATED,
                    {
                        "id": res["id"],
                        "titre": res["titre"],
                        "valide": res["valide"],
                        "erreurs": check["erreurs"],
                        "avertissements": check["avertissements"],
                        "minutage": check["minutage"],
                        "saved_at": res["saved_at"],
                    },
                )
            return _error(405)
        if len(parts) == 3 and parts[2].isdigit():
            if method != "GET":
                return _error(405)
            prop = store.get_proposal(compte["id"], int(parts[2]))
            if prop is None:
                return _json_response(HTTPStatus.NOT_FOUND, {"error": "Proposition introuvable."})
            return _json_response(HTTPStatus.OK, prop)
        return _json_response(HTTPStatus.NOT_FOUND, {"error": "Proposition introuvable."})


def _equipe_id(nom: str, existing: set) -> str:
    """Slug d'équipe dérivé du nom (sans accents, insensible à la casse) ;
    suffixé en cas de collision (« u8-1 », « u8-1-2 » …). Miroir simple du
    fold() de la recherche ; borné à 128 caractères (DRAFT_ID_RE)."""
    base = re.sub(r"[^a-z0-9]+", "-", fold(nom)).strip("-")
    if not base:
        base = "equipe"
    if len(base) > 128:
        base = base[:128]
    if base not in existing:
        return base
    n = 2
    while f"{base}-{n}" in existing:
        n += 1
    return f"{base}-{n}"


def _route_coachs(environ):
    """GET|POST /api/coachs ; DELETE /api/coachs/<id> — « coachs
    disponibles » : union des comptes et des coachs sans compte ajoutés par
    nom (tranché v1.1, 2026-11-24)."""
    method = environ.get("REQUEST_METHOD", "GET")
    parts = [unquote(p) for p in environ["PATH_INFO"].split("/") if p]
    coach_id = parts[2] if len(parts) > 2 else None
    with app_store.AppStore(app_db_path()) as store:
        compte = _require_account(environ, store)
        if compte is None:
            return _json_response(HTTPStatus.UNAUTHORIZED, {"error": "Authentification requise."})
        if coach_id is None:
            if method == "GET":
                return _json_response(HTTPStatus.OK, {"coachs": store.list_coaches()})
            if method == "POST":
                err, data = _read_json_body(environ)
                if err is not None:
                    return _json_response(err, data)
                if not isinstance(data, dict):
                    return _json_response(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "Objet JSON requis (nom du coach au minimum)."},
                    )
                try:
                    coach = store.ajouter_coach(
                        compte["id"], data.get("nom"), data.get("club")
                    )
                except app_store.CoachExists:
                    return _json_response(
                        HTTPStatus.CONFLICT,
                        {"error": "Un coach de ce nom existe déjà pour votre compte."},
                    )
                except ValueError as exc:
                    return _json_response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return _json_response(HTTPStatus.CREATED, coach)
            return _error(405)
        if len(parts) != 3:
            return _json_response(
                HTTPStatus.BAD_REQUEST, {"error": "Identifiant de coach invalide."}
            )
        if method != "DELETE":
            return _error(405)
        try:
            store.supprimer_coach(compte["id"], coach_id)
        except ValueError:
            return _json_response(HTTPStatus.NOT_FOUND, {"error": "Coach introuvable."})
        return _json_response(HTTPStatus.OK, {"ok": True})


def _route_conseils(environ):
    """GET /api/conseils → conseils coach (data/coach-cues.json).

    Lecture fraîche à chaque requête : ajouter ou corriger des conseils
    dans le fichier ne demande ni code ni redémarrage. Fichier absent ou
    illisible → {"records": []} : la section est vide, jamais bloquante.
    Contenu général de l'app (pas de données de compte) : pas
    d'authentification requise.
    """
    try:
        with open(CUES_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        data = {"version": 0, "scope": "", "records": []}
    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        data = {"version": 0, "scope": "", "records": []}
    return _json_response(HTTPStatus.OK, data)


def _route_equipes(environ):
    """GET|POST /api/equipes ; GET|PUT|DELETE /api/equipes/<id>
    (équipes d'effectif du compte, tranché 2026-11-22) ; 404, pas 403,
    sur les équipes d'autrui (C1)."""
    method = environ.get("REQUEST_METHOD", "GET")
    parts = [unquote(p) for p in environ["PATH_INFO"].split("/") if p]
    with app_store.AppStore(app_db_path()) as store:
        compte = _require_account(environ, store)
        if compte is None:
            return _json_response(HTTPStatus.UNAUTHORIZED, {"error": "Authentification requise."})
        if len(parts) == 2:
            if method == "GET":
                return _json_response(
                    HTTPStatus.OK, {"equipes": store.list_equipes(compte["id"])}
                )
            if method == "POST":
                err, data = _read_json_body(environ)
                if err is not None:
                    return _json_response(err, data)
                if not isinstance(data, dict):
                    return _json_response(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "Objet JSON requis (nom de l'équipe au minimum)."},
                    )
                team_id = data.get("id")
                if team_id is None:
                    nom = data.get("nom")
                    existing = {e["id"] for e in store.list_equipes(compte["id"])}
                    team_id = _equipe_id(nom if isinstance(nom, str) else "", existing)
                try:
                    equipe = store.upsert_equipe(
                        compte["id"], team_id, data.get("nom"),
                        data.get("club"), data.get("categorie"),
                        data.get("effectif"), data.get("coachs"),
                        data.get("joueurs"),
                    )
                except ValueError as exc:
                    return _json_response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return _json_response(HTTPStatus.CREATED, equipe)
            return _error(405)
        if len(parts) != 3:
            return _json_response(HTTPStatus.BAD_REQUEST, {"error": "Identifiant d'équipe invalide."})
        team_id = parts[2]
        if not app_store.draft_id_ok(team_id):
            return _json_response(HTTPStatus.BAD_REQUEST, {"error": "Identifiant d'équipe invalide."})
        if method == "GET":
            equipe = store.get_equipe(compte["id"], team_id)
            if equipe is None:
                return _json_response(HTTPStatus.NOT_FOUND, {"error": "Équipe introuvable."})
            return _json_response(HTTPStatus.OK, equipe)
        if method == "PUT":
            err, data = _read_json_body(environ)
            if err is not None:
                return _json_response(err, data)
            if not isinstance(data, dict):
                return _json_response(HTTPStatus.BAD_REQUEST, {"error": "Objet JSON requis."})
            try:
                equipe = store.upsert_equipe(
                    compte["id"], team_id, data.get("nom"),
                    data.get("club"), data.get("categorie"),
                    data.get("effectif"), data.get("coachs"),
                    data.get("joueurs"),
                )
            except ValueError as exc:
                return _json_response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return _json_response(HTTPStatus.OK, equipe)
        if method == "DELETE":
            store.delete_equipe(compte["id"], team_id)
            return _json_response(HTTPStatus.OK, {"ok": True})
        return _error(405)


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
    elif path == "/api/seances/trame-u8":
        status, headers, body = _json_response(HTTPStatus.OK, TRAME_U8)
    elif path == "/api/seances/valider":
        if method != "POST":
            status, headers, body = _error(405)
        else:
            err, plan = _read_json_body(environ)
            if err is not None:
                status, headers, body = _json_response(err, plan)
            elif not isinstance(plan, dict):
                status, headers, body = _json_response(
                    HTTPStatus.BAD_REQUEST, {"error": "brouillon de séance JSON attendu"}
                )
            else:
                try:
                    status, headers, body = _json_response(HTTPStatus.OK, valider_seance(plan))
                except session_plan.PlanMalforme as exc:
                    # M1 : brouillon malformé → 400 lisible, jamais 500.
                    status, headers, body = _json_response(
                        HTTPStatus.BAD_REQUEST, {"error": "Plan malformé : " + str(exc)}
                    )
    elif path in ("/api/auth/inscription", "/api/auth/login", "/api/auth/deconnexion"):
        # 405 explicite : sans cette branche, un GET tomberait dans le
        # fallback statique (index.html, 200).
        if method != "POST":
            status, headers, body = _error(405)
        elif path == "/api/auth/inscription":
            status, headers, body = _route_inscription(environ)
        elif path == "/api/auth/login":
            status, headers, body = _route_login(environ)
        else:
            status, headers, body = _route_deconnexion(environ)
    elif path == "/api/moi":
        if method != "GET":
            status, headers, body = _error(405)
        else:
            status, headers, body = _route_moi(environ)
    elif path == "/api/club/theme":
        # 405 explicite : sans cette branche, un GET tomberait dans le
        # fallback statique (index.html, 200).
        if method != "PUT":
            status, headers, body = _error(405)
        else:
            status, headers, body = _route_club_theme(environ)
    elif path == "/api/brouillons" or path.startswith("/api/brouillons/"):
        status, headers, body = _route_brouillons(environ)
    elif path == "/api/propositions" or path.startswith("/api/propositions/"):
        status, headers, body = _route_propositions(environ)
    elif path == "/api/coachs" or path.startswith("/api/coachs/"):
        status, headers, body = _route_coachs(environ)
    elif path == "/api/equipes" or path.startswith("/api/equipes/"):
        status, headers, body = _route_equipes(environ)
    elif path == "/api/conseils":
        if method != "GET":
            status, headers, body = _error(405)
        else:
            status, headers, body = _route_conseils(environ)
    elif method == "GET" or method == "HEAD":
        status, headers, body = _static_response(path)
    else:
        status, headers, body = _error(405)

    start_response(status, headers)
    if method == "HEAD":
        return [b""]
    return body


def main():
    # M2 : un client malhonnête (longueur mentière sous le plafond) ne bloque
    # plus la file — un thread par connexion (SQLite ouvert par requête).
    # Python 3.14 : WSGIServer hérite de HTTPServer ; make_server passe le
    # WSGIRequestHandler en position 2 et l'application via set_app.
    server = make_server(HOST, PORT, application, server_class=ThreadingWSGIServer)
    print(f"Lot 1 — Rugby Training Library : http://{HOST}:{PORT}")
    print(f"Vue catalogue : {len(EXERCISES)} fiches ; front statique : {STATIC_DIR}")
    try:
        server.serve_forever()
    except (KeyboardInterrupt, socket.error):
        print("\nArrêt du serveur.")


if __name__ == "__main__":
    main()
