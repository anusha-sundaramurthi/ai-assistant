from openai import OpenAI
from src.config import NVIDIA_API_KEY

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)

def get_embeddings(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(
        model="baai/bge-m3",
        input=texts,
        encoding_format="float",
        extra_body={"input_type": "query", "truncate": "END"}
    )
    return [item.embedding for item in response.data]