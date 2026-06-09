from openai import OpenAI
from src.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def get_embeddings(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    return [item.embedding for item in response.data]