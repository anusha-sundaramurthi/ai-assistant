import google.generativeai as genai
from src.config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

def get_embeddings(texts: list[str]) -> list[list[float]]:
    result = []
    for text in texts:
        response = genai.embed_content(
            model="models/text-multilingual-embedding-002",
            content=text
        )
        result.append(response["embedding"])
    return result