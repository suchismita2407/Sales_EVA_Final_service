import sqlite3

from werkzeug.security import check_password_hash

import db


def test_database_helpers_and_hashed_seed_user(tmp_path, monkeypatch):
    database_path = tmp_path / "test.db"
    monkeypatch.setattr(db.Config, "DATABASE_PATH", str(database_path))

    db.init_db()
    inserted_id = db.execute(
        "INSERT INTO offerings (name, industry) VALUES (?, ?)",
        ("Analytics", "Retail"),
    )

    offering = db.query_one("SELECT * FROM offerings WHERE id=?", (inserted_id,))
    users = db.query_all("SELECT * FROM users")

    assert offering["name"] == "Analytics"
    assert len(users) == 1
    assert check_password_hash(users[0]["password"], "admin123")
    assert db.authenticate_user("admin", "admin123")["username"] == "admin"
    assert db.authenticate_user("admin", "wrong") is None


def test_legacy_password_is_upgraded(tmp_path, monkeypatch):
    database_path = tmp_path / "legacy.db"
    monkeypatch.setattr(db.Config, "DATABASE_PATH", str(database_path))

    connection = sqlite3.connect(database_path)
    connection.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)"
    )
    connection.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        ("legacy", "old-password", "user"),
    )
    connection.commit()
    connection.close()

    db.init_db()
    user = db.query_one("SELECT * FROM users WHERE username=?", ("legacy",))

    assert user["password"] != "old-password"
    assert db.authenticate_user("legacy", "old-password") is not None