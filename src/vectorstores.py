from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from src.config import QDRANT_HOST, QDRANT_API_KEY, COLLECTION_NAME

VECTOR_SIZE = 1536

def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_HOST, api_key=QDRANT_API_KEY)

def _ensure_collection(client: QdrantClient, collection_name: str):
    existing = [c.name for c in client.get_collections().collections]
    if collection_name not in existing:
        print(f"[Qdrant] Creating collection '{collection_name}'...")
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )

def init_qdrant(collection_name: str = None):
    client = get_qdrant_client()
    name   = collection_name or COLLECTION_NAME
    _ensure_collection(client, name)
    return client

def clear_qdrant(collection_name: str = None):
    client = get_qdrant_client()
    name   = collection_name or COLLECTION_NAME
    print(f"[Qdrant] Clearing collection '{name}'...")
    client.delete_collection(collection_name=name)
    _ensure_collection(client, name)
    return client