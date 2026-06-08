import requests
from src.config import HF_API_KEY, EMBEDDING_MODEL

API_URL = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{EMBEDDING_MODEL}"
HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}


def get_embeddings(texts: list[str]) -> list[list[float]]:
    response = requests.post(
        API_URL,
        headers=HEADERS,
        json={"inputs": texts, "options": {"wait_for_model": True}}
    )
    response.raise_for_status()
    embeddings = response.json()
    # HF returns shape: [n_texts, n_tokens, dim] for bge-m3 (sentence embeddings = first token / pooled)
    # The feature-extraction pipeline returns [n_texts, dim] when sentences are passed
    return embeddings