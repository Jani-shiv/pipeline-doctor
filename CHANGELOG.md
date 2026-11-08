# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure
- Core models for pipelines, runs, jobs, and steps
- Analysis framework with findings and reports
- Configuration system with environment variable support
- Plugin architecture for analyzers, reporters, and integrations

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

## [0.1.0] - 2024-01-15

### Added
- **Analyzers**:
  - Failure Pattern Analyzer: Detects common failure patterns (timeouts, OOM, permissions, etc.)
  - Performance Analyzer: Identifies bottlenecks and slow jobs/steps
  - Security Analyzer: Scans for secrets, vulnerable dependencies, and misconfigurations
  - Cost Analyzer: Calculates pipeline costs and identifies waste
  - Reliability Analyzer: Detects flaky tests and retry patterns

- **Reporters**:
  - HTML Reporter: Interactive reports with charts
  - JSON Reporter: Machine-readable output
  - JSON Lines Reporter: Streaming-friendly NDJSON
  - Markdown Reporter: Documentation-friendly reports
  - GitHub Markdown Reporter: PR comment optimized
  - PDF Reporter: Professional PDF reports

- **Platform Integrations**:
  - GitHub Actions
  - GitLab CI/CD
  - Jenkins
  - Azure DevOps Pipelines
  - CircleCI

- **CLI Commands**:
  - `analyze`: Analyze pipeline runs
  - `monitor`: Real-time pipeline monitoring
  - `report`: Historical health reports
  - `scan`: Local configuration scanning

- **Configuration**:
  - YAML-based configuration with environment variable override
  - Per-analyzer, per-reporter, per-platform settings
  - Notification channels (Slack, Email, PagerDuty, Webhooks)

- **Infrastructure**:
  - Docker support with multi-stage build
  - Docker Compose for local development
  - GitHub Actions CI/CD pipeline
  - Pre-commit hooks for code quality
  - Comprehensive test suite

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- Secret scanning in logs and configurations
- Secure credential handling via environment variables
- SSL verification for all platform APIs