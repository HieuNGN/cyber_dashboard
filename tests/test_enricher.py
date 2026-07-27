from dataclasses import replace

import pytest

from services.article import Article
from services.enricher import enrich


@pytest.mark.parametrize("tag,source", [
    ("Hardware / Memory", "S"),
    ("Hardware / GPU", "S"),
    ("Security / Vulnerability", "S"),
    ("Security / Ransomware", "S"),
    ("AI Security", "S"),
    ("AI / Models", "S"),
    ("Hardware / Datacenter", "S"),
    ("Crypto / Markets", "S"),
    ("Policy", "S"),
    ("General / Tech", "S"),  # default branch
])
def test_enrich_populates_importance_and_noteworthy(tag, source):
    article = Article(title="t", url="https://x.com", source=source, tag=tag)
    result = enrich(article)
    assert result.importance
    assert result.noteworthy
    assert result.tag == tag


def test_enrich_returns_unchanged_when_importance_already_set():
    article = Article(
        title="x", url="y", source="S", tag="Hardware / Memory",
        importance="preset", noteworthy="preset",
    )
    result = enrich(article)
    assert result is article
    assert result.importance == "preset"
    assert result.noteworthy == "preset"


def test_enrich_kev_source_triggers_vulnerability_branch():
    article = Article(title="t", url="u", source="CISA KEV", tag="General / Tech")
    result = enrich(article)
    assert "exploitation" in result.importance or "patch" in result.importance.lower()
    assert result.importance  # populated, not empty


def test_enrich_memory_branch_triggers_via_title_when_tag_general():
    # Title contains "HBM" -> Memory branch fires even though tag is General / Tech.
    article = Article(title="HBM shortage reported", url="u", source="S", tag="General / Tech")
    result = enrich(article)
    assert "Memory" in result.importance or "DRAM" in result.importance or "HBM" in result.importance


def test_enrich_returns_new_instance_original_unchanged():
    original = Article(title="t", url="u", source="S", tag="Hardware / Memory")
    result = enrich(original)
    assert result is not original
    assert original.importance == ""
    assert result.importance != ""