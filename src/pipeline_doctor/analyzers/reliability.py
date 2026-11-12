"""Reliability analyzer."""

from collections import defaultdict
from typing import Any

from pipeline_doctor.analyzers.base import AnalyzerRegistry, BaseAnalyzer
from pipeline_doctor.core.models import (
    AnalysisResult,
    FindingCategory,
    FindingSeverity,
    PipelineRun,
    PipelineStatus,
)


@AnalyzerRegistry.register
class ReliabilityAnalyzer(BaseAnalyzer):
    """Analyzes pipeline reliability and flakiness."""

    name = "reliability"
    description = "Detects flaky tests, unreliable jobs, and stability issues"
    version = "1.0.0"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.flaky_threshold = self.get_config("flaky_threshold", 0.1)
        self.min_runs_for_flaky = self.get_config("min_runs_for_flaky", 10)
        self.check_retries = self.get_config("check_retries", True)
        self.check_timeouts = self.get_config("check_timeouts", True)

    async def analyze(self, run: PipelineRun) -> AnalysisResult:
        """Analyze pipeline run for reliability issues."""
        result = AnalysisResult(analyzer_name=self.name, analyzer_version=self.version)

        # Check current run for retries
        if self.check_retries:
            self._check_retries(result, run)

        # Check for timeouts
        if self.check_timeouts:
            self._check_timeouts(result, run)

        # Note: Flakiness detection requires historical data
        # This would be implemented in a separate historical analyzer
        # that has access to multiple runs

        return result

    def _check_retries(self, result: AnalysisResult, run: PipelineRun) -> None:
        """Check for job/step retries."""
        for job in run.jobs:
            retry_count = job.metadata.get("retry_count", 0)
            if retry_count > 0:
                severity = FindingSeverity.WARNING if retry_count == 1 else FindingSeverity.ERROR
                result.add_finding(
                    self.create_finding(
                        category=FindingCategory.RELIABILITY,
                        severity=severity,
                        title=f"Job retried {retry_count} time(s)",
                        message=f"Job '{job.name}' was retried {retry_count} time(s)",
                        suggestion="Investigate root cause of intermittent failures",
                        affected_job=job.name,
                        evidence={"retry_count": retry_count},
                    )
                )

            # Check steps for retries
            for step in job.steps:
                step_retry = step.metadata.get("retry_count", 0)
                if step_retry > 0:
                    severity = FindingSeverity.WARNING if step_retry == 1 else FindingSeverity.ERROR
                    result.add_finding(
                        self.create_finding(
                            category=FindingCategory.RELIABILITY,
                            severity=severity,
                            title=f"Step retried {step_retry} time(s)",
                            message=f"Step '{step.name}' in job '{job.name}' was retried {step_retry} time(s)",
                            suggestion="Investigate root cause of intermittent step failures",
                            affected_job=job.name,
                            affected_step=step.name,
                            evidence={"retry_count": step_retry},
                        )
                    )

    def _check_timeouts(self, result: AnalysisResult, run: PipelineRun) -> None:
        """Check for timeout-related failures."""
        for job in run.jobs:
            if job.status == PipelineStatus.TIMEOUT:
                result.add_finding(
                    self.create_finding(
                        category=FindingCategory.RELIABILITY,
                        severity=FindingSeverity.ERROR,
                        title="Job timed out",
                        message=f"Job '{job.name}' exceeded timeout limit",
                        suggestion="Increase timeout or optimize job execution time",
                        affected_job=job.name,
                        evidence={"timeout": True, "duration_seconds": job.duration_seconds},
                    )
                )

            for step in job.steps:
                if step.status == PipelineStatus.TIMEOUT:
                    result.add_finding(
                        self.create_finding(
                            category=FindingCategory.RELIABILITY,
                            severity=FindingSeverity.ERROR,
                            title="Step timed out",
                            message=f"Step '{step.name}' in job '{job.name}' exceeded timeout limit",
                            suggestion="Increase timeout or optimize step execution time",
                            affected_job=job.name,
                            affected_step=step.name,
                            evidence={"timeout": True, "duration_seconds": step.duration_seconds},
                        )
                    )

    def analyze_historical(self, runs: list[PipelineRun]) -> AnalysisResult:
        """Analyze multiple runs for flakiness patterns (requires historical data)."""
        result = AnalysisResult(analyzer_name=self.name, analyzer_version=self.version)

        if len(runs) < self.min_runs_for_flaky:
            return result

        # Group by job name
        job_runs = defaultdict(list)
        for run in runs:
            for job in run.jobs:
                job_runs[job.name].append(job)

        # Analyze each job for flakiness
        for job_name, jobs in job_runs.items():
            if len(jobs) < self.min_runs_for_flaky:
                continue

            # Calculate failure rate
            total = len(jobs)
            failures = sum(1 for j in jobs if j.status == PipelineStatus.FAILURE)
            failure_rate = failures / total

            # Check for flakiness (intermittent failures)
            if failure_rate > 0 and failure_rate < self.flaky_threshold:
                # Check if failures are intermittent (not all consecutive)
                statuses = [j.status for j in jobs]
                failure_indices = [i for i, s in enumerate(statuses) if s == PipelineStatus.FAILURE]

                # Check if failures are scattered (not all at the end)
                if len(failure_indices) > 1:
                    gaps = [
                        failure_indices[i + 1] - failure_indices[i]
                        for i in range(len(failure_indices) - 1)
                    ]
                    if any(g > 1 for g in gaps):  # Non-consecutive failures
                        result.add_finding(
                            self.create_finding(
                                category=FindingCategory.RELIABILITY,
                                severity=FindingSeverity.WARNING,
                                title=f"Flaky job detected: {job_name}",
                                message=f"Job '{job_name}' has {failure_rate * 100:.1f}% failure rate over {total} runs (intermittent)",
                                suggestion="Investigate and fix flaky job - check for race conditions, timing issues, or external dependencies",
                                affected_job=job_name,
                                evidence={
                                    "failure_rate": failure_rate,
                                    "total_runs": total,
                                    "failure_count": failures,
                                    "flaky_threshold": self.flaky_threshold,
                                },
                            )
                        )

        return result

    @classmethod
    def get_default_config(cls) -> dict[str, Any]:
        return {
            "enabled": True,
            "flaky_threshold": 0.1,
            "min_runs_for_flaky": 10,
            "check_retries": True,
            "check_timeouts": True,
        }
