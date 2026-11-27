"""Lot 5 — État applicatif : comptes, brouillons, propositions.

Premier store écrit de l'application (charter V1), distinct du catalogue
en lecture seule : base SQLite dédiée `data/app.sqlite` (gitignorée,
comme `web/out/`). Python standard uniquement (sqlite3, hashlib, hmac,
secrets).

Décisions du cadrage validé (02-cadrage-lot5-auth.md) :
- A1 : comptes locaux hors-ligne. Mot de passe haché PBKDF2-HMAC-SHA256
  (600 000 itérations, sel aléatoire 16 octets) ; session = jeton signé
  HMAC-SHA256 (clé générée à l'initialisation et conservée en base),
  expiration 30 jours ; déconnexion = retrait du cookie côté client.
- B1 : brouillons et propositions rattachés au compte.
- C1 : strictement privé — chaque compte ne voit que ses propres données.
- D1 : une proposition stocke un snapshot immuable (plan + résultat de
  validation au moment de l'enregistrement) ; l'évolution d'une fiche ne
  modifie pas rétroactivement les séances conservées.

Lot club (03-cadrage-club.md, A/A/A/A validé le 2026-11-20) : le compte
porte deux champs facultatifs — `club` (texte ≤ 80 caractères) et
`categorie` (liste contrôlée babys, U6…U18, Autre). Le club est un simple
libellé : il n'ouvre aucun accès (C1 inchangé).

Séances (tranché 2026-11-22) : une équipe est un dispositif d'effectif
rattaché au compte — identifiant slug, nom (seul champ obligatoire), club et
catégorie facultatifs (mêmes règles que le compte), effectif facultatif
(entier ≥ 0), coachs rattachés (logins enregistrés ou noms libres, duplis
retirés). Les tailles d'effectif varient d'un club à l'autre : tout est
flexible sauf le nom.

Coachs (tranché v1.1, 2026-11-24 ; filtre club, lot P2, 2026-11-26) : un coach sans compte est ajouté par nom
seul (2 à 80 caractères, club facultatif) dans la table `coachs`, clé
(compte_id, id) — chaque compte ne gère que ses propres coachs (C1
inchangé). La liste « coachs disponibles » est filtrée par le club du compte appelant : comptes du même club + coachs nommés du club + les coachs nommés du compte appelant, quel que soit leur libellé de club ; sans club : le compte et ses coachs nommés. Forme unifiée
{nom, login, club, categorie, id} : login = null pour un nom seul. Brouillons
et propositions restent strictement privés (C1 inchangé).

La connexion est ouverte et fermée par requête (l'API tourne en un thread par
connexion : `ThreadingWSGIServer`, voir webapp.py).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime, timezone

COOKIE_NAME = "rtrl_session"
SESSION_DAYS = 30
SESSION_SECONDS = SESSION_DAYS * 24 * 3600
PBKDF2_ITERATIONS = 600_000
MIN_PASSWORD = 8
MAX_PASSWORD = 128

# Lot club (cadrage 03) : club = texte facultatif ≤ 80 caractères ;
# catégorie = liste contrôlée, facultative.
MAX_CLUB = 80
CATEGORIES = ("babys", "U6", "U8", "U10", "U12", "U14", "U16", "U18", "Autre")

LOGIN_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,31}$")
DRAFT_ID_RE = re.compile(r"^[a-z0-9._-]{1,128}$", re.IGNORECASE)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS comptes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT NOT NULL UNIQUE,
    salt_hex TEXT NOT NULL,
    pw_hash_hex TEXT NOT NULL,
    created_at TEXT NOT NULL,
    club TEXT,
    categorie TEXT
);
CREATE TABLE IF NOT EXISTS brouillons (
    compte_id INTEGER NOT NULL,
    draft_id TEXT NOT NULL,
    titre TEXT NOT NULL,
    plan_json TEXT NOT NULL,
    saved_at TEXT NOT NULL,
    PRIMARY KEY (compte_id, draft_id)
);
CREATE TABLE IF NOT EXISTS propositions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    compte_id INTEGER NOT NULL,
    titre TEXT NOT NULL,
    plan_json TEXT NOT NULL,
    valide INTEGER NOT NULL,
    erreurs_json TEXT NOT NULL,
    avertissements_json TEXT NOT NULL,
    minutage_json TEXT NOT NULL,
    saved_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS equipes (
    id TEXT NOT NULL,
    compte_id INTEGER NOT NULL,
    nom TEXT NOT NULL,
    club TEXT,
    categorie TEXT,
    effectif INTEGER,
    coachs_json TEXT NOT NULL DEFAULT '[]',
    joueurs_json TEXT NOT NULL DEFAULT '[]',
    groupes_json TEXT NOT NULL DEFAULT '[]',
    saved_at TEXT NOT NULL,
    PRIMARY KEY (compte_id, id)
);
CREATE TABLE IF NOT EXISTS coachs (
    id TEXT NOT NULL,
    compte_id INTEGER NOT NULL,
    nom TEXT NOT NULL,
    club TEXT,
    saved_at TEXT NOT NULL,
    PRIMARY KEY (compte_id, id)
);
-- Lot peaufinage B (2026-11-25) : identité du club — couleurs + logo
-- (v2-cadrage §3.4, option A). Clé = nom du club (strip) : le thème est
-- commun à tous les comptes du club ; CREATE TABLE IF NOT EXISTS, donc
-- aucune migration pour les bases existantes.
CREATE TABLE IF NOT EXISTS clubs (
    club TEXT PRIMARY KEY,
    couleur_primary TEXT NOT NULL,
    couleur_secondaire TEXT,
    couleur_accent TEXT,
    logo_mime TEXT,
    logo BLOB,
    saved_at TEXT NOT NULL
);
-- Lot P3 (cadrage 05, 2026-11-26) : magasin joueurs par club — première
-- donnée partagée par club (D4). Clé = nom du club (strip, même règle que
-- clubs) : la brique est commune à tous les comptes du club ; l'entité club
-- du v2 (V0) l'absorbe telle quelle (nom → club_id). Joueur = prénom + nom
-- uniquement (RGPD v1.1) : aucun autre champ accepté ni stocké.
CREATE TABLE IF NOT EXISTS joueurs_club (
    club TEXT NOT NULL,
    joueur TEXT NOT NULL,
    saved_at TEXT NOT NULL,
    PRIMARY KEY (club, joueur)
);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class AccountExists(Exception):
    """Login déjà enregistré (→ HTTP 409 côté API)."""


class CoachExists(Exception):
    """Nom de coach déjà présent pour le compte (→ HTTP 409 côté API)."""


class JoueurExists(Exception):
    """Joueur déjà présent pour le club (→ HTTP 409 côté API)."""


def normalize_login(login: str) -> str:
    """Normalise (trim + minuscules) et valide le login.

    Lève ValueError si le login normalisé n'est pas composé de 2 à 32
    caractères parmi lettres, chiffres, « . _ - » (sans espace ni accent).
    """
    if not isinstance(login, str):
        raise ValueError(login)
    login = login.strip().lower()
    if not LOGIN_RE.fullmatch(login):
        raise ValueError(login)
    return login


def normalize_coach_name(nom) -> str:
    """Nom d'un coach sans compte (tranché v1.1, 2026-11-24) : texte libre,
    trim + espaces internes ramenés à un seul, 2 à 80 caractères.

    Indépendant de normalize_login : un nom contient espaces et accents, un
    login non. Lève ValueError sinon.
    """
    if not isinstance(nom, str):
        raise ValueError(nom)
    nom = " ".join(nom.split())
    if not (2 <= len(nom) <= MAX_CLUB):
        raise ValueError(nom)
    return nom


def normalize_player_name(nom) -> str:
    """Joueur d'une équipe enregistrée (lot L3, v1.1) : prénom + nom,
    même forme que normalize_coach_name — texte, trim + espaces internes
    ramenés à un seul, 2 à 80 caractères. RGPD v1.1 : rien d'autre n'est
    collecté (le formulaire n'a pas d'autre champ joueur). Lève ValueError
    sinon.
    """
    return normalize_coach_name(nom)


def password_ok(password) -> bool:
    return isinstance(password, str) and MIN_PASSWORD <= len(password) <= MAX_PASSWORD


def club_ok(club) -> bool:
    """Nom de club : absent (None) ou texte de ≤ MAX_CLUB caractères."""
    if club is None:
        return True
    return isinstance(club, str) and len(club.strip()) <= MAX_CLUB


# Lot peaufinage B (2026-11-25) — identité du club (v2-cadrage §3.4, option A) :
# couleurs hexadécimales + logo PNG ou SVG statique ≤ 500 Ko. Le logo est une
# marque du club, pas une donnée personnelle (pas de contrainte RGPD).
COULEUR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
LOGO_MAX_OCTETS = 500 * 1000
_MIME_LOGO = ("image/png", "image/svg+xml")
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_SVG_DYNAMIQUE_RE = re.compile(r"(<script|javascript:|on\w+\s*=)", re.IGNORECASE)


def couleur_ok(couleur) -> bool:
    """Couleur du club : absente (None) ou hexadécimale #RRGGBB."""
    if couleur is None:
        return True
    return isinstance(couleur, str) and COULEUR_RE.fullmatch(couleur) is not None


def mime_logo(data):
    """Format du logo d'après les octets seuls (v2-cadrage §3.4 : le type,
    la taille, pas d'exécutables) : « image/png » (signature), « image/svg+xml »
    (texte UTF-8 commençant par <svg ou <?xml), ou None."""
    if not data or not isinstance(data, (bytes, bytearray)):
        return None
    if data.startswith(_PNG_MAGIC):
        return "image/png"
    try:
        texte = bytes(data).decode("utf-8")
    except UnicodeDecodeError:
        return None
    debut = texte.lstrip()
    if debut.startswith("<svg") or debut.startswith("<?xml"):
        return "image/svg+xml"
    return None


def logo_ok(data, mime) -> bool:
    """Logo du club : PNG ou SVG UTF-8 statique, ≤ 500 Ko.

    Le SVG est du texte : on refuse scripts, URIs javascript: et attributs
    événementiels (onload=…). Pas de décodage PNG complet — la signature et
    la taille suffisent au périmètre (v2-cadrage §3.4).
    """
    if mime_logo(data) != mime or len(data) > LOGO_MAX_OCTETS:
        return False
    if mime == "image/svg+xml":
        return _SVG_DYNAMIQUE_RE.search(data.decode("utf-8")) is None
    return True


def categorie_ok(categorie) -> bool:
    """Catégorie : absente (None) ou présente dans la liste contrôlée."""
    return categorie is None or categorie in CATEGORIES


def draft_id_ok(draft_id) -> bool:
    return isinstance(draft_id, str) and bool(DRAFT_ID_RE.fullmatch(draft_id))


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)


class AppStore:
    """Accès à la base d'état ; ouverte et fermée par requête."""

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.executescript(_SCHEMA)
        self._migrate_comptes()
        self._migrate_equipes()
        self._session_key = self._load_session_key()

    # -------------------------------------------------------------- cycle
    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "AppStore":
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    # ----------------------------------------------------------- migration
    def _migrate_comptes(self) -> None:
        """Migration idempotente (lot club) : ajoute `club` et `categorie`
        sur une base créée avant le lot ; sans effet sur une base neuve
        (les colonnes sont déjà dans le schéma)."""
        colonnes = {
            row[1] for row in self.conn.execute("PRAGMA table_info(comptes)")
        }
        if "club" not in colonnes:
            self.conn.execute("ALTER TABLE comptes ADD COLUMN club TEXT")
        if "categorie" not in colonnes:
            self.conn.execute("ALTER TABLE comptes ADD COLUMN categorie TEXT")

    def _migrate_equipes(self) -> None:
        """Migrations idempotentes : ajoute `joueurs_json` (lot L3, v1.1) et
        `groupes_json` (lot peaufinage C, 2026-11-25) sur une base créée
        avant les lots ; sans effet sur une base neuve (les colonnes sont
        déjà dans le schéma)."""
        colonnes = {
            row[1] for row in self.conn.execute("PRAGMA table_info(equipes)")
        }
        if "joueurs_json" not in colonnes:
            self.conn.execute(
                "ALTER TABLE equipes ADD COLUMN joueurs_json TEXT NOT NULL "
                "DEFAULT '[]'"
            )
        if "groupes_json" not in colonnes:
            self.conn.execute(
                "ALTER TABLE equipes ADD COLUMN groupes_json TEXT NOT NULL "
                "DEFAULT '[]'"
            )

    # ------------------------------------------------------ clé de session
    def _load_session_key(self) -> bytes:
        row = self.conn.execute(
            "SELECT value FROM meta WHERE key = 'session_key'"
        ).fetchone()
        if row is not None:
            return bytes.fromhex(row[0])
        key = secrets.token_hex(32)
        self.conn.execute(
            "INSERT INTO meta (key, value) VALUES ('session_key', ?)", (key,)
        )
        self.conn.commit()
        return bytes.fromhex(key)

    # ------------------------------------------------------------- comptes
    def create_account(
        self,
        login: str,
        password: str,
        club: str | None = None,
        categorie: str | None = None,
    ) -> dict:
        """Crée un compte (lot club : `club` et `categorie` facultatifs).

        `club` : texte de ≤ MAX_CLUB caractères (un club vide est stocké
        comme NULL) ; `categorie` : une valeur de la liste contrôlée
        CATEGORIES. Lève ValueError si un champ est invalide.
        """
        login = normalize_login(login)
        if not password_ok(password):
            raise ValueError(password)
        if club is not None:
            if not isinstance(club, str):
                raise ValueError("Le nom du club doit être un texte.")
            club = club.strip() or None
            if club is not None and len(club) > MAX_CLUB:
                raise ValueError("Le nom du club est trop long (80 caractères maximum).")
        if not categorie_ok(categorie):
            raise ValueError(
                "Catégorie invalide (attendue : " + ", ".join(CATEGORIES) + " ou absente)."
            )
        salt = secrets.token_bytes(16)
        pw_hash = _hash_password(password, salt)
        now = _utcnow_iso()
        try:
            cur = self.conn.execute(
                "INSERT INTO comptes (login, salt_hex, pw_hash_hex, created_at, "
                "club, categorie) VALUES (?, ?, ?, ?, ?, ?)",
                (login, salt.hex(), pw_hash.hex(), now, club, categorie),
            )
        except sqlite3.IntegrityError:
            raise AccountExists(login)
        self.conn.commit()
        return {
            "id": cur.lastrowid,
            "login": login,
            "created_at": now,
            "club": club,
            "categorie": categorie,
        }

    def get_account(self, account_id: int):
        row = self.conn.execute(
            "SELECT id, login, created_at, club, categorie FROM comptes "
            "WHERE id = ?",
            (account_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "login": row[1],
            "created_at": row[2],
            "club": row[3],
            "categorie": row[4],
        }

    def list_coaches(self, compte_id: int, club: str | None = None):
        """Liste « coachs disponibles » pour le compte appelant (filtre
        club, lot P2, cadrage 05, 2026-11-26) :
        - compte avec club C : comptes de club C + coachs nommés de club C
          (+ les coachs nommés du compte appelant, quel que soit leur
          libellé de club) ;
        - compte sans club : lui-même + ses coachs nommés.
        L'union globale inter-clubs n'est plus restituée. Forme unifiée
        {nom, login, club, categorie, id} — login = null et id = slug pour
        un nom seul (le slug est nécessaire au retrait par
        DELETE /api/coachs/<id> — lot L4, 2026-11-25) ; id = null pour un
        compte. Brouillons et propositions d'autrui restent strictement
        privés (C1).
        """
        if club is None:
            comptes = self.conn.execute(
                "SELECT login, club, categorie FROM comptes WHERE id = ? ORDER BY login",
                (compte_id,),
            )
            nommes = self.conn.execute(
                "SELECT id, nom, club FROM coachs WHERE compte_id = ? ORDER BY nom",
                (compte_id,),
            )
        else:
            comptes = self.conn.execute(
                "SELECT login, club, categorie FROM comptes WHERE club = ? ORDER BY login",
                (club,),
            )
            nommes = self.conn.execute(
                "SELECT id, nom, club FROM coachs "
                "WHERE club = ? OR compte_id = ? ORDER BY nom",
                (club, compte_id),
            )
        return [
            {"nom": r[0], "login": r[0], "club": r[1], "categorie": r[2], "id": None}
            for r in comptes
        ] + [
            {"nom": r[1], "login": None, "club": r[2], "categorie": None, "id": r[0]}
            for r in nommes
        ]

    def ajouter_coach(self, account_id: int, nom, club: str | None = None) -> dict:
        """Ajoute un coach sans compte au compte (tranché v1.1, 2026-11-24) :
        nom libre (2 à 80 caractères) + club facultatif. Lève ValueError si
        le nom (ou le club) est invalide, CoachExists si un coach de ce nom
        existe déjà pour le compte — comparaison insensible à la casse : un
        doublon est un nom mal orthographié, on le corrige en supprimant.
        """
        nom = normalize_coach_name(nom)
        if club is not None:
            if not isinstance(club, str):
                raise ValueError("Le club doit être un texte (80 caractères maximum).")
            club = club.strip() or None
            if club is not None and len(club) > MAX_CLUB:
                raise ValueError("Le nom du club est trop long (80 caractères maximum).")
        if self.conn.execute(
            "SELECT 1 FROM coachs WHERE compte_id = ? AND nom = ? COLLATE NOCASE",
            (account_id, nom),
        ).fetchone() is not None:
            raise CoachExists(nom)
        base = re.sub(r"[^a-z0-9]+", "-", nom.lower()).strip("-") or "coach"
        coach_id, n = base, 2
        while self.conn.execute(
            "SELECT 1 FROM coachs WHERE compte_id = ? AND id = ?",
            (account_id, coach_id),
        ).fetchone():
            coach_id = f"{base}-{n}"
            n += 1
        now = _utcnow_iso()
        self.conn.execute(
            "INSERT INTO coachs (id, compte_id, nom, club, saved_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (coach_id, account_id, nom, club, now),
        )
        self.conn.commit()
        return {"id": coach_id, "nom": nom, "club": club, "saved_at": now}

    def supprimer_coach(self, account_id: int, coach_id: str) -> None:
        """Supprime un coach nommé du compte (les comptes ne sont pas
        supprimables ici). Lève ValueError si le coach est inconnu."""
        cur = self.conn.execute(
            "DELETE FROM coachs WHERE compte_id = ? AND id = ?",
            (account_id, coach_id),
        )
        if cur.rowcount != 1:
            raise ValueError("Coach inconnu.")
        self.conn.commit()

    def authenticate(self, login, password):
        """Compte (dict) si le login ET le mot de passe sont corrects, sinon
        None. Le hachage est calculé même si le compte est absent, afin de
        ne pas créer de fuite par chronométrie."""
        norm = None
        if isinstance(login, str):
            try:
                norm = normalize_login(login)
            except ValueError:
                norm = None
        row = None
        if norm is not None:
            row = self.conn.execute(
                "SELECT id, salt_hex, pw_hash_hex FROM comptes WHERE login = ?",
                (norm,),
            ).fetchone()
        if row is None:
            if not isinstance(password, str):
                password = ""
            _hash_password(password, b"\x00" * 16)
            return None
        computed = _hash_password(password, bytes.fromhex(row[1]))
        if not hmac.compare_digest(computed, bytes.fromhex(row[2])):
            return None
        return self.get_account(row[0])

    # ---------------------------------------------------- session signée
    def make_session_token(self, account_id: int, ttl_seconds: int | None = None) -> str:
        """Jeton « <compte_id>.<expiration_epoch>.<signature HMAC-SHA256> »."""
        ttl = SESSION_SECONDS if ttl_seconds is None else ttl_seconds
        expiry = int(time.time()) + ttl
        payload = f"{int(account_id)}.{expiry}".encode("ascii")
        sig = hmac.new(self._session_key, payload, hashlib.sha256).hexdigest()
        return f"{int(account_id)}.{expiry}.{sig}"

    def check_session_token(self, token):
        """Identifiant du compte si le jeton est valide (3 parties, entiers,
        signature exacte, non expiré, compte toujours présent), sinon None."""
        if not isinstance(token, str):
            return None
        parts = token.split(".")
        if len(parts) != 3:
            return None
        try:
            account_id = int(parts[0])
            expiry = int(parts[1])
        except ValueError:
            return None
        payload = f"{account_id}.{expiry}".encode("ascii")
        expected = hmac.new(self._session_key, payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(parts[2], expected):
            return None
        if expiry <= time.time():
            return None
        row = self.conn.execute(
            "SELECT id FROM comptes WHERE id = ?", (account_id,)
        ).fetchone()
        return account_id if row is not None else None

    # ---------------------------------------------------------- brouillons
    def upsert_draft(self, account_id: int, draft_id: str, titre: str, plan) -> dict:
        now = _utcnow_iso()
        plan_json = json.dumps(plan, ensure_ascii=False)
        self.conn.execute(
            "INSERT INTO brouillons (compte_id, draft_id, titre, plan_json, saved_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (compte_id, draft_id) DO UPDATE SET "
            "titre = excluded.titre, plan_json = excluded.plan_json, "
            "saved_at = excluded.saved_at",
            (account_id, draft_id, titre, plan_json, now),
        )
        self.conn.commit()
        return {"id": draft_id, "titre": titre, "saved_at": now}

    def list_drafts(self, account_id: int):
        """Références légères (sans le plan), plus récent en premier."""
        rows = self.conn.execute(
            "SELECT draft_id, titre, saved_at FROM brouillons "
            "WHERE compte_id = ? ORDER BY saved_at DESC, draft_id",
            (account_id,),
        ).fetchall()
        return [{"id": r[0], "titre": r[1], "saved_at": r[2]} for r in rows]

    def get_draft(self, account_id: int, draft_id: str):
        row = self.conn.execute(
            "SELECT draft_id, titre, plan_json, saved_at FROM brouillons "
            "WHERE compte_id = ? AND draft_id = ?",
            (account_id, draft_id),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "titre": row[1],
            "plan": json.loads(row[2]),
            "saved_at": row[3],
        }

    def delete_draft(self, account_id: int, draft_id: str) -> bool:
        cur = self.conn.execute(
            "DELETE FROM brouillons WHERE compte_id = ? AND draft_id = ?",
            (account_id, draft_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------- propositions
    def save_proposal(self, account_id: int, titre: str, plan, check: dict) -> dict:
        """Enregistre le snapshot immuable de la séance (décision D1) avec
        le résultat de validation au moment de l'enregistrement."""
        now = _utcnow_iso()
        cur = self.conn.execute(
            "INSERT INTO propositions (compte_id, titre, plan_json, valide, "
            "erreurs_json, avertissements_json, minutage_json, saved_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                account_id,
                titre,
                json.dumps(plan, ensure_ascii=False),
                1 if check.get("valide") else 0,
                json.dumps(check.get("erreurs", []), ensure_ascii=False),
                json.dumps(check.get("avertissements", []), ensure_ascii=False),
                json.dumps(check.get("minutage", {}), ensure_ascii=False),
                now,
            ),
        )
        self.conn.commit()
        return {
            "id": cur.lastrowid,
            "titre": titre,
            "valide": bool(check.get("valide")),
            "saved_at": now,
        }

    def list_proposals(self, account_id: int):
        """Références légères (sans le plan), plus récente en premier."""
        rows = self.conn.execute(
            "SELECT id, titre, valide, saved_at FROM propositions "
            "WHERE compte_id = ? ORDER BY id DESC",
            (account_id,),
        ).fetchall()
        return [
            {"id": r[0], "titre": r[1], "valide": bool(r[2]), "saved_at": r[3]}
            for r in rows
        ]

    def get_proposal(self, account_id: int, proposal_id: int):
        row = self.conn.execute(
            "SELECT id, titre, plan_json, valide, erreurs_json, "
            "avertissements_json, minutage_json, saved_at FROM propositions "
            "WHERE compte_id = ? AND id = ?",
            (account_id, proposal_id),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "titre": row[1],
            "plan": json.loads(row[2]),
            "valide": bool(row[3]),
            "erreurs": json.loads(row[4]),
            "avertissements": json.loads(row[5]),
            "minutage": json.loads(row[6]),
            "saved_at": row[7],
        }

    # ------------------------------------------------------------- équipes
    def upsert_equipe(
        self,
        account_id: int,
        team_id: str,
        nom,
        club: str | None = None,
        categorie: str | None = None,
        effectif: int | None = None,
        coachs: list | None = None,
        joueurs: list | None = None,
        groupes: list | None = None,
    ) -> dict:
        """Crée ou met à jour une équipe d'effectif du compte (tranché
        2026-11-22). Seul `nom` est obligatoire (1 à 80 caractères) ;
        club, catégorie, effectif, coachs, joueurs et groupes sont
        facultatifs (tailles flexibles selon le club). PUT = mise à jour
        complète : un champ absent est remis à absent. Lève ValueError si
        un champ est invalide.

        `joueurs` (lot L3, v1.1) : liste de joueurs de l'équipe — prénom +
        nom chacun (RGPD v1.1 : prénom + nom, rien d'autre ; le formulaire
        n'a pas d'autre champ joueur). Chaque élément est normalisé
        (normalize_player_name) et dédoublonné insensiblement à la casse
        (la casse préservée du premier écrit est conservée — c'est le nom
        que le coach aura saisi, affiché tel quel dans les groupes).
        La séance n'est PAS une référence vivante : l'attachement d'une
        équipe copie ce snapshot dans les groupes (front, lot L3).

        `groupes` (lot peaufinage C, 2026-11-25) : liste de groupes nommés
        librement de l'équipe — chaque élément est un objet
        {nom, joueurs}. Le nom est un texte libre de 2 à 80 caractères
        (normalize_coach_name) ; les joueurs du groupe doivent appartenir à
        l'effectif de l'équipe (`joueurs`) et un joueur ne peut appartenir
        qu'à un seul groupe (doublons intra-groupe et inter-groupes
        rejetés) — la page « club » sépare effetifs et groupes, les
        joueurs d'un groupe sont les joueurs de l'effectif, rien d'autre.
        """
        if not draft_id_ok(team_id):
            raise ValueError(
                "Identifiant d'équipe invalide (1 à 128 caractères : "
                "lettres, chiffres, « . _ - »)."
            )
        if not isinstance(nom, str):
            raise ValueError("Nom d'équipe requis (texte de 1 à 80 caractères).")
        nom = nom.strip()
        if not (1 <= len(nom) <= MAX_CLUB):
            raise ValueError("Nom d'équipe requis (texte de 1 à 80 caractères).")
        if club is not None:
            if not isinstance(club, str):
                raise ValueError("Le club doit être un texte (80 caractères maximum).")
            club = club.strip() or None
            if club is not None and len(club) > MAX_CLUB:
                raise ValueError("Le nom du club est trop long (80 caractères maximum).")
        if not categorie_ok(categorie):
            raise ValueError(
                "Catégorie invalide (attendue : " + ", ".join(CATEGORIES) + " ou absente)."
            )
        if effectif is not None:
            if isinstance(effectif, bool) or not isinstance(effectif, int) or effectif < 0:
                raise ValueError("Effectif invalide (entier positif, ou champ absent).")
        if coachs is None:
            coachs = []
        if not isinstance(coachs, list):
            raise ValueError(
                "Les coachs rattachés doivent être une liste de logins ou de noms."
            )
        norm_coachs = []
        for c in coachs:
            try:
                c2 = normalize_login(c)
            except ValueError:
                # v1.1 (2026-11-24) : un coach sans compte est désigné par
                # son nom libre (« Marie Dupont ») — repli après le login.
                try:
                    c2 = normalize_coach_name(c)
                except ValueError:
                    raise ValueError(
                        "Identifiant de coach invalide dans la liste des coachs "
                        "rattachés (login, ou nom libre de 2 à 80 caractères)."
                    )
            if c2 not in norm_coachs:
                norm_coachs.append(c2)
        if joueurs is None:
            joueurs = []
        if not isinstance(joueurs, list):
            raise ValueError(
                "Les joueurs doivent être une liste de « prénom + nom » "
                "(ou champ absent)."
            )
        norm_joueurs = []
        _joueurs_vus = set()
        for j in joueurs:
            try:
                j2 = normalize_player_name(j)
            except ValueError:
                raise ValueError(
                    "Nom de joueur invalide dans la liste des joueurs "
                    "(prénom + nom, 2 à 80 caractères)."
                )
            cle = j2.casefold()
            if cle in _joueurs_vus:
                continue
            _joueurs_vus.add(cle)
            norm_joueurs.append(j2)
        if groupes is None:
            groupes = []
        if not isinstance(groupes, list):
            raise ValueError(
                "Les groupes doivent être une liste d’objets {nom, joueurs} "
                "(ou champ absent)."
            )
        effectif_cles = {j.casefold() for j in norm_joueurs}
        groupes_cles: set = set()
        norm_groupes = []
        for g in groupes:
            if not isinstance(g, dict):
                raise ValueError(
                    "Chaque groupe doit être un objet {nom, joueurs} dans la "
                    "liste des groupes."
                )
            try:
                gnom = normalize_coach_name(g.get("nom"))
            except ValueError:
                raise ValueError(
                    "Nom de groupe invalide (texte libre de 2 à 80 caractères)."
                )
            gmembres = g.get("joueurs")
            if gmembres is None:
                gmembres = []
            if not isinstance(gmembres, list):
                raise ValueError(
                    "Les joueurs d’un groupe doivent être une liste de "
                    "« prénom + nom »."
                )
            membres_norm = []
            for j in gmembres:
                try:
                    j2 = normalize_player_name(j)
                except ValueError:
                    raise ValueError(
                        "Nom de joueur invalide dans un groupe (prénom + nom, "
                        "2 à 80 caractères)."
                    )
                cle = j2.casefold()
                if cle not in effectif_cles:
                    raise ValueError(
                        f"Le joueur « {j2} » du groupe « {gnom} » ne fait pas "
                        "partie de l’effectif de l’équipe."
                    )
                if cle in groupes_cles:
                    raise ValueError(
                        f"Le joueur « {j2} » est présent dans plusieurs "
                        "groupes (un joueur au plus dans un groupe)."
                    )
                groupes_cles.add(cle)
                membres_norm.append(j2)
            norm_groupes.append({"nom": gnom, "joueurs": membres_norm})
        now = _utcnow_iso()
        self.conn.execute(
            "INSERT INTO equipes (id, compte_id, nom, club, categorie, effectif, "
            "coachs_json, joueurs_json, groupes_json, saved_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (compte_id, id) DO UPDATE SET nom = excluded.nom, "
            "club = excluded.club, categorie = excluded.categorie, "
            "effectif = excluded.effectif, coachs_json = excluded.coachs_json, "
            "joueurs_json = excluded.joueurs_json, "
            "groupes_json = excluded.groupes_json, "
            "saved_at = excluded.saved_at",
            (
                team_id,
                account_id,
                nom,
                club,
                categorie,
                effectif,
                json.dumps(norm_coachs, ensure_ascii=False),
                json.dumps(norm_joueurs, ensure_ascii=False),
                json.dumps(norm_groupes, ensure_ascii=False),
                now,
            ),
        )
        self.conn.commit()
        return {
            "id": team_id,
            "nom": nom,
            "club": club,
            "categorie": categorie,
            "effectif": effectif,
            "coachs": norm_coachs,
            "joueurs": norm_joueurs,
            "groupes": norm_groupes,
            "saved_at": now,
        }

    def list_equipes(self, account_id: int):
        """Équipes du compte, plus récente en premier."""
        rows = self.conn.execute(
            "SELECT id, nom, club, categorie, effectif, coachs_json, "
            "joueurs_json, groupes_json, saved_at "
            "FROM equipes WHERE compte_id = ? ORDER BY saved_at DESC, id",
            (account_id,),
        ).fetchall()
        return [_equipe_dict(r) for r in rows]

    def get_equipe(self, account_id: int, team_id: str):
        row = self.conn.execute(
            "SELECT id, nom, club, categorie, effectif, coachs_json, "
            "joueurs_json, groupes_json, saved_at "
            "FROM equipes WHERE compte_id = ? AND id = ?",
            (account_id, team_id),
        ).fetchone()
        return _equipe_dict(row) if row is not None else None

    def delete_equipe(self, account_id: int, team_id: str) -> bool:
        cur = self.conn.execute(
            "DELETE FROM equipes WHERE compte_id = ? AND id = ?",
            (account_id, team_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    # ---------------------------------- identité du club (lot peaufinage B)
    def get_club_theme(self, club):
        """Identité du club (couleurs + logo en data URI) ou None si le club
        n'en a pas. La clé est le nom du club normalisé (strip) — même règle
        que l'enregistrement. Le logo est renvoyé prêt à afficher (data URI)."""
        if not isinstance(club, str):
            return None
        row = self.conn.execute(
            "SELECT couleur_primary, couleur_secondaire, couleur_accent, "
            "logo_mime, logo FROM clubs WHERE club = ?",
            (club.strip(),),
        ).fetchone()
        if row is None:
            return None
        logo = None
        if row[4] is not None:
            b64 = base64.b64encode(row[4]).decode("ascii")
            logo = "data:%s;base64,%s" % (row[3], b64)
        return {
            "couleurs": {
                "primary": row[0],
                "secondary": row[1],
                "accent": row[2],
            },
            "logo": logo,
        }

    def set_club_theme(self, club, couleurs, logo, logo_mime):
        """Crée ou remplace l'identité du club (upsert). `logo` : octets
        (PNG/SVG validés) ou None pour retirer le logo. Renvoie l'identité
        enregistrée, telle qu'elle sera servie par get_club_theme."""
        now = _utcnow_iso()
        self.conn.execute(
            "INSERT INTO clubs (club, couleur_primary, couleur_secondaire, "
            "couleur_accent, logo_mime, logo, saved_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (club) DO UPDATE SET "
            "couleur_primary = excluded.couleur_primary, "
            "couleur_secondaire = excluded.couleur_secondaire, "
            "couleur_accent = excluded.couleur_accent, "
            "logo_mime = excluded.logo_mime, "
            "logo = excluded.logo, "
            "saved_at = excluded.saved_at",
            (
                club.strip(),
                couleurs["primary"],
                couleurs["secondary"],
                couleurs["accent"],
                logo_mime,
                logo,
                now,
            ),
        )
        self.conn.commit()
        return self.get_club_theme(club)

    def list_clubs(self):
        """Noms de club distincts (table comptes) pour les suggestions du
        formulaire d'inscription (lot L1, cadrage 06, 2026-11-27) : non
        vides, strip, dé-doublonnés casefold (accents comptent — même règle
        d'orthographe que partout dans l'app), ordre alphabétique. Les noms
        seuls : l'endpoint est public (le formulaire s'utilise sans
        session), aucune donnée personnelle n'est livrée."""
        rows = self.conn.execute(
            "SELECT club FROM comptes "
            "WHERE club IS NOT NULL AND TRIM(club) != '' ORDER BY id"
        ).fetchall()
        par_canon = {}
        for (raw,) in rows:
            if not isinstance(raw, str):
                continue
            club = raw.strip()
            if not club:
                continue
            par_canon.setdefault(club.casefold(), club)
        return [par_canon[cle] for cle in sorted(par_canon)]

    # ---------------------------------------------------- magasin joueurs par club
    def ajouter_joueur_club(self, club, joueur) -> dict:
        """Ajoute un joueur au magasin du club (lot P3, cadrage 05,
        2026-11-26, D4). Clé = nom du club (strip, même règle que `clubs`) :
        le magasin est commun à tous les comptes du club — le gestionnaire
        saisit, les coachs lisent. Joueur = prénom + nom uniquement (RGPD
        v1.1) : aucun autre champ n'est accepté ni stocké. Lève ValueError
        si le club ou le nom est invalide, JoueurExists si un joueur de ce
        nom existe déjà pour le club (comparaison insensible à la casse :
        le doublon est une faute de frappe, elle se corrige par une
        suppression)."""
        if not isinstance(club, str) or not club.strip():
            raise ValueError("Nom de club requis (texte de 80 caractères au plus).")
        club = club.strip()
        if len(club) > MAX_CLUB:
            raise ValueError("Nom de club trop long (80 caractères au plus).")
        joueur = normalize_player_name(joueur)
        if self.conn.execute(
            "SELECT 1 FROM joueurs_club WHERE club = ? "
            "AND joueur = ? COLLATE NOCASE",
            (club, joueur),
        ).fetchone() is not None:
            raise JoueurExists(joueur)
        now = _utcnow_iso()
        self.conn.execute(
            "INSERT INTO joueurs_club (club, joueur, saved_at) VALUES (?, ?, ?)",
            (club, joueur, now),
        )
        self.conn.commit()
        return {"club": club, "joueur": joueur, "saved_at": now}

    def supprimer_joueur_club(self, club, joueur) -> None:
        """Retire un joueur du magasin du club (lot P3). Lève ValueError si
        le club est absent/vide, si le nom est invalide ou si le joueur est
        inconnu pour ce club (comparaison insensible à la casse)."""
        if not isinstance(club, str) or not club.strip():
            raise ValueError("Nom de club requis (texte de 80 caractères au plus).")
        joueur = normalize_player_name(joueur)
        cur = self.conn.execute(
            "DELETE FROM joueurs_club WHERE club = ? "
            "AND joueur = ? COLLATE NOCASE",
            (club.strip(), joueur),
        )
        if cur.rowcount != 1:
            raise ValueError("Joueur introuvable.")
        self.conn.commit()

    def list_joueurs_club(self, club):
        """Magasin joueurs du club (lot P3, clé = nom du club) : liste de
        chaînes prénom + nom, ordre alphabétique insensible à la casse. Un
        club sans joueur — ou un nom de club absent/vide — renvoie la liste
        vide. Le magasin n'est rattaché à aucun compte : tout compte qui
        connaît le club lit la même liste."""
        if not isinstance(club, str) or not club.strip():
            return []
        rows = self.conn.execute(
            "SELECT joueur FROM joueurs_club WHERE club = ? "
            "ORDER BY joueur COLLATE NOCASE",
            (club.strip(),),
        ).fetchall()
        return [r[0] for r in rows]


def _equipe_dict(row) -> dict:
    """Ligne (id, nom, club, categorie, effectif, coachs_json, joueurs_json,
    groupes_json, saved_at)."""
    return {
        "id": row[0],
        "nom": row[1],
        "club": row[2],
        "categorie": row[3],
        "effectif": row[4],
        "coachs": json.loads(row[5]),
        "joueurs": json.loads(row[6]),
        "groupes": json.loads(row[7]),
        "saved_at": row[8],
    }
