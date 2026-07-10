import pytest

from services.normalizer import normalize_article


def test_normalize_article_strips_html_from_title_and_desc():
    raw = {
        "title": "<img src=x onerror=alert(1)> normal title <b>bold</b>",
        "url": "https://example.com/article",
        "desc": "<a href='javascript:alert(2)'>click</a> summary",
        "source": "<script>alert(3)</script>Feed",
        "raw_tags": ["<iframe>", "<b>ok</b>", "plain"],
    }
    article = normalize_article(raw)

    assert article["title"] == "normal title bold"
    assert "<" not in article["title"]
    assert article["desc"] == "click summary"
    assert "<" not in article["desc"]
    assert article["source"] == "alert(3)Feed"
    assert "<" not in article["source"]
    assert "<script>" not in article["source"]
    assert article["raw_tags"] == ["ok", "plain"]


def test_normalize_article_keeps_plain_text_intact():
    raw = {
        "title": "Plain text title",
        "url": "https://example.com/article",
    }
    article = normalize_article(raw)
    assert article["title"] == "Plain text title"
    assert article["source"] == "unknown"


def test_normalize_article_rejects_missing_title_or_url():
    assert normalize_article({"title": "", "url": "https://example.com"}) == {}
    assert normalize_article({"title": "Title", "url": ""}) == {}
    assert normalize_article({}) == {}


def test_normalize_article_cleans_url_for_dedup():
    raw = {
        "title": "Title",
        "url": "https://example.com/article?utm_source=x#section",
    }
    article = normalize_article(raw)
    assert article["url"] == "https://example.com/article"
