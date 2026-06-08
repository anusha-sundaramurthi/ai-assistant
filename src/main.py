from fastapi import FastAPI, UploadFile, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.websockets import WebSocket
from contextlib import asynccontextmanager
from pydantic import BaseModel
from src.ingest import ingest_pdf
from src.vectorstores import init_qdrant, clear_qdrant
from src.generator import generate_answer, clear_memory
import httpx
import websockets
import asyncio

STREAMLIT_URL = "http://127.0.0.1:8501"
STREAMLIT_WS  = "ws://127.0.0.1:8501"

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing Qdrant database...")
    init_qdrant()
    print("Database initialization complete.")
    yield

app = FastAPI(lifespan=lifespan)

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

# ── WebSocket proxy ───────────────────────────────────────
@app.websocket("/{path:path}")
async def websocket_proxy(websocket: WebSocket, path: str):
    await websocket.accept()
    target = f"{STREAMLIT_WS}/{path}"
    try:
        async with websockets.connect(
            target,
            additional_headers={"Host": "127.0.0.1:8501"}
        ) as ws_target:
            async def forward_to_target():
                try:
                    async for message in websocket.iter_bytes():
                        await ws_target.send(message)
                except Exception:
                    pass

            async def forward_to_client():
                try:
                    async for message in ws_target:
                        if isinstance(message, bytes):
                            await websocket.send_bytes(message)
                        else:
                            await websocket.send_text(message)
                except Exception:
                    pass

            await asyncio.gather(forward_to_target(), forward_to_client())
    except Exception as e:
        print(f"[WebSocket proxy error] {e}")
        await websocket.close()

# ── HTTP proxy ────────────────────────────────────────────
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def proxy_streamlit(request: Request, path: str):
    url = f"{STREAMLIT_URL}/{path}"
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            proxied = await client.request(
                method=request.method,
                url=url,
                headers={
                    k: v for k, v in request.headers.items()
                    if k.lower() not in ("host", "connection")
                },
                content=await request.body(),
                params=request.query_params,
                follow_redirects=True
            )
            return StreamingResponse(
                content=proxied.aiter_bytes(),
                status_code=proxied.status_code,
                headers={
                    k: v for k, v in proxied.headers.items()
                    if k.lower() not in ("content-encoding", "transfer-encoding")
                }
            )
        except httpx.ConnectError:
            return HTMLResponse(
                "<h3>App is starting up... please refresh in 10 seconds.</h3>",
                status_code=503
            )