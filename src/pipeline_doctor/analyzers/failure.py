"""Failure pattern analyzer."""

import re
from typing import Any

from pipeline_doctor.analyzers.base import AnalyzerRegistry, BaseAnalyzer
from pipeline_doctor.core.models import (
    AnalysisResult,
    FindingCategory,
    FindingSeverity,
    PipelineRun,
)


@AnalyzerRegistry.register
class FailureAnalyzer(BaseAnalyzer):
    """Analyzes pipeline failures for common patterns."""

    name = "failure"
    description = "Detects common failure patterns in pipeline runs"
    version = "1.0.0"

    # Common failure patterns with regex
    FAILURE_PATTERNS = {
        "timeout": {
            "patterns": [
                r"timeout",
                r"timed out",
                r"exceeded.*time limit",
                r"execution.*timeout",
            ],
            "severity": FindingSeverity.ERROR,
            "suggestion": "Increase timeout limits or optimize long-running steps",
            "category": FindingCategory.FAILURE_PATTERN,
        },
        "out_of_memory": {
            "patterns": [
                r"out of memory",
                r"OOM",
                r"memory limit exceeded",
                r"cannot allocate memory",
                r"Java heap space",
                r"GC overhead limit exceeded",
            ],
            "severity": FindingSeverity.ERROR,
            "suggestion": "Increase memory limits or optimize memory usage",
            "category": FindingCategory.RESOURCE,
        },
        "permission_denied": {
            "patterns": [
                r"permission denied",
                r"access denied",
                r"unauthorized",
                r"forbidden",
                r"403",
                r"insufficient permissions",
            ],
            "severity": FindingSeverity.ERROR,
            "suggestion": "Check service account permissions and credentials",
            "category": FindingCategory.CONFIGURATION,
        },
        "connection_refused": {
            "patterns": [
                r"connection refused",
                r"connect.*failed",
                r"network unreachable",
                r"host unreachable",
                r"ECONNREFUSED",
            ],
            "severity": FindingSeverity.ERROR,
            "suggestion": "Verify network connectivity and service availability",
            "category": FindingCategory.CONFIGURATION,
        },
        "disk_full": {
            "patterns": [
                r"no space left on device",
                r"disk full",
                r"disk quota exceeded",
                r"ENOSPC",
            ],
            "severity": FindingSeverity.CRITICAL,
            "suggestion": "Clean up disk space or increase storage allocation",
            "category": FindingCategory.RESOURCE,
        },
        "dependency_failure": {
            "patterns": [
                r"dependency.*failed",
                r"package.*not found",
                r"module.*not found",
                r"import.*error",
                r"cannot find module",
                r"npm ERR!",
                r"pip.*error",
            ],
            "severity": FindingSeverity.ERROR,
            "suggestion": "Check dependency versions and lock files",
            "category": FindingCategory.DEPENDENCY,
        },
        "test_failure": {
            "patterns": [
                r"test.*failed",
                r"assertion.*failed",
                r"FAILED.*test",
                r"pytest.*failed",
                r"jest.*failed",
                r"mocha.*failed",
            ],
            "severity": FindingSeverity.ERROR,
            "suggestion": "Review test output for specific failures",
            "category": FindingCategory.FAILURE_PATTERN,
        },
        "build_failure": {
            "patterns": [
                r"build.*failed",
                r"compilation.*failed",
                r"error:.*compilation",
                r"BUILD FAILED",
                r"gradle.*failed",
                r"maven.*failed",
            ],
            "severity": FindingSeverity.ERROR,
            "suggestion": "Check build logs for compilation errors",
            "category": FindingCategory.FAILURE_PATTERN,
        },
        "container_failure": {
            "patterns": [
                r"container.*exited",
                r"docker.*failed",
                r"image.*not found",
                r"pull.*failed",
                r"CrashLoopBackOff",
                r"ImagePullBackOff",
            ],
            "severity": FindingSeverity.ERROR,
            "suggestion": "Check container logs and image availability",
            "category": FindingCategory.CONFIGURATION,
        },
        "kubernetes_failure": {
            "patterns": [
                r"pod.*failed",
                r"deployment.*failed",
                r"replica.*set.*failed",
                r"kubectl.*error",
            ],
            "severity": FindingSeverity.ERROR,
            "suggestion": "Check Kubernetes events and pod logs",
            "category": FindingCategory.CONFIGURATION,
        },
        "segmentation_fault": {
            "patterns": [
                r"segmentation fault",
                r"segfault",
                r"SIGSEGV",
                r"exit code 139",
            ],
            "severity": FindingSeverity.CRITICAL,
            "suggestion": "Investigate native code crashes or memory corruption",
            "category": FindingCategory.FAILURE_PATTERN,
        },
        "killed_process": {
            "patterns": [
                r"killed",
                r"SIGKILL",
                r"exit code 137",
                r"OOMKilled",
            ],
            "severity": FindingSeverity.ERROR,
            "suggestion": "Process was killed, likely due to memory limits",
            "category": FindingCategory.RESOURCE,
        },
    }

    def __init__(self, config: dict[str, Any] = None):
        super().__init__(config)
        self.custom_patterns = self.get_config("custom_patterns", [])
        self.patterns = self._compile_patterns()

    def _compile_patterns(self) -> dict[str, dict]:
        """Compile all patterns including custom ones."""
        patterns = {}

        # Built-in patterns
        for key, config in self.FAILURE_PATTERNS.items():
            compiled = [re.compile(p, re.IGNORECASE) for p in config["patterns"]]
            patterns[key] = {**config, "compiled": compiled}

        # Custom patterns
        for i, custom in enumerate(self.custom_patterns):
            if isinstance(custom, dict) and "pattern" in custom:
                key = f"custom_{i}"
                compiled = [re.compile(custom["pattern"], re.IGNORECASE)]
                patterns[key] = {
                    "compiled": compiled,
                    "severity": custom.get("severity", FindingSeverity.WARNING),
                    "suggestion": custom.get("suggestion", "Review custom pattern match"),
                    "category": custom.get("category", FindingCategory.CUSTOM),
                }

        return patterns

    async def analyze(self, run: PipelineRun) -> AnalysisResult:
        """Analyze pipeline run for failure patterns."""
        result = AnalysisResult(analyzer_name=self.name, analyzer_version=self.version)

        for job in run.jobs:
            if job.status not in (FindingSeverity.ERROR.value, "failure"):
                continue

            # Check job-level logs
            job_logs = self._get_job_logs(job)
            self._check_patterns(result, job_logs, job.name, None)

            # Check step-level logs
            for step in job.steps:
                if step.status != "failure":
                    continue
                step_logs = step.logs or ""
                self._check_patterns(result, step_logs, job.name, step.name)

        return result

    def _get_job_logs(self, job: PipelineRun) -> str:
        """Aggregate logs from all steps in a job."""
        logs = []
        for step in job.steps:
            if step.logs:
                logs.append(f"=== Step: {step.name} ===\n{step.logs}")
        return "\n\n".join(logs)

    def _check_patterns(
        self,
        result: AnalysisResult,
        logs: str,
        job_name: str,
        step_name: str | None,
    ) -> None:
        """Check logs against all failure patterns."""
        if not logs:
            return

        for pattern_name, pattern_config in self.patterns.items():
            for compiled in pattern_config["compiled"]:
                matches = list(compiled.finditer(logs))
                if matches:
                    # Get context around first match
                    match = matches[0]
                    start = max(0, match.start() - 100)
                    end = min(len(logs), match.end() + 100)
                    context = logs[start:end]

                    finding = self.create_finding(
                        category=pattern_config["category"],
                        severity=pattern_config["severity"],
                        title=f"Failure pattern detected: {pattern_name}",
                        message=f"Found '{pattern_name}' pattern in {'step ' + step_name if step_name else 'job'} '{job_name}'",
                        suggestion=pattern_config["suggestion"],
                        affected_job=job_name,
                        affected_step=step_name,
                        evidence={
                            "pattern": pattern_name,
                            "match": match.group(),
                            "context": context,
                            "match_count": len(matches),
                        },
                        references=[f"failure-pattern:{pattern_name}"],
                    )
                    result.add_finding(finding)
                    break  # Only report first match per pattern per job/step

    @classmethod
    def get_default_config(cls) -> dict[str, Any]:
        return {
            "enabled": True,
            "custom_patterns": [],
        }
