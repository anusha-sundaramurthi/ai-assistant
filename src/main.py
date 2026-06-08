from fastapi import FastAPI, UploadFile, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pydantic import BaseModel
from src.ingest import ingest_pdf
from src.vectorstores import init_qdrant, clear_qdrant
from src.generator import generate_answer, clear_memory
from src.tenants import (
    create_tenant, get_tenant, list_tenants,
    update_tenant_config, delete_tenant
)
from src.auth import verify_master_key, verify_widget_key
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    # Serve static files (widget.js + admin panel)
    yield

app = FastAPI(title="AI Widget API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (widget.js, admin panel)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ══════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS — end users (no auth needed)
# ══════════════════════════════════════════════════════════

class QueryRequest(BaseModel):
    query:       str
    session_id:  str  = "default"
    use_general: bool = False
    language:    str  = "English"
    widget_id:   str  = "default"       # ← NEW

@app.post("/ask")
async def ask_question(req: QueryRequest):
    tenant = get_tenant(req.widget_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Widget not found")

    result = generate_answer(
        req.query,
        session_id=f"{req.widget_id}_{req.session_id}",
        use_general=req.use_general,
        language=req.language,
        collection_name=tenant["collection"]
    )
    return {
        "response":        result["answer"],
        "rewritten_query": result["rewritten_query"],
        "has_pdf_context": result["has_pdf_context"]
    }

@app.post("/clear")
async def clear_chat(session_id: str = "default", widget_id: str = "default"):
    clear_memory(f"{widget_id}_{session_id}")
    return {"message": "Memory cleared"}

@app.get("/widget-config/{widget_id}")
async def get_widget_config(widget_id: str):
    """Public endpoint — widget fetches its own config (colors, title etc.)"""
    tenant = get_tenant(widget_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Widget not found")
    return {
        "widget_id": widget_id,
        "config":    tenant["config"]
    }


# ══════════════════════════════════════════════════════════
# WIDGET OWNER ENDPOINTS — protected by widget api_key
# ══════════════════════════════════════════════════════════

@app.post("/upload")
async def upload_file(
    file: UploadFile = None,
    tenant = Depends(verify_widget_key)
):
    if not file:
        return {"message": "No file uploaded"}
    if not file.filename.endswith(".pdf"):
        return {"message": "Please upload a PDF file"}
    try:
        await ingest_pdf(file, tenant["collection"])
        return {"message": f"File processed successfully into widget {tenant['widget_id']}"}
    except Exception as e:
        return {"message": f"Error: {str(e)}"}

@app.post("/clear-db")
async def clear_database(tenant = Depends(verify_widget_key)):
    clear_qdrant(tenant["collection"])
    return {"message": f"Database cleared for widget {tenant['widget_id']}"}

@app.put("/widget-config")
async def update_config(config: dict, tenant = Depends(verify_widget_key)):
    updated = update_tenant_config(tenant["widget_id"], config)
    return {"message": "Config updated", "config": updated["config"]}


# ══════════════════════════════════════════════════════════
# MASTER ADMIN ENDPOINTS — protected by master api_key
# ══════════════════════════════════════════════════════════

class CreateWidgetRequest(BaseModel):
    name:   str
    config: dict = {
        "title":        "AI Assistant",
        "color":        "#4a9eff",
        "welcome":      "Hi! How can I help you?",
        "language":     "English",
        "placeholder":  "Ask me anything..."
    }

@app.post("/admin/widgets", dependencies=[Depends(verify_master_key)])
async def create_widget(req: CreateWidgetRequest):
    tenant = create_tenant(req.name, req.config)
    init_qdrant(tenant["collection"])
    return {
        "widget_id":  tenant["widget_id"],
        "api_key":    tenant["api_key"],
        "collection": tenant["collection"],
        "embed_code": f'<script src="{os.getenv("FASTAPI_URL")}/static/widget.js" data-widget-id="{tenant["widget_id"]}" data-api="{os.getenv("FASTAPI_URL")}"></script>'
    }

@app.get("/admin/widgets", dependencies=[Depends(verify_master_key)])
async def list_all_widgets():
    return list_tenants()

@app.delete("/admin/widgets/{widget_id}", dependencies=[Depends(verify_master_key)])
async def delete_widget(widget_id: str):
    tenant = get_tenant(widget_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Widget not found")
    clear_qdrant(tenant["collection"])
    delete_tenant(widget_id)
    return {"message": f"Widget {widget_id} deleted"}

@app.get("/")
def root():
    return {"message": "AI Widget API is running"}