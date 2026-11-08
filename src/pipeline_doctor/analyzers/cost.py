"""Cost optimization analyzer."""

from typing import Any

from pipeline_doctor.analyzers.base import AnalyzerRegistry, BaseAnalyzer
from pipeline_doctor.core.models import (
    AnalysisResult,
    FindingCategory,
    FindingSeverity,
    PipelineRun,
)


@AnalyzerRegistry.register
class CostAnalyzer(BaseAnalyzer):
    """Analyzes pipeline costs and identifies optimization opportunities."""

    name = "cost"
    description = "Calculates pipeline costs and identifies waste"
    version = "1.0.0"

    def __init__(self, config: dict[str, Any] = None):
        super().__init__(config)
        self.currency = self.get_config("currency", "USD")
        self.compute_cost_per_minute = self.get_config("compute_cost_per_minute", 0.008)
        self.storage_cost_per_gb_month = self.get_config("storage_cost_per_gb_month", 0.10)
        self.network_cost_per_gb = self.get_config("network_cost_per_gb", 0.09)
        self.track_waste = self.get_config("track_waste", True)
        self.waste_threshold_minutes = self.get_config("waste_threshold_minutes", 10)

    async def analyze(self, run: PipelineRun) -> AnalysisResult:
        """Analyze pipeline run for cost optimization."""
        result = AnalysisResult(analyzer_name=self.name, analyzer_version=self.version)

        if not run.duration_seconds:
            return result

        # Calculate compute cost
        compute_cost = self._calculate_compute_cost(run)
        result.add_finding(self.create_finding(
            category=FindingCategory.COST,
            severity=FindingSeverity.INFO,
            title="Pipeline compute cost",
            message=f"Estimated compute cost: {compute_cost:.4f} {self.currency}",
            suggestion="Consider optimizing long-running jobs to reduce costs",
            evidence={
                "cost": compute_cost,
                "currency": self.currency,
                "duration_minutes": run.duration_seconds / 60,
                "rate_per_minute": self.compute_cost_per_minute,
            },
        ))

        # Check for waste
        if self.track_waste:
            self._check_waste(result, run)

        # Check for parallelization opportunities
        self._check_parallelization(result, run)

        # Check for caching opportunities
        self._check_caching(result, run)

        return result

    def _calculate_compute_cost(self, run: PipelineRun) -> float:
        """Calculate estimated compute cost for a run."""
        total_minutes = run.duration_seconds / 60
        return total_minutes * self.compute_cost_per_minute

    def _check_waste(self, result: AnalysisResult, run: PipelineRun) -> None:
        """Check for wasted compute resources."""
        waste_threshold_seconds = self.waste_threshold_minutes * 60

        for job in run.jobs:
            if job.status in ["cancelled", "skipped", "failure"] and job.duration_seconds:
                if job.duration_seconds >= waste_threshold_seconds:
                    waste_cost = (job.duration_seconds / 60) * self.compute_cost_per_minute
                    result.add_finding(self.create_finding(
                        category=FindingCategory.COST,
                        severity=FindingSeverity.WARNING,
                        title=f"Compute waste: {job.status} job",
                        message=f"Job '{job.name}' {job.status} after {job.duration_seconds:.0f}s (${waste_cost:.4f} waste)",
                        suggestion="Add early failure detection or improve pre-flight checks",
                        affected_job=job.name,
                        evidence={
                            "waste_cost": waste_cost,
                            "currency": self.currency,
                            "duration_seconds": job.duration_seconds,
                            "status": job.status,
                        },
                    ))

    def _check_parallelization(self, result: AnalysisResult, run: PipelineRun) -> None:
        """Check for parallelization opportunities."""
        # Find sequential jobs that could run in parallel
        # This is a simplified check - real implementation would analyze dependencies

        if len(run.jobs) <= 1:
            return

        # Check if jobs have no explicit dependencies (simplified)
        sequential_jobs = []
        for job in run.jobs:
            deps = job.metadata.get("needs", [])
            if not deps and job.duration_seconds:
                sequential_jobs.append(job)

        if len(sequential_jobs) > 2:
            total_time = sum(j.duration_seconds for j in sequential_jobs)
            max_time = max(j.duration_seconds for j in sequential_jobs)
            potential_savings = total_time - max_time
            savings_cost = (potential_savings / 60) * self.compute_cost_per_minute

            result.add_finding(self.create_finding(
                category=FindingCategory.COST,
                severity=FindingSeverity.INFO,
                title="Parallelization opportunity",
                message=f"{len(sequential_jobs)} independent jobs running sequentially (potential savings: ${savings_cost:.4f})",
                suggestion="Configure jobs to run in parallel where possible",
                evidence={
                    "sequential_jobs": [j.name for j in sequential_jobs],
                    "potential_time_savings_seconds": potential_savings,
                    "potential_cost_savings": savings_cost,
                    "currency": self.currency,
                },
            ))

    def _check_caching(self, result: AnalysisResult, run: PipelineRun) -> None:
        """Check for caching opportunities."""
        cache_keywords = ["npm install", "pip install", "yarn install", "bundle install", "go mod download", "mvn dependency:resolve"]

        for job in run.jobs:
            for step in job.steps:
                if step.logs:
                    for keyword in cache_keywords:
                        if keyword in step.logs.lower():
                            # Check if caching is mentioned
                            cache_indicators = ["cache", "cached", "restore", "save"]
                            has_cache = any(ind in step.logs.lower() for ind in cache_indicators)

                            if not has_cache and step.duration_seconds and step.duration_seconds > 60:
                                result.add_finding(self.create_finding(
                                    category=FindingCategory.COST,
                                    severity=FindingSeverity.INFO,
                                    title="Missing dependency caching",
                                    message=f"Step '{step.name}' runs '{keyword}' without apparent caching",
                                    suggestion="Add dependency caching to speed up builds and reduce costs",
                                    affected_job=job.name,
                                    affected_step=step.name,
                                    evidence={
                                        "command": keyword,
                                        "duration_seconds": step.duration_seconds,
                                    },
                                ))
                            break

    @classmethod
    def get_default_config(cls) -> dict[str, Any]:
        return {
            "enabled": True,
            "currency": "USD",
            "compute_cost_per_minute": 0.008,
            "storage_cost_per_gb_month": 0.10,
            "network_cost_per_gb": 0.09,
            "track_waste": True,
            "waste_threshold_minutes": 10,
        }
