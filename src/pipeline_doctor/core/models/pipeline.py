"""Pipeline domain models."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class PipelinePlatform(StrEnum):
    """Supported CI/CD platforms."""

    GITHUB = "github"
    GITLAB = "gitlab"
    JENKINS = "jenkins"
    AZURE_DEVOPS = "azure_devops"
    CIRCLECI = "circleci"
    BITBUCKET = "bitbucket"
    TRAVIS = "travis"
    LOCAL = "local"


class PipelineStatus(StrEnum):
    """Pipeline execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class PipelineStep(BaseModel):
    """Individual step within a job."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    status: PipelineStatus = PipelineStatus.UNKNOWN
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    logs: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_completed(self) -> bool:
        return self.status in {
            PipelineStatus.SUCCESS,
            PipelineStatus.FAILURE,
            PipelineStatus.CANCELLED,
            PipelineStatus.SKIPPED,
            PipelineStatus.TIMEOUT,
        }

    @property
    def computed_duration(self) -> float | None:
        """Compute duration from timestamps if not explicitly set."""
        if self.duration_seconds is not None:
            return self.duration_seconds
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @field_validator("duration_seconds", mode="before")
    @classmethod
    def compute_duration(cls, v: Any) -> float | None:
        if v is None:
            return None
        return float(v)


class PipelineJob(BaseModel):
    """Job within a pipeline run."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    status: PipelineStatus = PipelineStatus.UNKNOWN
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    steps: list[PipelineStep] = Field(default_factory=list)
    runner: str | None = None
    runner_labels: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_completed(self) -> bool:
        return self.status in {
            PipelineStatus.SUCCESS,
            PipelineStatus.FAILURE,
            PipelineStatus.CANCELLED,
            PipelineStatus.SKIPPED,
            PipelineStatus.TIMEOUT,
        }

    @property
    def failed_steps(self) -> list[PipelineStep]:
        return [s for s in self.steps if s.status == PipelineStatus.FAILURE]

    @property
    def computed_duration(self) -> float | None:
        """Compute duration from timestamps if not explicitly set."""
        if self.duration_seconds is not None:
            return self.duration_seconds
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @field_validator("duration_seconds", mode="before")
    @classmethod
    def compute_duration(cls, v: Any) -> float | None:
        if v is None:
            return None
        return float(v)


class PipelineRun(BaseModel):
    """A single pipeline execution."""

    id: UUID = Field(default_factory=uuid4)
    pipeline_id: UUID
    number: int
    status: PipelineStatus = PipelineStatus.UNKNOWN
    trigger: str = "manual"
    branch: str | None = None
    commit_sha: str | None = None
    commit_message: str | None = None
    author: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    jobs: list[PipelineJob] = Field(default_factory=list)
    url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_completed(self) -> bool:
        return self.status in {
            PipelineStatus.SUCCESS,
            PipelineStatus.FAILURE,
            PipelineStatus.CANCELLED,
            PipelineStatus.SKIPPED,
            PipelineStatus.TIMEOUT,
        }

    @property
    def failed_jobs(self) -> list[PipelineJob]:
        return [j for j in self.jobs if j.status == PipelineStatus.FAILURE]

    @property
    def total_steps(self) -> int:
        return sum(len(j.steps) for j in self.jobs)

    @property
    def failed_steps(self) -> list[PipelineStep]:
        steps = []
        for job in self.jobs:
            steps.extend(job.failed_steps)
        return steps

    @property
    def computed_duration(self) -> float | None:
        """Compute duration from timestamps if not explicitly set."""
        if self.duration_seconds is not None:
            return self.duration_seconds
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @field_validator("duration_seconds", mode="before")
    @classmethod
    def compute_duration(cls, v: Any) -> float | None:
        if v is None:
            return None
        return float(v)


class Pipeline(BaseModel):
    """CI/CD Pipeline definition."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    platform: PipelinePlatform
    repository: str
    platform_id: str | None = None  # Platform-specific ID
    path: str | None = None  # Path to pipeline config file
    branch: str = "main"
    description: str | None = None
    runs: list[PipelineRun] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def latest_run(self) -> PipelineRun | None:
        if not self.runs:
            return None
        return max(self.runs, key=lambda r: r.number)

    @property
    def success_rate(self) -> float:
        if not self.runs:
            return 0.0
        completed = [r for r in self.runs if r.is_completed]
        if not completed:
            return 0.0
        successful = [r for r in completed if r.status == PipelineStatus.SUCCESS]
        return len(successful) / len(completed)

    @property
    def average_duration(self) -> float | None:
        completed = [r for r in self.runs if r.is_completed and r.duration_seconds is not None]
        if not completed:
            return None
        return sum(r.duration_seconds for r in completed if r.duration_seconds is not None) / len(
            completed
        )
