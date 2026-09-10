import sqlite3
from typing import Any

from werkzeug.security import check_password_hash, generate_password_hash

from config import Config


def get_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    );
    """)

    # Offerings
    cur.execute("""
    CREATE TABLE IF NOT EXISTS offerings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        industry TEXT,
        owner TEXT,
        tags TEXT,
        description TEXT,
        artifact_links TEXT
    );
    """)

    # Case studies
    cur.execute("""
    CREATE TABLE IF NOT EXISTS case_studies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        industry TEXT,
        key_benefit TEXT,
        link TEXT
    )
    """)


    # Opportunities
    cur.execute("""
    CREATE TABLE IF NOT EXISTS opportunities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        client TEXT,
        industry TEXT,
        value TEXT,
        stage TEXT,
        description TEXT,
        requirements TEXT
    );
    """)

    # Recommendations history
    cur.execute("""
    CREATE TABLE IF NOT EXISTS recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        opportunity_id INTEGER,
        offering_id INTEGER,
        fit_score REAL,
        explanation TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # AI logs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ai_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        query TEXT,
        response TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()

    # Upgrade legacy plaintext passwords when an older database is opened.
    cur.execute("SELECT id, password FROM users")
    for user_id, password in cur.fetchall():
        if password and not password.startswith(("scrypt:", "pbkdf2:", "argon2:")):
            cur.execute(
                "UPDATE users SET password=? WHERE id=?",
                (generate_password_hash(password), user_id)
            )

    # Seed a default user and some dummy data if empty
    cur.execute("SELECT COUNT(*) FROM users;")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", generate_password_hash("admin123"), "admin")
        )

    conn.commit()
    conn.close()

def query_all(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def query_one(sql: str, params: tuple = ()) -> dict[str, Any] | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def execute(sql: str, params: tuple = ()) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    """Return a user only when the supplied password matches its hash."""
    user = query_one("SELECT * FROM users WHERE username = ?", (username,))
    if user and check_password_hash(user["password"], password):
        return user
    return None
