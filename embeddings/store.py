import chromadb
from chromadb.utils import embedding_functions
from config import CHROMA_DIR, EMBEDDING_MODEL

# Initialize ChromaDB client
client = chromadb.PersistentClient(path=str(CHROMA_DIR))

# Use a local sentence-transformer model (no API cost)
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)

# Two collections: one for chunks, one for claims
chunks_col = client.get_or_create_collection("paper_chunks", embedding_function=ef)
claims_col = client.get_or_create_collection("claims", embedding_function=ef)


def add_chunk(doc_id: str, text: str, metadata: dict):
    chunks_col.upsert(documents=[text], ids=[doc_id], metadatas=[metadata])


def add_claim(claim_id: int, claim_text: str, metadata: dict) -> str:
    doc_id = f"claim_{claim_id}"
    claims_col.upsert(documents=[claim_text], ids=[doc_id], metadatas=[metadata])
    return doc_id


def find_similar_claims(claim_text: str, n_results: int = 10) -> list[dict]:
    """Find the most semantically similar claims to a given text."""
    results = claims_col.query(
        query_texts=[claim_text],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )
    
    similar = []
    for i in range(len(results["ids"][0])):
        similar.append({
            "doc_id": results["ids"][0][i],
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return similar


def find_similar_chunks(query: str, n_results: int = 5) -> list[dict]:
    """Find paper chunks relevant to a query."""
    results = chunks_col.query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )
    
    similar = []
    for i in range(len(results["ids"][0])):
        similar.append({
            "doc_id": results["ids"][0][i],
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return similar