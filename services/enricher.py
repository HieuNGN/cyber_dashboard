from dataclasses import replace
from typing import Callable

from services.article import Article

# ponytail: rule predicate takes (tag, source, title); tuple-of-strings shape from
# the spec can't express the Memory (title DRAM/HBM) or Vulnerability (source KEV)
# disjunctions that test_enricher.py asserts. Predicates are the minimal honest shape.
Rule = tuple[Callable[[str, str, str], bool], str, str]

ENRICHMENT_RULES: list[Rule] = [
    (lambda tag, src, title: "Memory" in tag or "DRAM" in title or "HBM" in title.upper(),
     "Memory supply and pricing directly affect AI infrastructure buildouts, consumer hardware costs, and datacenter margins.",
     "Watch for DRAM/HBM price moves, supply allocation to AI vs consumer, and foundry capacity announcements."),
    (lambda tag, src, title: "GPU" in tag,
     "GPU availability and pricing shape both AI training capacity and consumer/enterprise upgrade cycles.",
     "Track restock patterns, MSRP changes, and datacenter-vs-gaming allocation."),
    (lambda tag, src, title: "Vulnerability" in tag or "KEV" in src,
     "Active exploitation or high-severity vulnerabilities may require immediate patching or mitigation.",
     "Check affected products/versions, available patches, and whether the flaw is under active exploitation."),
    (lambda tag, src, title: "Ransomware" in tag,
     "Ransomware activity can indicate threat-actor focus areas and viable infection vectors.",
     "Review IOCs, targeted sectors, and initial access methods."),
    (lambda tag, src, title: "AI" in tag,
     "AI model, security, or infrastructure news can shift capability and risk assumptions quickly.",
     "Assess release terms, capability claims, safety mitigations, and competitive implications."),
    (lambda tag, src, title: "Datacenter" in tag,
     "Datacenter infrastructure news affects scale, power, cooling, and supply-chain planning.",
     "Watch for capacity announcements, power/land constraints, and new architectures."),
    (lambda tag, src, title: "Crypto" in tag,
     "Crypto market moves can signal macro risk sentiment and regulatory pressure.",
     "Monitor support/resistance levels and any exchange or regulatory developments."),
    (lambda tag, src, title: "Policy" in tag,
     "Regulatory and policy changes can reshape market access, compliance burden, and cross-border technology flows.",
     "Track effective dates, jurisdictions covered, and industry pushback."),
]

_DEFAULT_IMPORTANCE = "Worth monitoring for strategic or operational relevance to your sector."
_DEFAULT_NOTEWORTHY = "Open the source link for full context and follow-on coverage."


def enrich(article: Article) -> Article:
    """Populate importance/noteworthy heuristically for RSS articles (no LLM)."""
    if article.importance or article.noteworthy:
        return article

    tag = article.tag
    source = article.source
    title = article.title

    importance = _DEFAULT_IMPORTANCE
    noteworthy = _DEFAULT_NOTEWORTHY
    for matches, imp, note in ENRICHMENT_RULES:
        if matches(tag, source, title):
            importance, noteworthy = imp, note
            break

    return replace(article, importance=importance, noteworthy=noteworthy)