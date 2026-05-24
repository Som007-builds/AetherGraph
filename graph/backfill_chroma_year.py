# graph/backfill_chroma_year.py
"""
One-time script: adds paper_year to existing ChromaDB claim metadata.
Safe to run multiple times.
"""
import chromadb
from chromadb.utils import embedding_functions
from config import CHROMA_DIR, EMBEDDING_MODEL
from graph.queries import get_all_claims

client = chromadb.PersistentClient(path=str(CHROMA_DIR))
ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
claims_col = client.get_or_create_collection("claims", embedding_function=ef)


def run():
    all_claims = get_all_claims()
    year_by_claim_id = {c["id"]: c["paper_year"] for c in all_claims if c["paper_year"]}

    print(f"Backfilling {len(year_by_claim_id)} claims in ChromaDB...")

    updated = 0
    for claim in all_claims:
        doc_id = f"claim_{claim['id']}"
        year = year_by_claim_id.get(claim["id"])
        if not year:
            continue

        try:
            result = claims_col.get(ids=[doc_id], include=["metadatas"])
            if not result["ids"]:
                continue
            existing_meta = result["metadatas"][0]

            if existing_meta.get("paper_year"):
                continue

            existing_meta["paper_year"] = str(year)
            claims_col.update(ids=[doc_id], metadatas=[existing_meta])
            updated += 1
        except Exception as e:
            print(f"  Warning: could not update {doc_id}: {e}")

    print(f"Done. Updated {updated} records.")


if __name__ == "__main__":
    run()