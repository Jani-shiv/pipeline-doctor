"""GitHub Actions integration."""

from datetime import datetime
from typing import Any
from uuid import uuid4

import httpx

from pipeline_doctor.core.exceptions import (
    AuthenticationError,
)
from pipeline_doctor.core.models import (
    Pipeline,
    PipelineJob,
    PipelinePlatform,
    PipelineRun,
    PipelineStatus,
    PipelineStep,
)
from pipeline_doctor.core.utils import retry_with_backoff
from pipeline_doctor.integrations.base import BaseIntegration, IntegrationRegistry


@IntegrationRegistry.register
class GitHubIntegration(BaseIntegration):
    """GitHub Actions API integration."""

    platform = PipelinePlatform.GITHUB

    def __init__(self, config: dict[str, Any] = None):
        super().__init__(config)
        self.api_url = self.config.get("api_url", "https://api.github.com")
        self.owner = self.config.get("owner")
        self.repo = self.config.get("repo")

    async def connect(self) -> None:
        """Establish connection to GitHub API."""
        if not self.token:
            raise AuthenticationError("GitHub token is required", platform=self.platform.value)

        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=self.timeout,
            verify=self.verify_ssl,
        )

    async def disconnect(self) -> None:
        """Close connection."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_repo_path(self) -> str:
        """Get repository path for API calls."""
        if not self.owner or not self.repo:
            raise ValueError("Owner and repo must be configured")
        return f"repos/{self.owner}/{self.repo}"

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_pipeline(self, pipeline_id: str) -> Pipeline:
        """Get workflow by ID."""
        repo_path = self._get_repo_path()
        data = await self._make_request(
            "GET",
            f"{repo_path}/actions/workflows/{pipeline_id}",
        )

        return Pipeline(
            id=uuid4(),
            name=data["name"],
            platform=PipelinePlatform.GITHUB,
            repository=f"{self.owner}/{self.repo}",
            platform_id=str(data["id"]),
            path=data["path"],
            metadata={"github_data": data},
        )

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_pipeline_runs(
        self,
        pipeline_id: str,
        limit: int = 100,
        offset: int = 0,
        status: PipelineStatus | None = None,
    ) -> list[PipelineRun]:
        """Get workflow runs."""
        repo_path = self._get_repo_path()
        params = {"per_page": min(limit, 100), "page": (offset // 100) + 1}
        if status:
            params["status"] = self._status_to_github(status)

        data = await self._make_request(
            "GET",
            f"{repo_path}/actions/workflows/{pipeline_id}/runs",
            params=params,
        )

        runs = []
        for run_data in data.get("workflow_runs", [])[:limit]:
            runs.append(self._parse_run(run_data))
        return runs

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_run(self, pipeline_id: str, run_id: str) -> PipelineRun:
        """Get specific workflow run."""
        repo_path = self._get_repo_path()
        data = await self._make_request(
            "GET",
            f"{repo_path}/actions/runs/{run_id}",
        )
        return self._parse_run(data, pipeline_id=pipeline_id)

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def get_run_logs(
        self, pipeline_id: str, run_id: str, job_id: str = None
    ) -> dict[str, Any]:
        """Get logs for a run or job."""
        repo_path = self._get_repo_path()

        if job_id:
            # Get job logs
            response = await self._client.get(
                f"{self.api_url}/{repo_path}/actions/jobs/{job_id}/logs",
                headers={"Accept": "text/plain"},
            )
            response.raise_for_status()
            return {"logs": response.text}
        else:
            # Get all jobs for the run
            data = await self._make_request(
                "GET",
                f"{repo_path}/actions/runs/{run_id}/jobs",
            )
            return {"jobs": data.get("jobs", [])}

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def trigger_pipeline(
        self, pipeline_id: str, params: dict[str, Any] = None
    ) -> PipelineRun:
        """Trigger a new workflow run."""
        repo_path = self._get_repo_path()
        await self._make_request(
            "POST",
            f"{repo_path}/actions/workflows/{pipeline_id}/dispatches",
            json={
                "ref": params.get("ref", "main") if params else "main",
                "inputs": params.get("inputs", {}) if params else {},
            },
        )
        # GitHub returns 204 on success, need to poll for the run
        # For now, return a placeholder
        return PipelineRun(
            id=uuid4(),
            pipeline_id=uuid4(),
            number=0,
            status=PipelineStatus.PENDING,
            metadata={"triggered": True},
        )

    @retry_with_backoff(max_attempts=3, exceptions=(httpx.RequestError,))
    async def cancel_run(self, pipeline_id: str, run_id: str) -> bool:
        """Cancel a workflow run."""
        repo_path = self._get_repo_path()
        await self._make_request(
            "POST",
            f"{repo_path}/actions/runs/{run_id}/cancel",
        )
        return True

    def _status_to_github(self, status: PipelineStatus) -> str:
        """Convert PipelineStatus to GitHub status."""
        mapping = {
            PipelineStatus.SUCCESS: "completed",
            PipelineStatus.FAILURE: "completed",
            PipelineStatus.CANCELLED: "cancelled",
            PipelineStatus.RUNNING: "in_progress",
            PipelineStatus.PENDING: "queued",
        }
        return mapping.get(status, "completed")

    def _parse_run(self, data: dict[str, Any], pipeline_id: str = None) -> PipelineRun:
        """Parse GitHub workflow run data."""
        run_id = uuid4()

        # Parse timestamps
        started_at = None
        completed_at = None
        if data.get("run_started_at"):
            started_at = datetime.fromisoformat(data["run_started_at"].replace("Z", "+00:00"))
        if data.get("updated_at"):
            completed_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))

        run = PipelineRun(
            id=run_id,
            pipeline_id=uuid4() if not pipeline_id else uuid4(),
            number=data.get("run_number", 0),
            status=self._parse_github_status(data.get("conclusion"), data.get("status")),
            trigger=data.get("event", "manual"),
            branch=data.get("head_branch"),
            commit_sha=data.get("head_sha"),
            commit_message=data.get("head_commit", {}).get("message"),
            author=data.get("actor", {}).get("login"),
            started_at=started_at,
            completed_at=completed_at,
            url=data.get("html_url"),
            metadata={"github_data": data},
        )

        # Fetch jobs for this run
        # Note: In practice, you'd want to fetch jobs separately
        # This is a simplified version
        return run

    def _parse_github_status(self, conclusion: str, status: str) -> PipelineStatus:
        """Parse GitHub conclusion and status to PipelineStatus."""
        if conclusion:
            conclusion_lower = conclusion.lower()
            if conclusion_lower == "success":
                return PipelineStatus.SUCCESS
            elif conclusion_lower == "failure":
                return PipelineStatus.FAILURE
            elif conclusion_lower == "cancelled":
                return PipelineStatus.CANCELLED
            elif conclusion_lower == "skipped":
                return PipelineStatus.SKIPPED
            elif conclusion_lower == "timed_out":
                return PipelineStatus.TIMEOUT

        if status:
            status_lower = status.lower()
            if status_lower in ("in_progress", "queued", "requested", "waiting"):
                return PipelineStatus.RUNNING

        return PipelineStatus.UNKNOWN

    async def get_jobs_for_run(self, run_id: str) -> list[PipelineJob]:
        """Get jobs for a specific run."""
        repo_path = self._get_repo_path()
        data = await self._make_request(
            "GET",
            f"{repo_path}/actions/runs/{run_id}/jobs",
        )

        jobs = []
        for job_data in data.get("jobs", []):
            jobs.append(self._parse_job(job_data))
        return jobs

    def _parse_job(self, data: dict[str, Any]) -> PipelineJob:
        """Parse GitHub job data."""
        job_id = uuid4()

        started_at = None
        completed_at = None
        if data.get("started_at"):
            started_at = datetime.fromisoformat(data["started_at"].replace("Z", "+00:00"))
        if data.get("completed_at"):
            completed_at = datetime.fromisoformat(data["completed_at"].replace("Z", "+00:00"))

        steps = []
        for step_data in data.get("steps", []):
            steps.append(self._parse_step(step_data))

        return PipelineJob(
            id=job_id,
            name=data.get("name", "unknown"),
            status=self._parse_github_status(data.get("conclusion"), data.get("status")),
            started_at=started_at,
            completed_at=completed_at,
            runner=data.get("runner_name"),
            runner_labels=data.get("runner_labels", []),
            steps=steps,
            metadata={"github_data": data},
        )

    def _parse_step(self, data: dict[str, Any]) -> PipelineStep:
        """Parse GitHub step data."""
        step_id = uuid4()

        started_at = None
        completed_at = None
        if data.get("started_at"):
            started_at = datetime.fromisoformat(data["started_at"].replace("Z", "+00:00"))
        if data.get("completed_at"):
            completed_at = datetime.fromisoformat(data["completed_at"].replace("Z", "+00:00"))

        return PipelineStep(
            id=step_id,
            name=data.get("name", "unknown"),
            status=self._parse_github_status(data.get("conclusion"), data.get("status")),
            started_at=started_at,
            completed_at=completed_at,
            metadata={"github_data": data},
        )
