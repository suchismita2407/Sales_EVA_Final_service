"""One-time utility for adding the feedback table to an existing database."""

import sqlite3

from config import Config


def create_feedback_table():
    with sqlite3.connect(Config.DATABASE_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opportunity_id INTEGER,
                offering_id INTEGER,
                rating INTEGER,
                comments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


if __name__ == "__main__":
    create_feedback_table()