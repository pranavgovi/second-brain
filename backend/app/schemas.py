
from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl

from app.models import SourceType

#this is just request response schema
class TextIngestRequest(BaseModel):
    title: str
    content: str
    tags: str | None = None


class UrlIngestRequest(BaseModel):
    url: HttpUrl
    title: str | None = None
    tags: str | None = None


class IngestedItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str | None
    tags: str | None
    source_type: SourceType
    file_path: str | None
    original_filename: str | None
    source_url: str | None
    created_at: datetime


class AskRequest(BaseModel):
    question: str


class AskSource(BaseModel):
    ingested_item_id: int
    title: str
    chunk_text: str


class AskResponse(BaseModel):
    answer: str
    sources: list[AskSource]
