"""Security vulnerability analyzer."""

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
class SecurityAnalyzer(BaseAnalyzer):
    """Analyzes pipeline for security vulnerabilities and misconfigurations."""

    name = "security"
    description = "Detects secrets, vulnerable dependencies, and security misconfigurations"
    version = "1.0.0"

    # Common secret patterns
    SECRET_PATTERNS = [
        # Generic API keys
        (r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?", "API Key"),
        # AWS
        (r"(?i)(aws[_-]?access[_-]?key|aws[_-]?secret[_-]?key)\s*[:=]\s*['\"]?([A-Z0-9]{20,})['\"]?", "AWS Credentials"),
        # GitHub
        (r"(?i)(github[_-]?token|gh[_-]?pat)\s*[:=]\s*['\"]?(gh[ps]_[a-zA-Z0-9]{36,40})['\"]?", "GitHub Token"),
        (r"(?i)(?:^|[^\w])(gh[ps]_[a-zA-Z0-9]{36,40})(?:$|[^\w])", "GitHub Token"),
        # GitLab
        (r"(?i)(gitlab[_-]?token|glpat)\s*[:=]\s*['\"]?(glpat-[a-zA-Z0-9_\-]{20,})['\"]?", "GitLab Token"),
        (r"(?i)(?:^|[^\w])(glpat-[a-zA-Z0-9_\-]{20,})(?:$|[^\w])", "GitLab Token"),
        # Slack
        (r"(?i)(slack[_-]?token|xox[baprs]-[a-zA-Z0-9]{10,})", "Slack Token"),
        # Docker
        (r"(?i)(docker[_-]?password|docker[_-]?auth)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{10,})['\"]?", "Docker Credentials"),
        # NPM
        (r"(?i)(npm[_-]?token|_authToken)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?", "NPM Token"),
        # Generic passwords
        (r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?([^\s'\"]{8,})['\"]?", "Password"),
        # Private keys
        (r"-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----", "Private Key"),
        # JWT
        (r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "JWT Token"),
    ]

    # Security misconfiguration patterns
    MISCONFIG_PATTERNS = [
        (r"(?i)disable.*ssl|ssl.*verify.*false|verify.*ssl.*false", "SSL Verification Disabled"),
        (r"(?i)allow.*insecure|insecure.*true", "Insecure Connections Allowed"),
        (r"(?i)privileged.*true", "Privileged Container"),
        (r"(?i)run.*as.*root|USER root", "Running as Root"),
        (r"(?i)hostnetwork.*true|network.*host", "Host Network Mode"),
        (r"(?i)hostpid.*true|pid.*host", "Host PID Namespace"),
        (r"(?i)hostipc.*true|ipc.*host", "Host IPC Namespace"),
        (r"(?i)capabilities.*add.*ALL|cap_add.*ALL", "All Capabilities Added"),
        (r"(?i)readonly.*false", "Non-Readonly Root Filesystem"),
    ]

    def __init__(self, config: dict[str, Any] = None):
        super().__init__(config)
        self.scan_secrets = self.get_config("scan_secrets", True)
        self.scan_dependencies = self.get_config("scan_dependencies", True)
        self.scan_misconfigurations = self.get_config("scan_misconfigurations", True)
        self.custom_secret_patterns = self.get_config("secret_patterns", [])
        self._compiled_secret_patterns = self._compile_secret_patterns()
        self._compiled_misconfig_patterns = [
            (re.compile(p, re.IGNORECASE), desc) for p, desc in self.MISCONFIG_PATTERNS
        ]

    def _compile_secret_patterns(self) -> list[tuple]:
        """Compile all secret patterns."""
        patterns = []
        for pattern, desc in self.SECRET_PATTERNS:
            patterns.append((re.compile(pattern), desc))
        for custom in self.custom_secret_patterns:
            if isinstance(custom, dict) and "pattern" in custom:
                patterns.append((re.compile(custom["pattern"]), custom.get("description", "Custom Secret")))
        return patterns

    async def analyze(self, run: PipelineRun) -> AnalysisResult:
        """Analyze pipeline run for security issues."""
        result = AnalysisResult(analyzer_name=self.name, analyzer_version=self.version)

        if self.scan_secrets:
            self._scan_secrets(result, run)

        if self.scan_misconfigurations:
            self._scan_misconfigurations(result, run)

        if self.scan_dependencies:
            self._scan_dependencies(result, run)

        return result

    def _scan_secrets(self, result: AnalysisResult, run: PipelineRun) -> None:
        """Scan for secrets in logs and configuration."""
        # Scan job/step logs
        for job in run.jobs:
            for step in job.steps:
                if step.logs:
                    self._check_secrets_in_text(result, step.logs, job.name, step.name)

        # Scan pipeline metadata (environment variables, etc.)
        if run.metadata.get("environment"):
            for key, value in run.metadata["environment"].items():
                if isinstance(value, str):
                    self._check_secrets_in_text(result, value, "environment", key)

    def _check_secrets_in_text(
        self,
        result: AnalysisResult,
        text: str,
        job_name: str,
        step_name: str,
    ) -> None:
        """Check text for secret patterns."""
        for pattern, desc in self._compiled_secret_patterns:
            matches = list(pattern.finditer(text))
            if matches:
                match = matches[0]
                # Mask the secret in evidence
                context = text[max(0, match.start()-50):match.end()+50]
                try:
                    masked_text = pattern.sub(r"\1=***REDACTED***", context)
                except re.error:
                    masked_text = context.replace(match.group(), "***REDACTED***")

                result.add_finding(self.create_finding(
                    category=FindingCategory.SECURITY,
                    severity=FindingSeverity.CRITICAL,
                    title=f"Potential secret detected: {desc}",
                    message=f"Found potential {desc.lower()} in {'step ' + step_name if step_name != job_name else 'job'} '{job_name}'",
                    suggestion="Remove secret from logs/configuration and rotate the credential",
                    affected_job=job_name,
                    affected_step=step_name if step_name != job_name else None,
                    evidence={
                        "type": desc,
                        "context": masked_text,
                        "match_count": len(matches),
                    },
                    references=["https://owasp.org/www-project-top-ten/"],
                ))

    def _scan_misconfigurations(self, result: AnalysisResult, run: PipelineRun) -> None:
        """Scan for security misconfigurations."""
        # Check job/step configuration
        for job in run.jobs:
            # Check job metadata for security-relevant settings
            job_config = str(job.metadata)
            for pattern, desc in self._compiled_misconfig_patterns:
                if pattern.search(job_config):
                    result.add_finding(self.create_finding(
                        category=FindingCategory.SECURITY,
                        severity=FindingSeverity.WARNING,
                        title=f"Security misconfiguration: {desc}",
                        message=f"Job '{job.name}' has potential security misconfiguration",
                        suggestion=f"Review {desc.lower()} setting",
                        affected_job=job.name,
                        evidence={"type": desc, "config_sample": job_config[:200]},
                        references=["https://kubernetes.io/docs/concepts/security/"],
                    ))

            # Check steps
            for step in job.steps:
                step_config = str(step.metadata)
                for pattern, desc in self._compiled_misconfig_patterns:
                    if pattern.search(step_config):
                        result.add_finding(self.create_finding(
                            category=FindingCategory.SECURITY,
                            severity=FindingSeverity.WARNING,
                            title=f"Security misconfiguration: {desc}",
                            message=f"Step '{step.name}' in job '{job.name}' has potential security misconfiguration",
                            suggestion=f"Review {desc.lower()} setting",
                            affected_job=job.name,
                            affected_step=step.name,
                            evidence={"type": desc, "config_sample": step_config[:200]},
                        ))

    def _scan_dependencies(self, result: AnalysisResult, run: PipelineRun) -> None:
        """Scan for vulnerable dependencies (placeholder for integration with vulnerability DBs)."""
        # This would integrate with vulnerability databases like:
        # - GitHub Advisory Database
        # - NVD
        # - Snyk
        # - OSV
        # For now, we check for common indicators in logs

        vulnerability_indicators = [
            (r"vulnerability.*found|CVE-\d{4}-\d{4,}", "Known Vulnerability"),
            (r"audit.*vulnerabilit", "Dependency Audit Warning"),
            (r"outdated.*dependenc", "Outdated Dependency"),
            (r"deprecated.*package", "Deprecated Package"),
        ]

        compiled_indicators = [(re.compile(p, re.IGNORECASE), desc) for p, desc in vulnerability_indicators]

        for job in run.jobs:
            for step in job.steps:
                if step.logs:
                    for pattern, desc in compiled_indicators:
                        if pattern.search(step.logs):
                            result.add_finding(self.create_finding(
                                category=FindingCategory.DEPENDENCY,
                                severity=FindingSeverity.WARNING,
                                title=f"Dependency issue: {desc}",
                                message=f"Potential {desc.lower()} detected in step '{step.name}'",
                                suggestion="Run dependency audit and update vulnerable packages",
                                affected_job=job.name,
                                affected_step=step.name,
                                evidence={"type": desc},
                                references=["https://owasp.org/www-project-dependency-check/"],
                            ))

    @classmethod
    def get_default_config(cls) -> dict[str, Any]:
        return {
            "enabled": True,
            "scan_secrets": True,
            "scan_dependencies": True,
            "scan_misconfigurations": True,
            "secret_patterns": [],
        }
