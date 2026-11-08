"""CircleCI integration."""

from datetime import datetime
from typing import Any
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
class CircleCIIntegration(BaseIntegration):
    """CircleCI API integration."""

    platform = PipelinePlatform.CIRCLECI

    def __init__(self, config: dict[str, Any] = None):
        super().__init__(config)
        self.api_url = self.config.get("api_url", "https://circleci.com/api/v2")
        self.project_slug = self.config.get("project_slug")  # e.g., "gh/org/repo"

    async def connect(self) -> None:
        """Establish connection to CircleCI."""
        if not self.token:
            raise AuthenticationError("CircleCI token is required", platform=self.platform.value)
        if not self.project_slug:
            raise ValueError("Project slug must be configured")

        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            },
            timeout=self.timeout,
            verify=self.verify_ssl,
        )

    async def disconnect(self) -> None:
        """Close connection."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_pipeline(self, pipeline_id: str) -> Pipeline:
        """Get pipeline by ID."""
        data = await self._make_request("GET", f"{self.api_url}/pipeline/{pipeline_id}")

        return Pipeline(
            id=uuid4(),
            name=f"Pipeline {pipeline_id}",
            platform=PipelinePlatform.CIRCLECI,
            repository=self.project_slug,
            platform_id=pipeline_id,
            metadata={"circleci_data": data},
        )

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_pipeline_runs(
        self,
        pipeline_id: str,
        limit: int = 100,
        offset: int = 0,
        status: PipelineStatus | None = None,
    ) -> list[PipelineRun]:
        """Get pipeline runs (workflows)."""
        params = {"page-token": offset, "limit": min(limit, 100)}

        data = await self._make_request(
            "GET", f"{self.api_url}/project/{self.project_slug}/pipeline", params=params
        )

        runs = []
        for run_data in data.get("items", []):
            run = self._parse_pipeline(run_data)
            if status is None or run.status == status:
                runs.append(run)
        return runs

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_run(self, pipeline_id: str, run_id: str) -> PipelineRun:
        """Get specific pipeline."""
        data = await self._make_request("GET", f"{self.api_url}/pipeline/{run_id}")
        return self._parse_pipeline(data)

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_run_logs(
        self, pipeline_id: str, run_id: str, job_id: str = None
    ) -> dict[str, Any]:
        """Get logs for a pipeline or job."""
        if job_id:
            # Get job logs
            response = await self._client.get(
                f"{self.api_url}/job/{job_id}/output",
            )
            response.raise_for_status()
            return {"logs": response.text}
        else:
            # Get workflow jobs
            data = await self._make_request("GET", f"{self.api_url}/pipeline/{run_id}/workflow")
            workflow_id = data.get("id")
            if workflow_id:
                jobs_data = await self._make_request(
                    "GET", f"{self.api_url}/workflow/{workflow_id}/job"
                )
                return {"jobs": jobs_data.get("items", [])}
            return {"jobs": []}

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def trigger_pipeline(
        self, pipeline_id: str, params: dict[str, Any] = None
    ) -> PipelineRun:
        """Trigger a new pipeline."""
        data = await self._make_request(
            "POST",
            f"{self.api_url}/project/{self.project_slug}/pipeline",
            json={
                "branch": params.get("branch", "main") if params else "main",
                "parameters": params.get("parameters", {}) if params else {},
            },
        )
        return self._parse_pipeline(data)

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def cancel_run(self, pipeline_id: str, run_id: str) -> bool:
        """Cancel a pipeline."""
        await self._make_request("POST", f"{self.api_url}/pipeline/{run_id}/cancel")
        return True

    def _parse_pipeline(self, data: dict[str, Any]) -> PipelineRun:
        """Parse CircleCI pipeline data."""
        run_id = uuid4()

        started_at = None
        completed_at = None
        if data.get("created_at"):
            started_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        if data.get("updated_at"):
            completed_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))

        return PipelineRun(
            id=run_id,
            pipeline_id=uuid4(),
            number=data.get("number", 0),
            status=self._parse_circleci_status(data.get("state")),
            trigger=data.get("trigger", {}).get("type", "manual"),
            branch=data.get("vcs", {}).get("branch_name"),
            commit_sha=data.get("vcs", {}).get("revision"),
            started_at=started_at,
            completed_at=completed_at,
            url=f"https://app.circleci.com/pipelines/{self.project_slug}/{data.get('number')}",
            metadata={"circleci_data": data},
        )

    def _parse_circleci_status(self, state: str) -> PipelineStatus:
        """Parse CircleCI state to PipelineStatus."""
        if not state:
            return PipelineStatus.UNKNOWN

        state_lower = state.lower()
        if state_lower == "success":
            return PipelineStatus.SUCCESS
        elif state_lower in ("failed", "error", "canceled", "unauthorized"):
            if state_lower == "canceled":
                return PipelineStatus.CANCELLED
            return PipelineStatus.FAILURE
        elif state_lower in ("running", "on_hold", "pending", "queued"):
            return PipelineStatus.RUNNING
        return PipelineStatus.UNKNOWN
