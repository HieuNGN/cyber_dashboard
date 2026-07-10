from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class DashboardConfig:
    """Explicit config interface used across modules.

    A single frozen instance is created at boot and injected into
    Ingestion, Scheduler, Repository, and Fetchers so tests can
    supply a fake config without touching env files.
    """

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

    # CORS
    cors_origins: List[str] = field(default_factory=lambda: ["*"])

    # Security
    api_key: str = ""

    # Retention (days)
    retention_days: int = 90

    # Limits
    max_articles_per_source: int = 50
    max_summary_length: int = 500

    @property
    def resolved_obsidian_vault_path(self) -> Path:
        return Path(self.obsidian_vault_path).expanduser()

    @property
    def resolved_database_path(self) -> Path:
        return Path(self.database_path).expanduser()


def settings_to_config(settings_obj) -> DashboardConfig:
    """Convert pydantic-settings object to explicit DashboardConfig."""
    return DashboardConfig(
        update_interval_hours=settings_obj.update_interval_hours,
        timezone=settings_obj.timezone,
        fetch_on_startup=settings_obj.fetch_on_startup,
        startup_staleness_minutes=settings_obj.startup_staleness_minutes,
        host=settings_obj.host,
        port=settings_obj.port,
        database_path=settings_obj.database_path,
        obsidian_vault_path=settings_obj.obsidian_vault_path,
        fetch_hackernews=settings_obj.fetch_hackernews,
        fetch_bleepingcomputer=settings_obj.fetch_bleepingcomputer,
        fetch_krebs=settings_obj.fetch_krebs,
        fetch_cisa_kev=settings_obj.fetch_cisa_kev,
        fetch_tomshardware=settings_obj.fetch_tomshardware,
        fetch_servethehome=settings_obj.fetch_servethehome,
        fetch_wccftech=settings_obj.fetch_wccftech,
        fetch_theregister=settings_obj.fetch_theregister,
        cors_origins=settings_obj.cors_origins_list,
        api_key=settings_obj.api_key,
        retention_days=settings_obj.retention_days,
        max_articles_per_source=settings_obj.max_articles_per_source,
        max_summary_length=settings_obj.max_summary_length,
    )
