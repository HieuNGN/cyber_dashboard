from typing import Dict, Any


def enrich(article: Dict[str, Any]) -> Dict[str, Any]:
    """Populate importance/noteworthy heuristically for RSS articles (no LLM)."""
    if article.get("importance") or article.get("noteworthy"):
        return article

    tag = article.get("tag", "General / Tech")
    source = article.get("source", "")
    title = article.get("title", "")

    importance = ""
    noteworthy = ""

    if "Memory" in tag or "DRAM" in title or "HBM" in title.upper():
        importance = "Memory supply and pricing directly affect AI infrastructure buildouts, consumer hardware costs, and datacenter margins."
        noteworthy = "Watch for DRAM/HBM price moves, supply allocation to AI vs consumer, and foundry capacity announcements."
    elif "GPU" in tag:
        importance = "GPU availability and pricing shape both AI training capacity and consumer/enterprise upgrade cycles."
        noteworthy = "Track restock patterns, MSRP changes, and datacenter-vs-gaming allocation."
    elif "Vulnerability" in tag or "KEV" in source:
        importance = "Active exploitation or high-severity vulnerabilities may require immediate patching or mitigation."
        noteworthy = "Check affected products/versions, available patches, and whether the flaw is under active exploitation."
    elif "Ransomware" in tag:
        importance = "Ransomware activity can indicate threat-actor focus areas and viable infection vectors."
        noteworthy = "Review IOCs, targeted sectors, and initial access methods."
    elif "AI" in tag:
        importance = "AI model, security, or infrastructure news can shift capability and risk assumptions quickly."
        noteworthy = "Assess release terms, capability claims, safety mitigations, and competitive implications."
    elif "Datacenter" in tag:
        importance = "Datacenter infrastructure news affects scale, power, cooling, and supply-chain planning."
        noteworthy = "Watch for capacity announcements, power/land constraints, and new architectures."
    elif "Crypto" in tag:
        importance = "Crypto market moves can signal macro risk sentiment and regulatory pressure."
        noteworthy = "Monitor support/resistance levels and any exchange or regulatory developments."
    elif "Policy" in tag:
        importance = "Regulatory and policy changes can reshape market access, compliance burden, and cross-border technology flows."
        noteworthy = "Track effective dates, jurisdictions covered, and industry pushback."
    else:
        importance = "Worth monitoring for strategic or operational relevance to your sector."
        noteworthy = "Open the source link for full context and follow-on coverage."

    article["importance"] = importance
    article["noteworthy"] = noteworthy
    return article
