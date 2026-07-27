from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class Article:
    """Frozen value object threaded through normalize -> dedup -> classify -> enrich -> persist.

    DB columns are included so repository reads can return full Article instances.
    `raw_tags` is pre-persist classification input only (not a SQL column).
    """

    title: str
    url: str
    source: str = "unknown"
    published_at: Optional[str] = None
    summary: str = ""
    desc: str = ""
    tag: str = "General / Tech"
    importance: str = ""
    noteworthy: str = ""
    raw_tags: List[str] = field(default_factory=list)
    id: Optional[int] = None
    fetched_at: Optional[str] = None
    is_read: int = 0
    is_bookmarked: int = 0