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
`categorie` (liste contrôlée U6…U18, Autre). Le club est un simple
libellé : il n'ouvre aucun accès (C1 inchangé).

La connexion est ouverte et fermée par requête (wsgiref est mono-thread).
"""

from __future__ import annotations

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
CATEGORIES = ("U6", "U8", "U10", "U12", "U14", "U16", "U18", "Autre")

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
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class AccountExists(Exception):
    """Login déjà enregistré (→ HTTP 409 côté API)."""


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


def password_ok(password) -> bool:
    return isinstance(password, str) and MIN_PASSWORD <= len(password) <= MAX_PASSWORD


def club_ok(club) -> bool:
    """Nom de club : absent (None) ou texte de ≤ MAX_CLUB caractères."""
    if club is None:
        return True
    return isinstance(club, str) and len(club.strip()) <= MAX_CLUB


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
