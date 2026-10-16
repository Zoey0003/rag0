from uuid import UUID

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """问答请求，指定用户和数据库会话。"""
    session_id: UUID
    question: str = Field(min_length=1, max_length=2000)
class Source(BaseModel):
    title: str
    source: str
    filename: str
    source_type: str

class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[Source]
    generation_count: int
