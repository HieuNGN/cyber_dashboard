from services.article import Article
from services.dedup import Deduplicator


def test_is_duplicate_returns_true_for_same_url():
    dedup = Deduplicator()
    a1 = Article(title="Title One", url="https://example.com/a")
    a2 = Article(title="Title Two", url="https://example.com/a")
    assert dedup.is_duplicate(a1) is False
    assert dedup.is_duplicate(a2) is True


def test_is_duplicate_returns_true_for_same_title_different_url():
    dedup = Deduplicator()
    a1 = Article(title="Same Title", url="https://example.com/a")
    a2 = Article(title="Same Title", url="https://example.com/b")
    assert dedup.is_duplicate(a1) is False
    assert dedup.is_duplicate(a2) is True


def test_is_duplicate_is_case_insensitive_on_title():
    dedup = Deduplicator()
    a1 = Article(title="Title", url="https://example.com/a")
    a2 = Article(title="TITLE", url="https://example.com/b")
    assert dedup.is_duplicate(a1) is False
    assert dedup.is_duplicate(a2) is True


def test_is_duplicate_returns_false_for_distinct_articles():
    dedup = Deduplicator()
    a1 = Article(title="Title One", url="https://example.com/a")
    a2 = Article(title="Title Two", url="https://example.com/b")
    assert dedup.is_duplicate(a1) is False
    assert dedup.is_duplicate(a2) is False