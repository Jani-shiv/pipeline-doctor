# Configuration Reference

Pipeline Doctor is configured via a YAML file with environment variable overrides.

## Configuration File

Default location: `config/pipeline-doctor.yaml`

```yaml
# Application settings
app_name: "pipeline-doctor"
version: "0.1.0"
debug: false
log_level: "INFO"
log_format: "json"

# Platform configurations
platforms:
  github:
    enabled: true
    token: "${GITHUB_TOKEN}"
    api_url: "https://api.github.com"
    owner: "your-org"
    repo: "your-repo"
    verify_ssl: true
    timeout: 30
    rate_limit: 100

# ... other platforms

# Analyzer configurations
analyzers:
  failure:
    enabled: true
    config:
      patterns: [...]
      custom_patterns: []

# Reporter configurations
reporters:
  html:
    enabled: true
    config:
      template: "default"
      include_charts: true

# Default reporter
default_reporter: "html"

# Notification configurations
notifications:
  slack:
    enabled: false
    webhook_url: "${SLACK_WEBHOOK}"
    channel: "#pipeline-alerts"

# Storage configuration
storage:
  type: "sqlite"
  path: "./data/pipeline-doctor.db"

# Analysis settings
max_concurrent_analyzers: 5
analysis_timeout: 300
cache_ttl: 3600
```

## Environment Variables

All configuration values can be overridden via environment variables using the pattern `PIPELINE_DOCTOR_<SECTION>_<KEY>` or platform-specific variables.

| Variable | Description | Default |
|----------|-------------|---------|
| `PIPELINE_DOCTOR_DEBUG` | Enable debug mode | `false` |
| `PIPELINE_DOCTOR_LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `GITHUB_TOKEN` | GitHub Personal Access Token | Required for GitHub |
| `GITHUB_OWNER` | GitHub organization/user | - |
| `GITHUB_REPO` | GitHub repository | - |
| `GITLAB_TOKEN` | GitLab Personal Access Token | Required for GitLab |
| `GITLAB_PROJECT_ID` | GitLab project ID | - |
| `JENKINS_URL` | Jenkins server URL | Required for Jenkins |
| `JENKINS_USER` | Jenkins username | - |
| `JENKINS_TOKEN` | Jenkins API token | Required for Jenkins |
| `AZURE_PAT` | Azure DevOps Personal Access Token | Required for Azure DevOps |
| `AZURE_ORG` | Azure DevOps organization | - |
| `AZURE_PROJECT` | Azure DevOps project | - |
| `CIRCLECI_TOKEN` | CircleCI API token | Required for CircleCI |
| `CIRCLECI_PROJECT` | CircleCI project slug | - |
| `SLACK_WEBHOOK` | Slack incoming webhook URL | - |
| `PAGERDUTY_KEY` | PagerDuty integration key | - |

## Platform Configuration

Each platform has its own configuration section under `platforms.<platform>`.

### GitHub Actions

```yaml
platforms:
  github:
    enabled: true
    token: "${GITHUB_TOKEN}"
    api_url: "https://api.github.com"
    owner: "your-org"
    repo: "your-repo"
    verify_ssl: true
    timeout: 30
    rate_limit: 100
```

Required token scopes: `repo`, `workflow`, `read:org`

### GitLab CI

```yaml
platforms:
  gitlab:
    enabled: true
    token: "${GITLAB_TOKEN}"
    api_url: "https://gitlab.com/api/v4"
    project_id: "12345678"
    verify_ssl: true
    timeout: 30
    rate_limit: 100
```

Required token scopes: `api`, `read_repository`

### Jenkins

```yaml
platforms:
  jenkins:
    enabled: true
    url: "${JENKINS_URL}"
    username: "${JENKINS_USER}"
    token: "${JENKINS_TOKEN}"
    job_name: "your-job-name"
    verify_ssl: true
    timeout: 30
    rate_limit: 50
```

### Azure DevOps

```yaml
platforms:
  azure_devops:
    enabled: true
    token: "${AZURE_PAT}"
    organization: "your-org"
    project: "your-project"
    api_url: "https://dev.azure.com"
    verify_ssl: true
    timeout: 30
    rate_limit: 100
```

Required token scopes: `Build`, `Code`, `Project and team` (read)

### CircleCI

```yaml
platforms:
  circleci:
    enabled: true
    token: "${CIRCLECI_TOKEN}"
    project_slug: "gh/your-org/your-repo"
    api_url: "https://circleci.com/api/v2"
    verify_ssl: true
    timeout: 30
    rate_limit: 100
```

## Analyzer Configuration

Each analyzer can be configured under `analyzers.<name>`.

### Failure Analyzer

```yaml
analyzers:
  failure:
    enabled: true
    config:
      patterns:
        - "timeout"
        - "out of memory"
        - "permission denied"
      custom_patterns:
        - pattern: "my_custom_error"
          severity: "warning"
          suggestion: "Check custom error"
          category: "custom"
```

### Performance Analyzer

```yaml
analyzers:
  performance:
    enabled: true
    config:
      thresholds:
        pipeline_duration_warn: 1800
        pipeline_duration_critical: 3600
        job_duration_warn: 300
        job_duration_critical: 600
        step_duration_warn: 60
        step_duration_critical: 180
        queue_time_warn: 120
        queue_time_critical: 300
        waste_threshold_minutes: 10
      compare_baseline: true
      baseline_runs: 10
```

### Security Analyzer

```yaml
analyzers:
  security:
    enabled: true
    config:
      scan_secrets: true
      scan_dependencies: true
      scan_misconfigurations: true
      secret_patterns:
        - "(?i)(api[_-]?key|secret|password|token)\\s*[:=]\\s*['\"]?[a-zA-Z0-9_\\-]{20,}['\"]?"
```

### Cost Analyzer

```yaml
analyzers:
  cost:
    enabled: true
    config:
      currency: "USD"
      compute_cost_per_minute: 0.008
      storage_cost_per_gb_month: 0.10
      network_cost_per_gb: 0.09
      track_waste: true
      waste_threshold_minutes: 10
```

### Reliability Analyzer

```yaml
analyzers:
  reliability:
    enabled: true
    config:
      flaky_threshold: 0.1
      min_runs_for_flaky: 10
      check_retries: true
      check_timeouts: true
```

## Reporter Configuration

Each reporter can be configured under `reporters.<name>`.

### HTML Reporter

```yaml
reporters:
  html:
    enabled: true
    config:
      template: "default"
      include_charts: true
      include_raw_data: false
      theme: "light"
    output_dir: "./reports"
```

### JSON Reporter

```yaml
reporters:
  json:
    enabled: true
    config:
      pretty: true
      include_metadata: true
    output_dir: "./reports"
```

### Markdown Reporter

```yaml
reporters:
  markdown:
    enabled: true
    config:
      include_summary: true
      include_details: true
      table_format: "github"
    output_dir: "./reports"
```

### PDF Reporter

```yaml
reporters:
  pdf:
    enabled: true
    config:
      page_size: "A4"
      margin: "2cm"
      include_charts: true
    output_dir: "./reports"
```

## Notification Configuration

Configure notification channels under `notifications.<name>`.

### Slack

```yaml
notifications:
  slack:
    enabled: true
    webhook_url: "${SLACK_WEBHOOK}"
    channel: "#pipeline-alerts"
    username: "Pipeline Doctor"
    icon_emoji: ":stethoscope:"
```

### Email

```yaml
notifications:
  email:
    enabled: true
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    smtp_username: "${EMAIL_USER}"
    smtp_password: "${EMAIL_PASSWORD}"
    from_email: "pipeline-doctor@example.com"
    to_emails:
      - "team@example.com"
      - "ops@example.com"
```

### PagerDuty

```yaml
notifications:
  pagerduty:
    enabled: true
    integration_key: "${PAGERDUTY_KEY}"
```

### Webhook

```yaml
notifications:
  webhook:
    enabled: true
    webhook_url: "${WEBHOOK_URL}"
```

## Storage Configuration

Configure data persistence under `storage`.

### SQLite (Default)

```yaml
storage:
  type: "sqlite"
  path: "./data/pipeline-doctor.db"
```

### PostgreSQL

```yaml
storage:
  type: "postgresql"
  host: "localhost"
  port: 5432
  database: "pipeline_doctor"
  username: "postgres"
  password: "${DB_PASSWORD}"
  pool_size: 5
  max_overflow: 10
  echo: false
```

### MongoDB

```yaml
storage:
  type: "mongodb"
  host: "localhost"
  port: 27017
  database: "pipeline_doctor"
  username: "admin"
  password: "${DB_PASSWORD}"
```

## Complete Example

See [config/example.yaml](../config/example.yaml) for a complete configuration example with all options.