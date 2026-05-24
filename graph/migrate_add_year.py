# graph/migrate_add_year.py
"""
One-time migration: adds paper_year to claims table,
backfills from the papers.published column.
Safe to run multiple times (idempotent).
"""
import sqlite3
from config import DB_PATH


def run():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    c.execute("PRAGMA table_info(claims)")
    columns = [row[1] for row in c.fetchall()]

    if "paper_year" in columns:
        print("Migration already applied — paper_year column exists.")
        conn.close()
        return

    print("Adding paper_year column to claims...")
    c.execute("ALTER TABLE claims ADD COLUMN paper_year INTEGER")

    c.execute("""
        UPDATE claims
        SET paper_year = (
            SELECT CAST(substr(p.published, 1, 4) AS INTEGER)
            FROM papers p
            WHERE p.id = claims.paper_id
        )
        WHERE paper_year IS NULL
    """)

    conn.commit()

    c.execute("SELECT COUNT(*) FROM claims WHERE paper_year IS NOT NULL")
    filled = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM claims")
    total = c.fetchone()[0]

    print(f"Migration complete: {filled}/{total} claims have paper_year set.")
    conn.close()


if __name__ == "__main__":
    run()