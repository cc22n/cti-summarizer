"""Application configuration via pydantic-settings."""

import logging
import warnings

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="ascii",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/cti_summarizer"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # CTI API keys
    nvd_api_key: str = ""
    otx_api_key: str = ""

    # xAI (Grok) LLM
    xai_api_key: str = ""
    xai_base_url: str = "https://api.x.ai/v1"
    xai_model: str = "grok-4-1-fast"

    # RSS feed URLs (comma-separated)
    rss_feed_urls: str = (
        "https://www.bleepingcomputer.com/feed/,"
        "https://krebsonsecurity.com/feed/,"
        "https://feeds.feedburner.com/TheHackersNews"
    )

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"

    # Security
    api_key: str = ""
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # Semantic search
    embedding_model: str = "text-embedding-3-small"

    # Notifications
    webhook_url: str = ""

    # VirusTotal IOC enrichment
    virustotal_api_key: str = ""
    vt_search_query: str = "positives:10+ tag:malware"

    # SMTP (weekly executive report email)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    report_email: str = ""

    # Elasticsearch / Logstash event forwarding
    # Point to an ES REST endpoint OR a Logstash HTTP-input URL.
    # Leave empty to disable forwarding.
    elasticsearch_url: str = ""
    elasticsearch_index: str = "cti-alerts"

    # Summarization tuning
    max_digest_alerts: int = 30
    alert_desc_limit: int = 1500
    digest_desc_limit: int = 300

    # Prediction tuning
    forecast_days: int = 14
    min_nonzero_days: int = 10
    lookback_days: int = 90

    @model_validator(mode="after")
    def _warn_missing_keys(self) -> "Settings":
        _log = logging.getLogger("app.config")
        if not self.xai_api_key:
            _log.warning(
                "XAI_API_KEY is not set — LLM summarization and "
                "semantic search embeddings will be unavailable."
            )
        if not self.jwt_secret_key:
            _log.warning(
                "JWT_SECRET_KEY is not set — write endpoints are "
                "unprotected (dev bypass active)."
            )
        if not self.nvd_api_key:
            _log.warning(
                "NVD_API_KEY is not set — NVD requests will be "
                "rate-limited to 5 req/30s (anonymous tier)."
            )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def rss_feed_urls_list(self) -> list[str]:
        return [u.strip() for u in self.rss_feed_urls.split(",") if u.strip()]


settings = Settings()
