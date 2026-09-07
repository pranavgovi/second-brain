from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.embeddings import find_similar_chunks
from app.llm import generate_answer
from app.models import IngestedItem
from app.schemas import AskRequest, AskResponse, AskSource

router = APIRouter(tags=["qa"])

NO_CONTENT_ANSWER = "I don't have any relevant information in the ingested notes to answer that."


@router.post("/ask", response_model=AskResponse)
async def ask(payload: AskRequest, db: Session = Depends(get_db)):
    chunks = find_similar_chunks(payload.question, db, top_k=5)

    if not chunks:
        return AskResponse(answer=NO_CONTENT_ANSWER, sources=[])

    item_ids = {chunk.ingested_item_id for chunk in chunks}
    items = db.query(IngestedItem).filter(IngestedItem.id.in_(item_ids)).all()
    titles_by_id = {item.id: item.title for item in items}

    answer = await generate_answer(payload.question, [chunk.text for chunk in chunks])

    sources = [
        AskSource(
            ingested_item_id=chunk.ingested_item_id,
            title=titles_by_id.get(chunk.ingested_item_id, "Untitled"),
            chunk_text=chunk.text,
        )
        for chunk in chunks
    ]

    return AskResponse(answer=answer, sources=sources)
