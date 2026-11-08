"""GitLab CI integration."""

from datetime import datetime
from typing import Any
from uuid import uuid4

import httpx

from pipeline_doctor.core.exceptions import AuthenticationError
from pipeline_doctor.core.models import (
    Pipeline,
    PipelineJob,
    PipelinePlatform,
    PipelineRun,
    PipelineStatus,
)
from pipeline_doctor.core.utils import retry_with_backoff
from pipeline_doctor.integrations.base import BaseIntegration, IntegrationRegistry


@IntegrationRegistry.register
class GitLabIntegration(BaseIntegration):
    """GitLab CI API integration."""

    platform = PipelinePlatform.GITLAB

    def __init__(self, config: dict[str, Any] = None):
        super().__init__(config)
        self.api_url = self.config.get("api_url", "https://gitlab.com/api/v4")
        self.project_id = self.config.get("project_id")

    async def connect(self) -> None:
        """Establish connection to GitLab API."""
        if not self.token:
            raise AuthenticationError("GitLab token is required", platform=self.platform.value)

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

    def _get_project_path(self) -> str:
        """Get project path for API calls."""
        if not self.project_id:
            raise ValueError("Project ID must be configured")
        return f"projects/{self.project_id}"

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_pipeline(self, pipeline_id: str) -> Pipeline:
        """Get pipeline by ID (GitLab uses project-level pipelines)."""
        project_path = self._get_project_path()
        data = await self._make_request(
            "GET",
            f"{project_path}/pipelines/{pipeline_id}",
        )

        return Pipeline(
            id=uuid4(),
            name=f"Pipeline #{data['id']}",
            platform=PipelinePlatform.GITLAB,
            repository=self.config.get("project_path", ""),
            platform_id=str(data["id"]),
            branch=data.get("ref"),
            metadata={"gitlab_data": data},
        )

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_pipeline_runs(
        self,
        pipeline_id: str,
        limit: int = 100,
        offset: int = 0,
        status: PipelineStatus | None = None,
    ) -> list[PipelineRun]:
        """Get pipeline runs (in GitLab, these are pipelines for a project)."""
        project_path = self._get_project_path()
        params = {"per_page": min(limit, 100), "page": (offset // 100) + 1}
        if status:
            params["status"] = self._status_to_gitlab(status)

        data = await self._make_request(
            "GET",
            f"{project_path}/pipelines",
            params=params,
        )

        runs = []
        for run_data in data[:limit]:
            runs.append(self._parse_run(run_data))
        return runs

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_run(self, pipeline_id: str, run_id: str) -> PipelineRun:
        """Get specific pipeline."""
        project_path = self._get_project_path()
        data = await self._make_request(
            "GET",
            f"{project_path}/pipelines/{run_id}",
        )
        return self._parse_run(data)

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_run_logs(
        self, pipeline_id: str, run_id: str, job_id: str = None
    ) -> dict[str, Any]:
        """Get logs for a pipeline or job."""
        project_path = self._get_project_path()

        if job_id:
            # Get job trace/logs
            response = await self._client.get(
                f"{self.api_url}/{project_path}/jobs/{job_id}/trace",
            )
            response.raise_for_status()
            return {"logs": response.text}
        else:
            # Get all jobs for the pipeline
            data = await self._make_request(
                "GET",
                f"{project_path}/pipelines/{run_id}/jobs",
            )
            return {"jobs": data}

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def trigger_pipeline(
        self, pipeline_id: str, params: dict[str, Any] = None
    ) -> PipelineRun:
        """Trigger a new pipeline."""
        project_path = self._get_project_path()
        data = await self._make_request(
            "POST",
            f"{project_path}/pipeline",
            json={
                "ref": params.get("ref", "main") if params else "main",
                "variables": params.get("variables", []) if params else [],
            },
        )
        return self._parse_run(data)

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def cancel_run(self, pipeline_id: str, run_id: str) -> bool:
        """Cancel a pipeline."""
        project_path = self._get_project_path()
        await self._make_request(
            "POST",
            f"{project_path}/pipelines/{run_id}/cancel",
        )
        return True

    def _status_to_gitlab(self, status: PipelineStatus) -> str:
        """Convert PipelineStatus to GitLab status."""
        mapping = {
            PipelineStatus.SUCCESS: "success",
            PipelineStatus.FAILURE: "failed",
            PipelineStatus.CANCELLED: "canceled",
            PipelineStatus.RUNNING: "running",
            PipelineStatus.PENDING: "pending",
            PipelineStatus.SKIPPED: "skipped",
        }
        return mapping.get(status, "success")

    def _parse_run(self, data: dict[str, Any]) -> PipelineRun:
        """Parse GitLab pipeline data."""
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
            number=data.get("id", 0),
            status=self._parse_gitlab_status(data.get("status")),
            trigger=data.get("source", "push"),
            branch=data.get("ref"),
            commit_sha=data.get("sha"),
            commit_message=data.get("commit", {}).get("title") if data.get("commit") else None,
            author=data.get("user", {}).get("username") if data.get("user") else None,
            started_at=started_at,
            completed_at=completed_at,
            url=data.get("web_url"),
            metadata={"gitlab_data": data},
        )

    def _parse_gitlab_status(self, status: str) -> PipelineStatus:
        """Parse GitLab status to PipelineStatus."""
        if not status:
            return PipelineStatus.UNKNOWN

        status_lower = status.lower()
        if status_lower == "success":
            return PipelineStatus.SUCCESS
        elif status_lower in ("failed", "failure"):
            return PipelineStatus.FAILURE
        elif status_lower == "canceled":
            return PipelineStatus.CANCELLED
        elif status_lower == "skipped":
            return PipelineStatus.SKIPPED
        elif status_lower in ("running", "pending", "created", "preparing", "waiting_for_resource"):
            return PipelineStatus.RUNNING
        elif status_lower == "manual":
            return PipelineStatus.PENDING
        return PipelineStatus.UNKNOWN

    async def get_jobs_for_run(self, run_id: str) -> list[PipelineJob]:
        """Get jobs for a specific pipeline."""
        project_path = self._get_project_path()
        data = await self._make_request(
            "GET",
            f"{project_path}/pipelines/{run_id}/jobs",
        )

        jobs = []
        for job_data in data:
            jobs.append(self._parse_job(job_data))
        return jobs

    def _parse_job(self, data: dict[str, Any]) -> PipelineJob:
        """Parse GitLab job data."""
        job_id = uuid4()

        started_at = None
        completed_at = None
        if data.get("started_at"):
            started_at = datetime.fromisoformat(data["started_at"].replace("Z", "+00:00"))
        if data.get("finished_at"):
            completed_at = datetime.fromisoformat(data["finished_at"].replace("Z", "+00:00"))

        # GitLab doesn't provide steps in job API by default
        # Would need separate API call for job trace
        steps = []

        return PipelineJob(
            id=job_id,
            name=data.get("name", "unknown"),
            status=self._parse_gitlab_status(data.get("status")),
            started_at=started_at,
            completed_at=completed_at,
            runner=data.get("runner", {}).get("description") if data.get("runner") else None,
            runner_labels=[data.get("tag_list", [])] if data.get("tag_list") else [],
            steps=steps,
            metadata={"gitlab_data": data},
        )
