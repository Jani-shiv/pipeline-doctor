"""Jenkins integration."""

from datetime import datetime
from typing import Any
from urllib.parse import urljoin
from uuid import uuid4

import httpx

from pipeline_doctor.core.exceptions import AuthenticationError
from pipeline_doctor.core.models import (
    Pipeline,
    PipelinePlatform,
    PipelineRun,
    PipelineStatus,
)
from pipeline_doctor.core.utils import retry_with_backoff
from pipeline_doctor.integrations.base import BaseIntegration, IntegrationRegistry


@IntegrationRegistry.register
class JenkinsIntegration(BaseIntegration):
    """Jenkins API integration."""

    platform = PipelinePlatform.JENKINS

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.url = self.config.get("url")
        self.job_name = self.config.get("job_name")

        # HTTP client
        # Type is defined in base class

    async def connect(self) -> None:
        """Establish connection to Jenkins."""
        if not self.url:
            raise ValueError("Jenkins URL is required")

        auth = None
        if self.username and self.token:
            auth = (self.username, self.token)
        elif self.token:
            # API token as password with any username
            auth = ("admin", self.token)

        self._client = httpx.AsyncClient(
            auth=auth,
            timeout=self.timeout,
            verify=self.verify_ssl,
        )

        # Test connection
        await self._test_connection()

    async def _test_connection(self) -> None:
        """Test Jenkins connection."""
        if not self._client:
            raise RuntimeError("Client not initialized")
        if not self.url:
            raise ValueError("Jenkins URL must be configured")
        try:
            response = await self._client.get(urljoin(self.url, "/api/json"))
            response.raise_for_status()
        except Exception as e:
            raise AuthenticationError(
                f"Failed to connect to Jenkins: {e}", platform=self.platform.value
            )

    async def disconnect(self) -> None:
        """Close connection."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_job_url(self) -> str:
        """Get job URL for API calls."""
        if not self.job_name:
            raise ValueError("Job name must be configured")
        if not self.url:
            raise ValueError("Jenkins URL must be configured")
        return str(urljoin(self.url, f"/job/{self.job_name}/"))

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_pipeline(self, pipeline_id: str) -> Pipeline:
        """Get job by name."""
        job_url = self._get_job_url()
        data = await self._make_request("GET", f"{job_url}api/json")

        return Pipeline(
            id=uuid4(),
            name=data.get("name", self.job_name),
            platform=PipelinePlatform.JENKINS,
            repository=self.config.get("repository", ""),
            platform_id=data.get("name"),
            metadata={"jenkins_data": data},
        )

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_pipeline_runs(
        self,
        pipeline_id: str,
        limit: int = 100,
        offset: int = 0,
        status: PipelineStatus | None = None,
    ) -> list[PipelineRun]:
        """Get build history."""
        job_url = self._get_job_url()
        data = await self._make_request(
            "GET",
            f"{job_url}api/json",
            params={"tree": "builds[number,result,timestamp,duration,url,building]"},
        )

        runs = []
        builds = data.get("builds", [])[offset : offset + limit]
        for build_data in builds:
            run = self._parse_build(build_data)
            if status is None or run.status == status:
                runs.append(run)
        return runs

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_run(self, pipeline_id: str, run_id: str) -> PipelineRun:
        """Get specific build."""
        job_url = self._get_job_url()
        data = await self._make_request("GET", f"{job_url}{run_id}/api/json")
        return self._parse_build(data)

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_run_logs(
        self, pipeline_id: str, run_id: str, job_id: str | None = None
    ) -> dict[str, Any]:
        """Get build logs."""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")
        if not self.job_name:
            raise ValueError("Job name must be configured")
        job_url = self._get_job_url()
        response = await self._client.get(
            f"{job_url}{run_id}/logText/progressiveText", params={"start": 0}
        )
        response.raise_for_status()
        return {"logs": response.text}

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def trigger_pipeline(
        self, pipeline_id: str, params: dict[str, Any] | None = None
    ) -> PipelineRun:
        """Trigger a new build."""
        job_url = self._get_job_url()
        trigger_url = f"{job_url}buildWithParameters" if params else f"{job_url}build"
        await self._make_request("POST", trigger_url, params=params or {})

        # Jenkins returns 201 with Location header for queue item
        # For simplicity, return a placeholder
        return PipelineRun(
            id=uuid4(),
            pipeline_id=uuid4(),
            number=0,
            status=PipelineStatus.PENDING,
            metadata={"triggered": True},
        )

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def cancel_run(self, pipeline_id: str, run_id: str) -> bool:
        """Cancel a build."""
        job_url = self._get_job_url()
        await self._make_request("POST", f"{job_url}{run_id}/stop")
        return True

    def _parse_build(self, data: dict[str, Any]) -> PipelineRun:
        """Parse Jenkins build data."""
        run_id = uuid4()

        timestamp = data.get("timestamp", 0)
        started_at = datetime.fromtimestamp(timestamp / 1000) if timestamp else None
        duration_ms = data.get("duration", 0)
        completed_at = None
        if started_at and duration_ms:
            from datetime import timedelta

            completed_at = started_at + timedelta(milliseconds=duration_ms)

        return PipelineRun(
            id=run_id,
            pipeline_id=uuid4(),
            number=data.get("number", 0),
            status=self._parse_jenkins_status(data.get("result"), data.get("building", False)),
            trigger="manual",
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_ms / 1000 if duration_ms else None,
            url=data.get("url"),
            metadata={"jenkins_data": data},
        )

    def _parse_jenkins_status(self, result: str | None, building: bool) -> PipelineStatus:
        """Parse Jenkins result to PipelineStatus."""
        if building:
            return PipelineStatus.RUNNING

        if not result:
            return PipelineStatus.UNKNOWN

        result_lower = result.lower()
        if result_lower == "success":
            return PipelineStatus.SUCCESS
        elif result_lower in ("failure", "unstable", "aborted"):
            return PipelineStatus.FAILURE
        elif result_lower == "not_built":
            return PipelineStatus.SKIPPED
        return PipelineStatus.UNKNOWN
