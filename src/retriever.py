import re
from src.embeddings import get_embeddings
from src.vectorstores import get_qdrant_client

TOP_SCORE_THRESHOLD = 0.70
MIN_CHUNK_SCORE     = 0.70

def normalize_query(query: str) -> str:
    replacements = {
        r'\bsrilanka\b':    'sri lanka',
        r'\bnewzealand\b':  'new zealand',
        r'\bsouthkorea\b':  'south korea',
        r'\bnorthkorea\b':  'north korea',
        r'\bsouthafrica\b': 'south africa',
        r'\bcostarica\b':   'costa rica',
        r'\bpuertorico\b':  'puerto rico',
        r'\buae\b':         'united arab emirates',
        r'\busa\b':         'united states',
        r'\buk\b':          'united kingdom',
    }
    normalized = query.lower().strip()
    for pattern, replacement in replacements.items():
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    return normalized

def retrieve_docs(query: str, collection_name: str, top_k: int = 10) -> list[str]:
    client           = get_qdrant_client()
    normalized_query = normalize_query(query)
    query_vector     = get_embeddings([normalized_query])[0]

    search_result = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=top_k,
        with_payload=True
    )

    hits = search_result.points
    if not hits:
        return []

    best_score = hits[0].score
    if best_score < TOP_SCORE_THRESHOLD:
        return []

    keep_threshold = max(best_score * 0.85, MIN_CHUNK_SCORE)
    relevant = []
    for hit in hits:
        if hit.score >= keep_threshold:
            relevant.append(hit.payload.get("text", ""))

    return relevant