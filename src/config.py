import os
from dotenv import load_dotenv

load_dotenv()

QDRANT_HOST     = os.getenv("QDRANT_HOST")
QDRANT_API_KEY  = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "default")

GROQ_API_KEY    = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")        # ← NEW

MASTER_API_KEY  = os.getenv("MASTER_API_KEY")

LLM_MODEL       = "gemini-2.5-flash-preview-05-20"   # primary
FALLBACK_MODEL  = "llama-3.3-70b-versatile"           # fallback on Groq

FASTAPI_URL     = os.getenv("FASTAPI_URL", "http://localhost:8000")