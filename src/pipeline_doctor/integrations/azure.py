"""Azure DevOps integration."""

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
class AzureDevOpsIntegration(BaseIntegration):
    """Azure DevOps API integration."""

    platform = PipelinePlatform.AZURE_DEVOPS

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.organization = self.config.get("organization")
        self.project = self.config.get("project")
        self.api_url = self.config.get("api_url", "https://dev.azure.com")

    async def connect(self) -> None:
        """Establish connection to Azure DevOps."""
        if not self.token:
            raise AuthenticationError("Azure DevOps PAT is required", platform=self.platform.value)
        if not self.organization or not self.project:
            raise ValueError("Organization and project must be configured")

        # Azure DevOps uses Basic auth with PAT as password
        auth = ("", self.token)

        self._client = httpx.AsyncClient(
            auth=auth,
            headers={
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

    def _get_base_url(self) -> str:
        """Get base API URL."""
        return f"{self.api_url}/{self.organization}/{self.project}/_apis"

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_pipeline(self, pipeline_id: str) -> Pipeline:
        """Get pipeline by ID."""
        base_url = self._get_base_url()
        data = await self._make_request(
            "GET", f"{base_url}/pipelines/{pipeline_id}?api-version=7.1"
        )

        return Pipeline(
            id=uuid4(),
            name=data.get("name", ""),
            platform=PipelinePlatform.AZURE_DEVOPS,
            repository=self.config.get("repository", ""),
            platform_id=str(data.get("id")),
            metadata={"azure_data": data},
        )

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_pipeline_runs(
        self,
        pipeline_id: str,
        limit: int = 100,
        offset: int = 0,
        status: PipelineStatus | None = None,
    ) -> list[PipelineRun]:
        """Get pipeline runs."""
        base_url = self._get_base_url()
        params = {
            "api-version": "7.1",
            "$top": min(limit, 100),
            "$skip": offset,
        }
        if status:
            params["resultFilter"] = self._status_to_azure(status)  # type: ignore[assignment]

        data = await self._make_request(
            "GET", f"{base_url}/pipelines/{pipeline_id}/runs", params=params
        )

        runs = []
        for run_data in data.get("value", []):
            runs.append(self._parse_run(run_data))
        return runs

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_run(self, pipeline_id: str, run_id: str) -> PipelineRun:
        """Get specific pipeline run."""
        base_url = self._get_base_url()
        data = await self._make_request(
            "GET", f"{base_url}/pipelines/{pipeline_id}/runs/{run_id}?api-version=7.1"
        )
        return self._parse_run(data)

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_run_logs(
        self, pipeline_id: str, run_id: str, job_id: str | None = None
    ) -> dict[str, Any]:
        """Get logs for a run or job."""
        base_url = self._get_base_url()

        if job_id:
            # Get job logs
            if not self._client:
                raise RuntimeError("Not connected. Call connect() first.")
            response = await self._client.get(
                f"{base_url}/pipelines/{pipeline_id}/runs/{run_id}/jobs/{job_id}/logs?api-version=7.1",
            )
            response.raise_for_status()
            return {"logs": response.text}
        else:
            # Get all jobs/stages for the run
            data = await self._make_request(
                "GET",
                f"{base_url}/pipelines/{pipeline_id}/runs/{run_id}?api-version=7.1",
            )
            return {"stages": data.get("stages", [])}

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def trigger_pipeline(
        self, pipeline_id: str, params: dict[str, Any] | None = None
    ) -> PipelineRun:
        """Trigger a new pipeline run."""
        base_url = self._get_base_url()
        data = await self._make_request(
            "POST",
            f"{base_url}/pipelines/{pipeline_id}/runs?api-version=7.1",
            json={
                "resources": params.get("resources", {}) if params else {},
                "variables": params.get("variables", {}) if params else {},
            },
        )
        return self._parse_run(data)

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def cancel_run(self, pipeline_id: str, run_id: str) -> bool:
        """Cancel a pipeline run."""
        base_url = self._get_base_url()
        await self._make_request(
            "PATCH",
            f"{base_url}/pipelines/{pipeline_id}/runs/{run_id}?api-version=7.1",
            json={"state": "canceling"},
        )
        return True

    def _status_to_azure(self, status: PipelineStatus) -> str:
        """Convert PipelineStatus to Azure DevOps filter."""
        mapping = {
            PipelineStatus.SUCCESS: "succeeded",
            PipelineStatus.FAILURE: "failed",
            PipelineStatus.CANCELLED: "canceled",
            PipelineStatus.RUNNING: "inProgress",
            PipelineStatus.PENDING: "notStarted",
        }
        return mapping.get(status, "succeeded")

    def _parse_run(self, data: dict[str, Any]) -> PipelineRun:
        """Parse Azure DevOps pipeline run data."""
        run_id = uuid4()

        started_at = None
        completed_at = None
        if data.get("createdDate"):
            started_at = datetime.fromisoformat(data["createdDate"].replace("Z", "+00:00"))
        if data.get("finishedDate"):
            completed_at = datetime.fromisoformat(data["finishedDate"].replace("Z", "+00:00"))

        return PipelineRun(
            id=run_id,
            pipeline_id=uuid4(),
            number=data.get("runNumber", 0),
            status=self._parse_azure_status(data.get("result"), data.get("state")),
            trigger=data.get("reason", "manual"),
            branch=data.get("sourceBranch", "").replace("refs/heads/", ""),
            commit_sha=data.get("sourceVersion"),
            url=data.get("_links", {}).get("web", {}).get("href"),
            started_at=started_at,
            completed_at=completed_at,
            metadata={"azure_data": data},
        )

    def _parse_azure_status(self, result: str | None, state: str | None) -> PipelineStatus:
        """Parse Azure DevOps result/state to PipelineStatus."""
        if state:
            state_lower = state.lower()
            if state_lower in ("inprogress", "running"):
                return PipelineStatus.RUNNING
            elif state_lower == "notstarted":
                return PipelineStatus.PENDING
            elif state_lower == "cancelling":
                return PipelineStatus.CANCELLED
            elif state_lower == "completed":
                if result:
                    result_lower = result.lower()
                    if result_lower == "succeeded":
                        return PipelineStatus.SUCCESS
                    elif result_lower in ("failed", "canceled"):
                        return (
                            PipelineStatus.FAILURE
                            if result_lower == "failed"
                            else PipelineStatus.CANCELLED
                        )
        return PipelineStatus.UNKNOWN
