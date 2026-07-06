import re
from typing import Dict, Any, List

TAG_RULES = [
    ("Security / Vulnerability", ["cve", "vulnerability", "exploit", "rce", "patch", "kev"]),
    ("Security / Ransomware", ["ransomware", "ransom", "encrypt", "blackmail"]),
    ("AI Security", ["ai agent", "llm", "prompt injection", "mcp", "ai-generated", "ai model"]),
    ("AI / Models", ["openai", "anthropic", "deepseek", "fable", "gpt-", "claude", "gemini", "llama", "mistral"]),
    ("Hardware / Memory", ["dram", "hbm", "lpddr", "ddr", "ram", "memory", "nand", "ssd", "storage"]),
    ("Hardware / GPU", ["gpu", "rtx", "radeon", "geforce", "arc", "graphics card"]),
    ("Hardware / CPU", ["cpu", "processor", "core", "ryzen", "xeon", "epyc", "snapdragon"]),
    ("Hardware / Datacenter", ["datacenter", "data center", "server", "ai factory", "compute", "microreactor"]),
    ("Hardware / Foundry", ["foundry", "tsmc", "samsung", "intel", "2nm", "3nm", "lithography"]),
    ("Software / Open Source", ["open source", "github", "linux", "podman", "immich"]),
    ("Privacy / Linux", ["luks", "encryption", "privacy", "kernel"]),
    ("Crypto / Markets", ["bitcoin", "btc", "ethereum", "eth", "solana", "sol", "crypto"]),
    ("Enterprise / Networking", ["router", "switch", "firewall", "loadmaster", "vpn", "sd-wan"]),
    ("Policy", ["export control", "regulation", "government", "federal", "cisa", "fcc"]),
]


def _keyword_matches(text: str, keyword: str) -> bool:
    """Match phrase/contains keywords as-is; single-word keywords require word boundaries."""
    if " " in keyword or "-" in keyword:
        return keyword in text
    return re.search(r'\b' + re.escape(keyword) + r'\b', text) is not None


def classify(article: Dict[str, Any]) -> str:
    text = " ".join(filter(None, [
        article.get("title", ""),
        article.get("desc", ""),
        article.get("summary", ""),
        " ".join(str(t) for t in article.get("raw_tags", [])),
    ])).lower()

    for tag, keywords in TAG_RULES:
        if any(_keyword_matches(text, kw) for kw in keywords):
            return tag
    return "General / Tech"
