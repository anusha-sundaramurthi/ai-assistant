from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from src.ingest import ingest_pdf
from src.vectorstores import init_qdrant, clear_qdrant
from src.generator import generate_answer, clear_memory


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing Qdrant database...")
    init_qdrant()
    print("Database initialization complete.")
    yield

app = FastAPI(lifespan=lifespan)

# ── CORS — allow Streamlit Cloud to call this API ─────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # or replace * with "https://ai-assistant-a.streamlit.app"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query:       str
    session_id:  str  = "default"
    use_general: bool = False
    language:    str  = "English"


@app.post("/ask")
async def ask_question(req: QueryRequest):
    result = generate_answer(
        req.query,
        session_id=req.session_id,
        use_general=req.use_general,
        language=req.language
    )
    return {
        "response":        result["answer"],
        "rewritten_query": result["rewritten_query"],
        "has_pdf_context": result["has_pdf_context"]
    }


@app.post("/upload")
async def upload_file(file: UploadFile = None):
    if not file:
        return {"message": "No file uploaded"}
    if not file.filename.endswith(".pdf"):
        return {"message": "Please upload a PDF file"}
    try:
        await ingest_pdf(file)
        return {"message": "File processed successfully"}
    except Exception as e:
        return {"message": f"Error processing file: {str(e)}"}


@app.post("/clear")
async def clear_chat(session_id: str = "default"):
    clear_memory(session_id)
    return {"message": f"Memory cleared for session {session_id}"}


@app.post("/clear-db")
async def clear_database():
    clear_qdrant()
    return {"message": "Database cleared. Please re-upload your PDF guides."}


@app.get("/")
def root():
    return {"message": "AI Travel Assistant API is running"}