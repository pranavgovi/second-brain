from fastapi import APIRouter

from app.embeddings import find_similar_neighbors
from app.llm import generate_answer
from app.schemas import AskRequest, AskResponse

router = APIRouter(tags=["qa"])

NO_CONTENT_ANSWER = "I don't have any relevant information in the ingested notes to answer that."


@router.post("/ask", response_model=AskResponse)
async def ask(payload: AskRequest):
    chunks = find_similar_neighbors(payload.question)
    print(chunks)
    if not chunks:
        return AskResponse(answer=NO_CONTENT_ANSWER)

    answer = await generate_answer(payload.question, chunks)
    return AskResponse(answer=answer)
