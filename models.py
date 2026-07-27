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


class ExportRequest(BaseModel):
    content: str = Field(..., max_length=200_000)
    vault_path: Optional[str] = None
