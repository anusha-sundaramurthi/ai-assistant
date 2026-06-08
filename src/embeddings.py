import requests
from src.config import HF_API_KEY, EMBEDDING_MODEL

API_URL = f"https://router.huggingface.co/hf-inference/models/{EMBEDDING_MODEL}/v1/feature-extraction"
HEADERS = {
    "Authorization": f"Bearer {HF_API_KEY}",
    "Content-Type": "application/json"
}

def get_embeddings(texts: list[str]) -> list[list[float]]:
    response = requests.post(
        API_URL,
        headers=HEADERS,
        json={
            "inputs": texts,
            "options": {"wait_for_model": True}
        }
    )
    response.raise_for_status()
    return response.json()