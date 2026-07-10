import re
import hashlib
import html
from html.parser import HTMLParser
from typing import Dict, Any, List


class _TextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.text: List[str] = []

    def handle_data(self, data: str) -> None:
        self.text.append(data)

    def handle_starttag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        # Drop inline markup entirely; block tags get a space to separate words.
        if tag.lower() in ("br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"):
            self.text.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in ("p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"):
            self.text.append(" ")

    def handle_entityref(self, name: str) -> None:
        self.text.append("&" + name + ";")

    def handle_charref(self, name: str) -> None:
        self.text.append("&" + name + ";")


def _strip_html(value: str) -> str:
    parser = _TextHTMLParser()
    try:
        parser.feed(value)
        parser.close()
    except Exception:
        pass
    stripped = "".join(parser.text)
    # Remove any leftover/malformed tags as defense-in-depth.
    stripped = re.sub(r"<[^>]*>", " ", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return stripped


def _clean_text(value: Any) -> str:
    """Escape and strip HTML tags; safe to render in HTML contexts with escaping already applied."""
    if value is None:
        return ""
    return html.escape(_strip_html(str(value).strip()))


def _plain_text(value: Any) -> str:
    """Strip HTML tags and normalize text; safe for textContent rendering."""
    if value is None:
        return ""
    return _strip_html(str(value).strip())


def normalize_article(raw: Dict[str, Any]) -> Dict[str, Any]:
    title = _plain_text(raw.get("title"))
    url = (raw.get("url") or "").strip()
    if not title or not url:
        return {}

    # Clean URL for dedup
    url = url.split("?")[0].split("#")[0]

    desc = _plain_text(raw.get("desc") or raw.get("description"))
    summary = _plain_text(raw.get("summary") or desc)

    # Import path: if fields already enriched, keep them
    importance = _plain_text(raw.get("importance"))
    noteworthy = _plain_text(raw.get("noteworthy"))

    raw_tags = raw.get("raw_tags", [])
    if isinstance(raw_tags, (list, tuple)):
        raw_tags = [_plain_text(tag) for tag in raw_tags if _plain_text(tag)]
    else:
        raw_tags = [_plain_text(raw_tags)] if _plain_text(raw_tags) else []

    return {
        "title": title,
        "url": url,
        "source": _plain_text(raw.get("source") or "unknown"),
        "published_at": raw.get("published_at"),
        "summary": summary,
        "desc": desc,
        "importance": importance,
        "noteworthy": noteworthy,
        "raw_tags": raw_tags,
    }


def article_hash(article: Dict[str, Any]) -> str:
    text = f"{article['url']}::{article['title']}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
