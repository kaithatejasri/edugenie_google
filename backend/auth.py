"""
Simple username/password auth + history storage backed by SQLite
(no extra dependencies -- sqlite3 is part of the Python standard library).
"""

import sqlite3
import hashlib
import secrets
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "edugenie.db")


def init_db():
    with get_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            feature TEXT NOT NULL,
            request_summary TEXT,
            response_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        db.commit()


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def hash_password(password: str, salt: str = None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return digest, salt


def create_user(username: str, password: str) -> int:
    digest, salt = hash_password(password)
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
            (username, digest, salt),
        )
        db.commit()
        return cur.lastrowid


def verify_user(username: str, password: str):
    with get_db() as db:
        row = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not row:
            return None
        digest, _ = hash_password(password, row["salt"])
        if digest != row["password_hash"]:
            return None
        return row["id"]


def create_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    with get_db() as db:
        db.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
        db.commit()
    return token


def get_user_from_token(token: str):
    if not token:
        return None
    with get_db() as db:
        row = db.execute(
            """SELECT users.id, users.username FROM sessions
               JOIN users ON sessions.user_id = users.id
               WHERE sessions.token = ?""",
            (token,),
        ).fetchone()
        return dict(row) if row else None


def delete_session(token: str):
    with get_db() as db:
        db.execute("DELETE FROM sessions WHERE token = ?", (token,))
        db.commit()


def add_history(user_id: int, feature: str, request_summary: str, response_json: str):
    with get_db() as db:
        db.execute(
            "INSERT INTO history (user_id, feature, request_summary, response_json) VALUES (?, ?, ?, ?)",
            (user_id, feature, request_summary, response_json),
        )
        db.commit()


def get_history(user_id: int, limit: int = 50):
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]