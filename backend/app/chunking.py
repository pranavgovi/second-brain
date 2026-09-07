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
