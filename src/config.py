import os
from dotenv import load_dotenv

load_dotenv()

QDRANT_HOST     = os.getenv("QDRANT_HOST")
QDRANT_API_KEY  = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")

GROQ_API_KEY    = os.getenv("GROQ_API_KEY")
HF_API_KEY      = os.getenv("HF_API_KEY")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")      # ← NEW

EMBEDDING_MODEL = "BAAI/bge-m3"
LLM_MODEL       = "llama-3.3-70b-versatile"        # Groq model
FALLBACK_MODEL  = "gemini-2.0-flash"               # Gemini fallback

FASTAPI_URL     = "http://localhost:8000"