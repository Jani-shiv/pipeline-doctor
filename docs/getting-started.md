# Getting Started

This guide will help you get up and running with Pipeline Doctor quickly.

## Installation

### Via pip (Recommended)

```bash
pip install pipeline-doctor
```

### Via Docker

```bash
docker pull ghcr.io/your-org/pipeline-doctor:latest
```

### From Source

```bash
git clone https://github.com/your-org/pipeline-doctor.git
cd pipeline-doctor
pip install -e ".[dev]"
```

## Configuration

Create a configuration file:

```bash
# Copy example config
cp config/example.yaml config/pipeline-doctor.yaml

# Edit with your settings
# Required: Add your platform tokens
```

### Minimum Configuration

```yaml
platforms:
  github:
    enabled: true
    token: "${GITHUB_TOKEN}"
    owner: "your-org"
    repo: "your-repo"
```

Set your token as an environment variable:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

## First Analysis

### Analyze a Specific Run

```bash
pipeline-doctor analyze \
  --platform github \
  --repo your-org/your-repo \
  --pipeline 12345678 \
  --run 87654321
```

### Analyze Recent Runs

```bash
pipeline-doctor analyze \
  --platform github \
  --repo your-org/your-repo \
  --pipeline 12345678 \
  --limit 20
```

### Generate a Health Report

```bash
pipeline-doctor report \
  --platform github \
  --repo your-org/your-repo \
  --pipeline 12345678 \
  --days 30 \
  --format html \
  --output health-report.html
```

### Scan Local Configuration

```bash
pipeline-doctor scan .github/workflows/ci.yml --platform github
```

## Understanding Results

Pipeline Doctor generates findings categorized by:

| Severity | Description |
|----------|-------------|
| 🔴 Critical | Immediate action required (security, data loss) |
| 🟠 Error | Significant issues affecting pipeline reliability |
| 🟡 Warning | Potential improvements or minor issues |
| 🔵 Info | Informational findings |

### Finding Categories

- **Failure Pattern**: Common failure signatures
- **Performance**: Bottlenecks and slow execution
- **Security**: Secrets, vulnerabilities, misconfigurations
- **Cost**: Resource waste and optimization opportunities
- **Reliability**: Flaky tests, retries, timeouts

## Next Steps

1. [Configure your platforms](configuration.md#platform-configuration)
2. [Set up notifications](configuration.md#notification-configuration)
3. [Explore built-in analyzers](analyzers.md)
4. [Customize reports](reporters.md)
5. [Read platform-specific guides](platforms/)