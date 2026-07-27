import pytest

from services.article import Article
from services.classifier import classify


@pytest.mark.parametrize("tag,keyword", [
    ("Security / Vulnerability", "cve"),
    ("Security / Ransomware", "ransomware"),
    ("AI Security", "prompt injection"),
    ("AI / Models", "openai"),
    ("Hardware / Memory", "dram"),
    ("Hardware / GPU", "gpu"),
    ("Hardware / CPU", "ryzen"),
    ("Hardware / Datacenter", "datacenter"),
    ("Hardware / Foundry", "tsmc"),
    ("Software / Open Source", "linux"),
    ("Privacy / Linux", "luks"),
    ("Crypto / Markets", "bitcoin"),
    ("Enterprise / Networking", "firewall"),
    ("Policy", "export control"),
])
def test_classify_assigns_tag_for_keyword(tag, keyword):
    article = Article(title=f"News about {keyword}", url="https://x.com")
    assert classify(article) == tag


def test_classify_first_match_wins_when_multiple_rules_match():
    # Both "cve" (rule 1) and "ransomware" (rule 2) match; rule 1 wins.
    article = Article(title="cve ransomware alert", url="https://x.com")
    assert classify(article) == "Security / Vulnerability"


def test_classify_falls_back_to_general_when_no_keyword_matches():
    article = Article(title="a quiet day in the park", url="https://x.com")
    assert classify(article) == "General / Tech"


def test_classify_single_word_keyword_uses_word_boundary():
    # "ram" is a single-word keyword -> word-boundary match. "programming" must NOT match.
    article = Article(title="programming tutorial", url="https://x.com")
    assert classify(article) == "General / Tech"
    # But "ram" alone does match.
    article_match = Article(title="ram upgrade guide", url="https://x.com")
    assert classify(article_match) == "Hardware / Memory"


def test_classify_phrase_keyword_uses_contains():
    # "export control" is a phrase keyword -> contains match.
    article = Article(title="new export control rules issued", url="https://x.com")
    assert classify(article) == "Policy"


def test_classify_considers_raw_tags_for_matching():
    article = Article(title="", url="https://x.com", raw_tags=["cve"])
    assert classify(article) == "Security / Vulnerability"