"""Performance bottleneck analyzer."""

from typing import Any

from pipeline_doctor.analyzers.base import AnalyzerRegistry, BaseAnalyzer
from pipeline_doctor.core.models import (
    AnalysisResult,
    FindingCategory,
    FindingSeverity,
    PipelineRun,
)


@AnalyzerRegistry.register
class PerformanceAnalyzer(BaseAnalyzer):
    """Analyzes pipeline performance and identifies bottlenecks."""

    name = "performance"
    description = "Detects performance bottlenecks and slow-running jobs/steps"
    version = "1.0.0"

    def __init__(self, config: dict[str, Any] = None):
        super().__init__(config)
        self.thresholds = self.get_config("thresholds", {})
        self.compare_baseline = self.get_config("compare_baseline", True)
        self.baseline_runs = self.get_config("baseline_runs", 10)

    async def analyze(self, run: PipelineRun) -> AnalysisResult:
        """Analyze pipeline run for performance issues."""
        result = AnalysisResult(analyzer_name=self.name, analyzer_version=self.version)

        if not run.duration_seconds:
            return result

        # Analyze overall pipeline duration
        self._check_pipeline_duration(result, run)

        # Analyze individual jobs
        for job in run.jobs:
            self._check_job_duration(result, job, run)

            # Analyze individual steps
            for step in job.steps:
                self._check_step_duration(result, step, job.name)

        # Check for queue time
        self._check_queue_time(result, run)

        # Check for resource waste
        self._check_resource_waste(result, run)

        return result

    def _check_pipeline_duration(self, result: AnalysisResult, run: PipelineRun) -> None:
        """Check overall pipeline duration."""
        warn_threshold = self.thresholds.get("pipeline_duration_warn", 1800)  # 30 min
        critical_threshold = self.thresholds.get("pipeline_duration_critical", 3600)  # 1 hour

        if run.duration_seconds >= critical_threshold:
            result.add_finding(
                self.create_finding(
                    category=FindingCategory.PERFORMANCE,
                    severity=FindingSeverity.CRITICAL,
                    title="Pipeline duration critically high",
                    message=f"Pipeline took {run.duration_seconds:.0f}s (>{critical_threshold}s threshold)",
                    suggestion="Investigate parallelization opportunities and slow jobs",
                    evidence={
                        "duration_seconds": run.duration_seconds,
                        "threshold": critical_threshold,
                    },
                )
            )
        elif run.duration_seconds >= warn_threshold:
            result.add_finding(
                self.create_finding(
                    category=FindingCategory.PERFORMANCE,
                    severity=FindingSeverity.WARNING,
                    title="Pipeline duration above warning threshold",
                    message=f"Pipeline took {run.duration_seconds:.0f}s (>{warn_threshold}s threshold)",
                    suggestion="Consider optimizing slow jobs or increasing parallelism",
                    evidence={
                        "duration_seconds": run.duration_seconds,
                        "threshold": warn_threshold,
                    },
                )
            )

    def _check_job_duration(
        self, result: AnalysisResult, job: PipelineRun, run: PipelineRun
    ) -> None:
        """Check individual job duration."""
        if not job.duration_seconds:
            return

        warn_threshold = self.thresholds.get("job_duration_warn", 300)  # 5 min
        critical_threshold = self.thresholds.get("job_duration_critical", 600)  # 10 min

        # Calculate job percentage of total pipeline time
        pct_of_total = (
            (job.duration_seconds / run.duration_seconds * 100) if run.duration_seconds else 0
        )

        if job.duration_seconds >= critical_threshold:
            result.add_finding(
                self.create_finding(
                    category=FindingCategory.PERFORMANCE,
                    severity=FindingSeverity.CRITICAL,
                    title=f"Job '{job.name}' duration critically high",
                    message=f"Job took {job.duration_seconds:.0f}s (>{critical_threshold}s threshold, {pct_of_total:.1f}% of pipeline)",
                    suggestion="Split job into parallel stages or optimize slow steps",
                    affected_job=job.name,
                    evidence={
                        "duration_seconds": job.duration_seconds,
                        "threshold": critical_threshold,
                        "pct_of_pipeline": pct_of_total,
                    },
                )
            )
        elif job.duration_seconds >= warn_threshold:
            result.add_finding(
                self.create_finding(
                    category=FindingCategory.PERFORMANCE,
                    severity=FindingSeverity.WARNING,
                    title=f"Job '{job.name}' duration above warning threshold",
                    message=f"Job took {job.duration_seconds:.0f}s (>{warn_threshold}s threshold, {pct_of_total:.1f}% of pipeline)",
                    suggestion="Review job steps for optimization opportunities",
                    affected_job=job.name,
                    evidence={
                        "duration_seconds": job.duration_seconds,
                        "threshold": warn_threshold,
                        "pct_of_pipeline": pct_of_total,
                    },
                )
            )

    def _check_step_duration(
        self, result: AnalysisResult, step: PipelineRun, job_name: str
    ) -> None:
        """Check individual step duration."""
        if not step.duration_seconds:
            return

        warn_threshold = self.thresholds.get("step_duration_warn", 60)  # 1 min
        critical_threshold = self.thresholds.get("step_duration_critical", 180)  # 3 min

        if step.duration_seconds >= critical_threshold:
            result.add_finding(
                self.create_finding(
                    category=FindingCategory.PERFORMANCE,
                    severity=FindingSeverity.CRITICAL,
                    title=f"Step '{step.name}' duration critically high",
                    message=f"Step took {step.duration_seconds:.0f}s (>{critical_threshold}s threshold)",
                    suggestion="Optimize step logic or split into smaller steps",
                    affected_job=job_name,
                    affected_step=step.name,
                    evidence={
                        "duration_seconds": step.duration_seconds,
                        "threshold": critical_threshold,
                    },
                )
            )
        elif step.duration_seconds >= warn_threshold:
            result.add_finding(
                self.create_finding(
                    category=FindingCategory.PERFORMANCE,
                    severity=FindingSeverity.WARNING,
                    title=f"Step '{step.name}' duration above warning threshold",
                    message=f"Step took {step.duration_seconds:.0f}s (>{warn_threshold}s threshold)",
                    suggestion="Review step for optimization",
                    affected_job=job_name,
                    affected_step=step.name,
                    evidence={
                        "duration_seconds": step.duration_seconds,
                        "threshold": warn_threshold,
                    },
                )
            )

    def _check_queue_time(self, result: AnalysisResult, run: PipelineRun) -> None:
        """Check for excessive queue/wait time."""
        if not run.started_at or not run.jobs:
            return

        # Check first job start time vs pipeline start
        first_job = min(run.jobs, key=lambda j: j.started_at or run.started_at)
        if first_job.started_at:
            queue_time = (first_job.started_at - run.started_at).total_seconds()

            warn_threshold = self.thresholds.get("queue_time_warn", 120)  # 2 min
            critical_threshold = self.thresholds.get("queue_time_critical", 300)  # 5 min

            if queue_time >= critical_threshold:
                result.add_finding(
                    self.create_finding(
                        category=FindingCategory.PERFORMANCE,
                        severity=FindingSeverity.CRITICAL,
                        title="Excessive queue time before first job",
                        message=f"First job started after {queue_time:.0f}s in queue",
                        suggestion="Check runner availability and queue configuration",
                        evidence={
                            "queue_time_seconds": queue_time,
                            "threshold": critical_threshold,
                        },
                    )
                )
            elif queue_time >= warn_threshold:
                result.add_finding(
                    self.create_finding(
                        category=FindingCategory.PERFORMANCE,
                        severity=FindingSeverity.WARNING,
                        title="Queue time above warning threshold",
                        message=f"First job started after {queue_time:.0f}s in queue",
                        suggestion="Consider adding more runners or optimizing scheduling",
                        evidence={"queue_time_seconds": queue_time, "threshold": warn_threshold},
                    )
                )

    def _check_resource_waste(self, result: AnalysisResult, run: PipelineRun) -> None:
        """Check for resource waste (cancelled/skipped jobs that ran long)."""
        waste_threshold = self.thresholds.get("waste_threshold_minutes", 10) * 60

        for job in run.jobs:
            if job.status in ["cancelled", "skipped"] and job.duration_seconds:
                if job.duration_seconds >= waste_threshold:
                    result.add_finding(
                        self.create_finding(
                            category=FindingCategory.COST,
                            severity=FindingSeverity.WARNING,
                            title=f"Resource waste: {job.status} job ran for {job.duration_seconds:.0f}s",
                            message=f"Job '{job.name}' was {job.status} after consuming resources",
                            suggestion="Add early exit conditions or improve failure detection",
                            affected_job=job.name,
                            evidence={
                                "duration_seconds": job.duration_seconds,
                                "status": job.status,
                                "waste_threshold": waste_threshold,
                            },
                        )
                    )

    @classmethod
    def get_default_config(cls) -> dict[str, Any]:
        return {
            "enabled": True,
            "thresholds": {
                "pipeline_duration_warn": 1800,
                "pipeline_duration_critical": 3600,
                "job_duration_warn": 300,
                "job_duration_critical": 600,
                "step_duration_warn": 60,
                "step_duration_critical": 180,
                "queue_time_warn": 120,
                "queue_time_critical": 300,
                "waste_threshold_minutes": 10,
            },
            "compare_baseline": True,
            "baseline_runs": 10,
        }
