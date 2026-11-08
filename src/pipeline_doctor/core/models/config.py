"""Configuration models."""

from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PlatformConfig(BaseModel):
    """Configuration for a CI/CD platform."""

    enabled: bool = True
    token: str | None = None
    api_url: str | None = None
    username: str | None = None
    password: str | None = None
    verify_ssl: bool = True
    timeout: int = 30
    rate_limit: int = 100  # requests per minute
    extra: dict[str, Any] = Field(default_factory=dict)


class AnalyzerConfig(BaseModel):
    """Configuration for an analyzer."""

    enabled: bool = True
    module: str | None = None  # Custom analyzer module path
    class_name: str | None = None  # Custom analyzer class name
    config: dict[str, Any] = Field(default_factory=dict)
    timeout: int = 60


class ReporterConfig(BaseModel):
    """Configuration for a reporter."""

    enabled: bool = True
    module: str | None = None
    class_name: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    output_dir: str = "./reports"


class NotificationConfig(BaseModel):
    """Configuration for notifications."""

    enabled: bool = False
    webhook_url: str | None = None
    channel: str | None = None
    username: str | None = None
    icon_emoji: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    from_email: str | None = None
    to_emails: list[str] = Field(default_factory=list)
    pagerduty_key: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class StorageConfig(BaseModel):
    """Configuration for data storage."""

    type: str = "sqlite"  # sqlite, postgresql, mongodb
    path: str = "./data/pipeline-doctor.db"
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None
    pool_size: int = 5
    max_overflow: int = 10
    echo: bool = False


class PipelineDoctorConfig(BaseSettings):
    """Main configuration for Pipeline Doctor."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="allow",
    )

    # Application settings
    app_name: str = "pipeline-doctor"
    version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"
    log_format: str = "json"  # json, console

    # Platform configurations
    platforms: dict[str, PlatformConfig] = Field(default_factory=dict)

    # Analyzer configurations
    analyzers: dict[str, AnalyzerConfig] = Field(default_factory=dict)

    # Reporter configurations
    reporters: dict[str, ReporterConfig] = Field(default_factory=dict)
    default_reporter: str = "html"

    # Notification configurations
    notifications: dict[str, NotificationConfig] = Field(default_factory=dict)

    # Storage configuration
    storage: StorageConfig = Field(default_factory=StorageConfig)

    # Analysis settings
    max_concurrent_analyzers: int = 5
    analysis_timeout: int = 300
    cache_ttl: int = 3600

    # Default analyzer configs
    def get_default_analyzers(self) -> dict[str, AnalyzerConfig]:
        return {
            "failure": AnalyzerConfig(
                enabled=True,
                config={
                    "patterns": [
                        "timeout",
                        "out of memory",
                        "permission denied",
                        "connection refused",
                        "disk full",
                        "segmentation fault",
                        "killed",
                        "exit code 1",
                        "exit code 137",
                        "exit code 139",
                    ],
                    "custom_patterns": [],
                },
            ),
            "performance": AnalyzerConfig(
                enabled=True,
                config={
                    "thresholds": {
                        "job_duration_warn": 300,
                        "job_duration_critical": 600,
                        "step_duration_warn": 60,
                        "step_duration_critical": 180,
                        "queue_time_warn": 120,
                        "queue_time_critical": 300,
                    },
                    "compare_baseline": True,
                    "baseline_runs": 10,
                },
            ),
            "security": AnalyzerConfig(
                enabled=True,
                config={
                    "scan_secrets": True,
                    "scan_dependencies": True,
                    "scan_misconfigurations": True,
                    "secret_patterns": [
                        r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{20,}['\"]?",
                        r"(?i)(aws[_-]?access[_-]?key|aws[_-]?secret[_-]?key)\s*[:=]\s*['\"]?[A-Z0-9]{20,}['\"]?",
                        r"(?i)(github[_-]?token|gh[_-]?pat)\s*[:=]\s*['\"]?gh[ps]_[a-zA-Z0-9]{36}['\"]?",
                    ],
                },
            ),
            "cost": AnalyzerConfig(
                enabled=True,
                config={
                    "currency": "USD",
                    "compute_cost_per_minute": 0.008,
                    "storage_cost_per_gb_month": 0.10,
                    "network_cost_per_gb": 0.09,
                    "track_waste": True,
                    "waste_threshold_minutes": 10,
                },
            ),
            "reliability": AnalyzerConfig(
                enabled=True,
                config={
                    "flaky_threshold": 0.1,
                    "min_runs_for_flaky": 10,
                    "check_retries": True,
                    "check_timeouts": True,
                },
            ),
        }

    def get_default_reporters(self) -> dict[str, ReporterConfig]:
        return {
            "html": ReporterConfig(
                enabled=True,
                config={
                    "template": "default",
                    "include_charts": True,
                    "include_raw_data": False,
                    "theme": "light",
                },
            ),
            "json": ReporterConfig(
                enabled=True,
                config={
                    "pretty": True,
                    "include_metadata": True,
                },
            ),
            "markdown": ReporterConfig(
                enabled=True,
                config={
                    "include_summary": True,
                    "include_details": True,
                    "table_format": "github",
                },
            ),
            "pdf": ReporterConfig(
                enabled=True,
                config={
                    "page_size": "A4",
                    "margin": "2cm",
                    "include_charts": True,
                },
            ),
        }

    def get_default_notifications(self) -> dict[str, NotificationConfig]:
        return {
            "slack": NotificationConfig(enabled=False),
            "email": NotificationConfig(enabled=False),
            "pagerduty": NotificationConfig(enabled=False),
            "webhook": NotificationConfig(enabled=False),
        }


def load_config(config_path: str | None = None) -> PipelineDoctorConfig:
    """Load configuration from file and environment."""
    config = PipelineDoctorConfig()

    if config_path:
        import yaml
        with open(config_path) as f:
            file_config = yaml.safe_load(f)
            if file_config:
                config = PipelineDoctorConfig.model_validate(
                    {**config.model_dump(), **file_config}
                )

    # Merge defaults
    for name, analyzer in config.get_default_analyzers().items():
        if name not in config.analyzers:
            config.analyzers[name] = analyzer

    for name, reporter in config.get_default_reporters().items():
        if name not in config.reporters:
            config.reporters[name] = reporter

    for name, notification in config.get_default_notifications().items():
        if name not in config.notifications:
            config.notifications[name] = notification

    return config
