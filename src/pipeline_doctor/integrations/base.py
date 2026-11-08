"""Base integration class."""

from abc import ABC, abstractmethod
from typing import Any

from pipeline_doctor.core.exceptions import (
    AuthenticationError,
    PipelineNotFoundError,
    PlatformError,
    RateLimitError,
)
from pipeline_doctor.core.models import (
    Pipeline,
    PipelinePlatform,
    PipelineRun,
    PipelineStatus,
)
from pipeline_doctor.core.utils import AsyncRateLimiter


class BaseIntegration(ABC):
    """Base class for platform integrations."""

    platform: PipelinePlatform

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}
        self.token = self.config.get("token")
        self.api_url = self.config.get("api_url")
        self.username = self.config.get("username")
        self.password = self.config.get("password")
        self.verify_ssl = self.config.get("verify_ssl", True)
        self.timeout = self.config.get("timeout", 30)
        self.rate_limit = self.config.get("rate_limit", 100)

        # Rate limiter
        self._rate_limiter = AsyncRateLimiter(self.rate_limit, per=60.0)

        # HTTP client (initialized in connect)
        self._client = None

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to platform."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to platform."""
        pass

    @abstractmethod
    async def get_pipeline(self, pipeline_id: str) -> Pipeline:
        """Get pipeline by ID."""
        pass

    @abstractmethod
    async def get_pipeline_runs(
        self,
        pipeline_id: str,
        limit: int = 100,
        offset: int = 0,
        status: PipelineStatus | None = None,
    ) -> list[PipelineRun]:
        """Get pipeline runs."""
        pass

    @abstractmethod
    async def get_run(self, pipeline_id: str, run_id: str) -> PipelineRun:
        """Get specific pipeline run."""
        pass

    @abstractmethod
    async def get_run_logs(
        self, pipeline_id: str, run_id: str, job_id: str = None
    ) -> dict[str, Any]:
        """Get logs for a run or job."""
        pass

    @abstractmethod
    async def trigger_pipeline(
        self, pipeline_id: str, params: dict[str, Any] = None
    ) -> PipelineRun:
        """Trigger a new pipeline run."""
        pass

    @abstractmethod
    async def cancel_run(self, pipeline_id: str, run_id: str) -> bool:
        """Cancel a running pipeline."""
        pass

    async def _make_request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] = None,
        json: dict[str, Any] = None,
        headers: dict[str, str] = None,
    ) -> Any:
        """Make HTTP request with rate limiting and error handling."""
        await self._rate_limiter.acquire()

        if not self._client:
            raise PlatformError("Not connected. Call connect() first.")

        url = f"{self.api_url.rstrip('/')}/{path.lstrip('/')}"
        request_headers = {"Accept": "application/json"}
        if headers:
            request_headers.update(headers)

        try:
            response = await self._client.request(
                method=method,
                url=url,
                params=params,
                json=json,
                headers=request_headers,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # Handle specific error types
            if hasattr(e, "response") and e.response is not None:
                status = e.response.status_code
                if status == 401:
                    raise AuthenticationError(
                        f"Authentication failed: {e}", platform=self.platform.value
                    )
                elif status == 403:
                    raise AuthenticationError(
                        f"Access forbidden: {e}", platform=self.platform.value
                    )
                elif status == 404:
                    raise PipelineNotFoundError(
                        f"Resource not found: {e}", platform=self.platform.value
                    )
                elif status == 429:
                    retry_after = int(e.response.headers.get("Retry-After", 60))
                    raise RateLimitError(
                        f"Rate limited: {e}",
                        platform=self.platform.value,
                        retry_after=retry_after,
                    )
            raise PlatformError(f"Request failed: {e}", platform=self.platform.value) from e

    def _parse_status(self, status: str) -> PipelineStatus:
        """Parse platform-specific status to PipelineStatus."""
        status_lower = status.lower()
        if status_lower in ("success", "passed", "completed", "succeeded", "green"):
            return PipelineStatus.SUCCESS
        elif status_lower in ("failure", "failed", "error", "red", "broken"):
            return PipelineStatus.FAILURE
        elif status_lower in ("cancelled", "canceled", "aborted"):
            return PipelineStatus.CANCELLED
        elif status_lower in ("skipped", "skipped"):
            return PipelineStatus.SKIPPED
        elif status_lower in ("timeout", "timed_out"):
            return PipelineStatus.TIMEOUT
        elif status_lower in ("running", "in_progress", "pending", "queued", "started"):
            return PipelineStatus.RUNNING
        return PipelineStatus.UNKNOWN

    def _create_pipeline_run(self, data: dict[str, Any]) -> PipelineRun:
        """Create PipelineRun from platform data (to be overridden)."""
        raise NotImplementedError


class IntegrationRegistry:
    """Registry for managing platform integrations."""

    _integrations: dict[str, type] = {}

    @classmethod
    def register(cls, integration_class: type) -> type:
        """Register an integration class."""
        if not issubclass(integration_class, BaseIntegration):
            raise PlatformError(f"{integration_class} is not a BaseIntegration")
        cls._integrations[integration_class.platform.value] = integration_class
        return integration_class

    @classmethod
    def get(cls, platform: str) -> type | None:
        """Get integration class by platform."""
        return cls._integrations.get(platform)

    @classmethod
    def create(cls, platform: str, config: dict[str, Any] = None) -> BaseIntegration | None:
        """Create integration instance."""
        integration_class = cls.get(platform)
        if not integration_class:
            return None
        return integration_class(config)

    @classmethod
    def list_available(cls) -> list[str]:
        """List all registered integration platforms."""
        return list(cls._integrations.keys())
