import requests
from src.config import HF_API_KEY

API_URL = "https://api-inference.huggingface.co/models/mixedbread-ai/mxbai-embed-large-v1"
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