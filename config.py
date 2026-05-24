import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# API - switch USE_GEMINI to False when you have Claude key
USE_GEMINI = True

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
 
GEMINI_MODEL = "gemini-2.0-flash"
# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "db" / "scimesh.db"
PAPERS_DIR = DATA_DIR / "papers"
CHROMA_DIR = DATA_DIR / "db" / "chroma"

# Embedding settings
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# Agent settings
MAX_CLAIMS_PER_PAPER = 8
CONTRADICTION_THRESHOLD = 0.95

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
 
GROQ_MODEL = "llama-3.1-8b-instant"
# Switch: "groq", "gemini", or "claude"
LLM_PROVIDER = "groq"