import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.models import Chunk

# Loaded once at import time — loading the model is slow (seconds), so this
# must not happen per-request. all-MiniLM-L6-v2: 384-dim output, fast on
# CPU, the standard default for semantic search at this scale.
_model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str) -> list[float]:
    """Embed a single string (e.g. a query at ask-time)."""
    return _model.encode(text, convert_to_numpy=True).tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of strings in one call (e.g. a document's chunks at
    ingest-time) — meaningfully faster than calling embed_text in a loop."""
    if not texts:
        return []
    return _model.encode(texts, convert_to_numpy=True).tolist()


#(a.b)/ |a|*|b|
def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr = np.asarray(a)
    b_arr = np.asarray(b)
    denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if denom == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / denom)


def find_similar_chunks(query: str, db: Session, top_k: int = 5) -> list[Chunk]:
    """Brute-force cosine similarity search over every stored chunk. Fine at
    personal scale (hundreds/low-thousands of chunks) — no vector DB/ANN
    index needed."""
    chunks = db.query(Chunk).all()
    if not chunks:
        return []

    query_vector = np.asarray(embed_text(query))#question gets embedded as well and compared
    query_norm = np.linalg.norm(query_vector)

    scored = []
    for chunk in chunks:
        chunk_vector = np.frombuffer(chunk.embedding, dtype=np.float32)
        denom = query_norm * np.linalg.norm(chunk_vector)
        similarity = float(np.dot(query_vector, chunk_vector) / denom) if denom else 0.0
        scored.append((similarity, chunk))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]
