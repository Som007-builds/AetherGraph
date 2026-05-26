import sqlite3
import json
from config import DB_PATH


def get_conn():
    return sqlite3.connect(str(DB_PATH))


def insert_paper(arxiv_id, title, authors, abstract, published) -> int:
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT OR IGNORE INTO papers (arxiv_id, title, authors, abstract, published)
            VALUES (?, ?, ?, ?, ?)
        """, (arxiv_id, title, json.dumps(authors), abstract, published))
        conn.commit()
        c.execute("SELECT id FROM papers WHERE arxiv_id = ?", (arxiv_id,))
        return c.fetchone()[0]
    finally:
        conn.close()


def insert_claim(paper_id, claim_text, section, confidence=1.0,
                 embedding_id=None, paper_year=None) -> int:
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO claims
              (paper_id, claim_text, section, confidence, embedding_id, paper_year)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (paper_id, claim_text, section, confidence, embedding_id, paper_year))
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()

def get_claims_in_year_range(year_start: int, year_end: int) -> list[dict]:
    """Return all claims from papers published within [year_start, year_end]."""
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("""
            SELECT cl.id, cl.claim_text, cl.section, cl.confidence,
                   p.arxiv_id, p.title, cl.paper_year
            FROM claims cl
            JOIN papers p ON cl.paper_id = p.id
            WHERE cl.paper_year >= ? AND cl.paper_year <= ?
            ORDER BY cl.paper_year ASC
        """, (year_start, year_end))
        rows = c.fetchall()
        return [
            {
                "id": r[0], "text": r[1], "section": r[2],
                "confidence": r[3], "arxiv_id": r[4],
                "paper_title": r[5], "paper_year": r[6]
            }
            for r in rows
        ]
    finally:
        conn.close()

def get_all_claims() -> list[dict]:
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("""
            SELECT cl.id, cl.claim_text, cl.section, cl.confidence,
                   p.arxiv_id, p.title, cl.paper_year
            FROM claims cl
            JOIN papers p ON cl.paper_id = p.id
        """)
        rows = c.fetchall()
        return [
            {
                "id": r[0], "text": r[1], "section": r[2],
                "confidence": r[3], "arxiv_id": r[4],
                "paper_title": r[5], "paper_year": r[6]
            }
            for r in rows
        ]
    finally:
        conn.close()


def insert_relationship(claim_a_id, claim_b_id, rel_type, explanation, confidence) -> int:
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO relationships (claim_a_id, claim_b_id, rel_type, explanation, confidence)
            VALUES (?, ?, ?, ?, ?)
        """, (claim_a_id, claim_b_id, rel_type, explanation, confidence))
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()


def insert_gap(gap_text, related_claim_ids, embedding_id=None) -> int:
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO gaps (gap_text, related_claim_ids, embedding_id)
            VALUES (?, ?, ?)
        """, (gap_text, json.dumps(related_claim_ids), embedding_id))
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()
def get_contradictions() -> list[dict]:
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("""
            SELECT r.id, r.explanation, r.confidence,
                   ca.claim_text, pa.title,
                   cb.claim_text, pb.title,
                   r.claim_a_id, r.claim_b_id
            FROM relationships r
            JOIN claims ca ON r.claim_a_id = ca.id
            JOIN claims cb ON r.claim_b_id = cb.id
            JOIN papers pa ON ca.paper_id = pa.id
            JOIN papers pb ON cb.paper_id = pb.id
            WHERE r.rel_type = 'CONTRADICTS'
            ORDER BY r.confidence DESC
        """)
        rows = c.fetchall()
        return [
            {
                "id": r[0], "explanation": r[1], "confidence": r[2],
                "claim_a": r[3], "paper_a": r[4],
                "claim_b": r[5], "paper_b": r[6],
                "claim_a_id": r[7], "claim_b_id": r[8]
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_gaps() -> list[dict]:
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("SELECT id, gap_text, related_claim_ids, created_at FROM gaps")
        rows = c.fetchall()
        return [
            {"id": r[0], "text": r[1],
             "related_claims": json.loads(r[2]), "created_at": r[3]}
            for r in rows
        ]
    finally:
        conn.close()