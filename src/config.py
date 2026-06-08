import os
from dotenv import load_dotenv

load_dotenv()

QDRANT_HOST     = os.getenv("QDRANT_HOST")
QDRANT_API_KEY  = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "default")  # fallback only

GROQ_API_KEY    = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
HF_API_KEY      = os.getenv("HF_API_KEY")

MASTER_API_KEY  = os.getenv("MASTER_API_KEY")  # your secret admin key

EMBEDDING_MODEL = "BAAI/bge-m3"
LLM_MODEL       = "llama-3.3-70b-versatile"
FALLBACK_MODEL  = "gemini-2.0-flash"

FASTAPI_URL     = os.getenv("FASTAPI_URL", "http://localhost:8000")