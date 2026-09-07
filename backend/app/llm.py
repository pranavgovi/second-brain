import httpx

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "llama3.2"

PROMPT_TEMPLATE = """Answer the question using only the context below. If the context doesn't contain enough information to answer, say you don't have relevant information in the ingested notes rather than guessing.

Context:
{context}

Question: {question}

Answer:"""


async def generate_answer(question: str, context_chunks: list[str]) -> str:
    context = "\n\n---\n\n".join(context_chunks)
    prompt = PROMPT_TEMPLATE.format(context=context, question=question)

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            OLLAMA_URL,
            json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
        )
        resp.raise_for_status()

    return resp.json()["response"].strip()
