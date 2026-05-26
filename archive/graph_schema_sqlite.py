import sqlite3
from pathlib import Path
from config import DB_PATH


def init_db():
    """Create all tables if they don't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    c.executescript("""
        CREATE TABLE IF NOT EXISTS papers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            arxiv_id    TEXT UNIQUE NOT NULL,
            title       TEXT,
            authors     TEXT,
            abstract    TEXT,
            published   TEXT,
            ingested_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS claims (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id    INTEGER REFERENCES papers(id),
            claim_text  TEXT NOT NULL,
            section     TEXT,
            confidence  REAL DEFAULT 1.0,
            embedding_id TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS relationships (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_a_id   INTEGER REFERENCES claims(id),
            claim_b_id   INTEGER REFERENCES claims(id),
            rel_type     TEXT NOT NULL,
            explanation  TEXT,
            confidence   REAL DEFAULT 0.0,
            created_at   TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS gaps (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            gap_text        TEXT NOT NULL,
            related_claim_ids TEXT,
            embedding_id    TEXT,
            created_at      TEXT DEFAULT (datetime('now'))
        );
    """)
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


if __name__ == "__main__":
    init_db()