# graph/fix_chroma_year_type.py
"""
One-time script: converts paper_year metadata in ChromaDB from string to int.
Safe to run multiple times.

Usage:
    python graph/fix_chroma_year_type.py
"""
import chromadb
from chromadb.utils import embedding_functions
from config import CHROMA_DIR, EMBEDDING_MODEL


def run():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    claims_col = client.get_or_create_collection("claims", embedding_function=ef)

    result = claims_col.get(include=["metadatas"])
    all_ids = result["ids"]
    all_meta = result["metadatas"]

    needs_fix = []
    for doc_id, meta in zip(all_ids, all_meta):
        year_val = meta.get("paper_year")
        if isinstance(year_val, str):
            needs_fix.append((doc_id, meta, year_val))

    print(f"Found {len(needs_fix)} entries with string paper_year.")

    fixed = 0
    for doc_id, meta, year_str in needs_fix:
        try:
            year_int = int(year_str) if year_str else 0
        except ValueError:
            year_int = 0

        meta["paper_year"] = year_int
        claims_col.update(ids=[doc_id], metadatas=[meta])
        fixed += 1

    print(f"Fixed {fixed} entries. All paper_year values now int.")


if __name__ == "__main__":
    run()