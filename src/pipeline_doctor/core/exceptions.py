"""Custom exceptions for Pipeline Doctor."""

from typing import Any


class PipelineDoctorError(Exception):
    """Base exception for Pipeline Doctor."""

    def __init__(self, message: str, code: str = "PIPELINE_DOCTOR_ERROR", details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class ConfigurationError(PipelineDoctorError):
    """Configuration-related errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, "CONFIGURATION_ERROR", details)


class PlatformError(PipelineDoctorError):
    """Platform integration errors."""

    def __init__(self, message: str, platform: str | None = None, details: dict | None = None):
        super().__init__(message, "PLATFORM_ERROR", details)
        self.platform = platform


class AuthenticationError(PlatformError):
    """Authentication failures."""

    def __init__(self, message: str, platform: str | None = None, details: dict | None = None):
        super().__init__(message, platform, details)
        self.code = "AUTHENTICATION_ERROR"


class RateLimitError(PlatformError):
    """Rate limit exceeded."""

    def __init__(
        self, message: str, platform: str | None = None, retry_after: int | None = None, details: dict | None = None
    ):
        super().__init__(message, platform, details)
        self.code = "RATE_LIMIT_ERROR"
        self.retry_after = retry_after


class PipelineNotFoundError(PlatformError):
    """Pipeline not found."""

    def __init__(
        self, message: str, platform: str | None = None, pipeline_id: str | None = None, details: dict | None = None
    ):
        super().__init__(message, platform, details)
        self.code = "PIPELINE_NOT_FOUND"
        self.pipeline_id = pipeline_id


class RunNotFoundError(PlatformError):
    """Pipeline run not found."""

    def __init__(
        self, message: str, platform: str | None = None, run_id: str | None = None, details: dict | None = None
    ):
        super().__init__(message, platform, details)
        self.code = "RUN_NOT_FOUND"
        self.run_id = run_id


class AnalyzerError(PipelineDoctorError):
    """Analyzer execution errors."""

    def __init__(self, message: str, analyzer: str | None = None, details: dict | None = None):
        super().__init__(message, "ANALYZER_ERROR", details)
        self.analyzer = analyzer


class ReporterError(PipelineDoctorError):
    """Reporter generation errors."""

    def __init__(self, message: str, reporter: str | None = None, details: dict | None = None):
        super().__init__(message, "REPORTER_ERROR", details)
        self.reporter = reporter


class NotificationError(PipelineDoctorError):
    """Notification delivery errors."""

    def __init__(self, message: str, channel: str | None = None, details: dict | None = None):
        super().__init__(message, "NOTIFICATION_ERROR", details)
        self.channel = channel


class StorageError(PipelineDoctorError):
    """Storage backend errors."""

    def __init__(self, message: str, operation: str | None = None, details: dict | None = None):
        super().__init__(message, "STORAGE_ERROR", details)
        self.operation = operation


class ValidationError(PipelineDoctorError):
    """Data validation errors."""

    def __init__(self, message: str, field: str | None = None, value: Any | None = None, details: dict | None = None):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field
        self.value = value


class PluginError(PipelineDoctorError):
    """Plugin loading/execution errors."""

    def __init__(self, message: str, plugin: str | None = None, details: dict | None = None):
        super().__init__(message, "PLUGIN_ERROR", details)
        self.plugin = plugin
