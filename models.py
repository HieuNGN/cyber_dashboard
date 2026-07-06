from pydantic import BaseModel, Field
from typing import Optional


class ArticleOut(BaseModel):
    id: int
    title: str
    url: str
    source: str
    published_at: Optional[str]
    summary: Optional[str]
    desc: Optional[str]
    tag: Optional[str]
    importance: Optional[str]
    noteworthy: Optional[str]
    fetched_at: Optional[str]
    is_read: int
    is_bookmarked: int

    class Config:
        from_attributes = True


class SourceStatusOut(BaseModel):
    source: str
    last_fetch: Optional[str]
    status: Optional[str]
    error_message: Optional[str]
    item_count: int


class ExportRequest(BaseModel):
    content: str
    vault_path: Optional[str] = None


class MessageResponse(BaseModel):
    success: bool
    message: str
