import numpy as np
from sqlalchemy.orm import Session

from app.embeddings import embed_texts
from app.models import Chunk


def chunk_text(text: str, chunk_size: int = 250, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks of ~chunk_size words. Splits only
    on whitespace (word boundaries), never mid-word. Consecutive chunks
    share `overlap` words so a sentence cut at a boundary still appears
    whole in at least one chunk."""
    words = text.split()
    if not words:
        return []
    if len(words) <= chunk_size:
        return [" ".join(words)]

    step = chunk_size - overlap
    chunks = []
    start = 0
    while start < len(words):
        chunk_words = words[start : start + chunk_size]
        chunks.append(" ".join(chunk_words))
        if start + chunk_size >= len(words):
            break
        start += step

    return chunks


def store_chunks(item_id: int, text: str | None, db: Session) -> None:
    """Chunk `text`, embed each chunk (batched), and persist them as Chunk
    rows linked to the given ingested item. No-op if there's no text."""
    if not text:
        return

    chunks = chunk_text(text)
    if not chunks:
        return

    vectors = embed_texts(chunks)

    for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
        db.add(
            Chunk(
                ingested_item_id=item_id,
                chunk_index=index,
                text=chunk,
                embedding=np.array(vector, dtype=np.float32).tobytes(),
            )
        )
