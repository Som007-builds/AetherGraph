import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# ─── LLM ─────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.1-8b-instant"

# Primary provider: "groq", "gemini", or "claude"
LLM_PROVIDER = "groq"

# Provider fallback chain — tried in order when the primary is rate-limited.
# Set to a single-element list to disable fallback.
LLM_PROVIDER_CHAIN = ["groq", "gemini"]

# LLM cache: set to True to enable in-process response caching (saves API calls
# for repeated identical prompts, e.g. during dev / repeated contradiction checks)
LLM_CACHE_ENABLED = os.getenv("LLM_CACHE_ENABLED", "false").lower() == "true"

# ─── Paths ───────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "db" / "scimesh.db"
PAPERS_DIR = DATA_DIR / "papers"
CHROMA_DIR = DATA_DIR / "db" / "chroma"

# ─── Embeddings ──────────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# ─── Agent settings ──────────────────────────────────────────
MAX_CLAIMS_PER_PAPER = 8
CONTRADICTION_THRESHOLD = 0.95

# ─── Neo4j ───────────────────────────────────────────────────
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j"))
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "scimesh123")
NEO4J_CONTAINER_NAME = os.getenv("NEO4J_CONTAINER_NAME", "scimesh-neo4j")

# ─── API / CORS ──────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

# ─── Scheduler ───────────────────────────────────────────────
SCHEDULER_INTERVAL_HOURS = int(os.getenv("SCHEDULER_INTERVAL_HOURS", "6"))
SCHEDULER_PAPERS_PER_RUN = int(os.getenv("SCHEDULER_PAPERS_PER_RUN", "5"))
SCHEDULER_TOPICS = [
    "chain of thought prompting LLM",
    "in-context learning large language models",
    "LLM reasoning benchmark evaluation",
    "instruction tuning language models",
    "RLHF reinforcement learning human feedback"
]
# Narrow topics surface better papers. Add or change as the graph grows.

# ─── Security ────────────────────────────────────────────────
TRIGGER_SECRET = os.getenv("TRIGGER_SECRET", "super_secret_trigger_key_default_123")