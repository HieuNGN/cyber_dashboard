from pathlib import Path
from typing import List, Tuple

from pydantic_settings import BaseSettings


# Classifier tag rules: (tag, keywords). Static data — lives in config, not logic.
TAG_RULES: List[Tuple[str, List[str]]] = [
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


class Settings(BaseSettings):
    # Schedule
    update_interval_hours: int = 12
    timezone: str = "Asia/Bangkok"
    fetch_on_startup: bool = True
    startup_staleness_minutes: int = 30

    # Server
    host: str = "127.0.0.1"
    port: int = 8080

    # Paths
    database_path: str = "data/dashboard.db"
    obsidian_vault_path: str = "~/Documents/Obsidian Vault"

    # Source toggles
    fetch_hackernews: bool = True
    fetch_bleepingcomputer: bool = True
    fetch_krebs: bool = True
    fetch_cisa_kev: bool = True
    fetch_tomshardware: bool = True
    fetch_servethehome: bool = True
    fetch_wccftech: bool = True
    fetch_theregister: bool = True

    # CORS — comma-separated list of allowed origins. Empty or "*" enables all origins (not recommended for production).
    cors_origins: str = ""

    # Security
    api_key: str = ""

    # Retention (days)
    retention_days: int = 90

    # Limits
    max_articles_per_source: int = 50
    max_summary_length: int = 500

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.cors_origins or self.cors_origins.strip() == "":
            return []
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def resolved_obsidian_vault_path(self) -> Path:
        return Path(self.obsidian_vault_path).expanduser()

    @property
    def resolved_database_path(self) -> Path:
        return Path(self.database_path).expanduser()


settings = Settings()
