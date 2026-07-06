from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Schedule
    daily_update_time: str = "07:00"
    timezone: str = "Asia/Bangkok"

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

    # CORS
    cors_origins: str = "*"

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
        if not self.cors_origins or self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def resolved_obsidian_vault_path(self) -> Path:
        return Path(self.obsidian_vault_path).expanduser()

    @property
    def resolved_database_path(self) -> Path:
        return Path(self.database_path).expanduser()


settings = Settings()
