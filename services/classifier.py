import re
from typing import List

from config import TAG_RULES
from services.article import Article


def _keyword_matches(text: str, keyword: str) -> bool:
    """Match phrase/contains keywords as-is; single-word keywords require word boundaries."""
    if " " in keyword or "-" in keyword:
        return keyword in text
    return re.search(r'\b' + re.escape(keyword) + r'\b', text) is not None


def classify(article: Article) -> str:
    text = " ".join(filter(None, [
        article.title,
        article.desc,
        article.summary,
        " ".join(str(t) for t in article.raw_tags),
    ])).lower()

    for tag, keywords in TAG_RULES:
        if any(_keyword_matches(text, kw) for kw in keywords):
            return tag
    return "General / Tech"