# Reporters

Pipeline Doctor supports multiple output formats for analysis reports.

## Available Reporters

| Reporter | Format | Use Case |
|----------|--------|----------|
| HTML | Interactive HTML | Web viewing, dashboards |
| JSON | Machine-readable JSON | API integration, automation |
| JSONL | Newline-delimited JSON | Log aggregation, streaming |
| Markdown | GitHub-flavored Markdown | Documentation, PR comments |
| PDF | Professional PDF | Archival, compliance |

## HTML Reporter (`html`)

Generates interactive HTML reports with charts and collapsible findings.

### Features

- Responsive design
- Severity color coding
- Chart.js visualizations
- Collapsible evidence details
- Print-friendly CSS

### Configuration

```yaml
reporters:
  html:
    enabled: true
    config:
      template: "default"      # Template name
      include_charts: true     # Include Chart.js charts
      include_raw_data: false  # Include raw JSON evidence
      theme: "light"           # light or dark
    output_dir: "./reports"
```

### Example Output

![HTML Report](assets/html-report.png)

## JSON Reporter (`json`)

Generates machine-readable JSON for programmatic consumption.

### Configuration

```yaml
reporters:
  json:
    enabled: true
    config:
      pretty: true             # Pretty-print JSON
      include_metadata: true   # Include full metadata
    output_dir: "./reports"
```

### Example Output

```json
{
  "report_id": "uuid",
  "pipeline_id": "uuid",
  "run_id": "uuid",
  "platform": "github",
  "generated_at": "2024-01-15T10:30:00Z",
  "summary": {
    "total_findings": 5,
    "by_severity": {
      "critical": 1,
      "error": 2,
      "warning": 1,
      "info": 1
    },
    "by_category": {
      "failure_pattern": 2,
      "performance": 1,
      "security": 1,
      "cost": 1
    },
    "has_critical_findings": true
  },
  "analyzers": [
    {
      "name": "failure",
      "version": "1.0.0",
      "findings": [
        {
          "id": "uuid",
          "category": "failure_pattern",
          "severity": "critical",
          "title": "Failure pattern detected: out_of_memory",
          "message": "...",
          "suggestion": "...",
          "evidence": {}
        }
      ]
    }
  ]
}
```

## JSON Lines Reporter (`jsonl`)

Generates newline-delimited JSON for streaming and log aggregation.

### Use Cases

- Real-time log streaming
- Elasticsearch/Logstash ingestion
- Splunk integration
- Custom processing pipelines

### Example Output

```json
{"type": "report_header", "report_id": "uuid", "pipeline_id": "uuid", "platform": "github", "generated_at": "2024-01-15T10:30:00Z"}
{"type": "analyzer_result", "analyzer": "failure", "duration_seconds": 0.5, "errors": []}
{"type": "finding", "id": "uuid", "analyzer": "failure", "category": "failure_pattern", "severity": "critical", "title": "...", "message": "..."}
{"type": "report_footer", "total_findings": 5, "by_severity": {"critical": 1, "error": 2, "warning": 1, "info": 1}}
```

## Markdown Reporter (`markdown`)

Generates GitHub-flavored Markdown for documentation and PR comments.

### Configuration

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

### Example Output

```markdown
# 🏥 Pipeline Doctor Report

**Pipeline:** `uuid`
**Run:** `uuid`
**Platform:** github
**Generated:** 2024-01-15 10:30:00 UTC

## 📊 Summary

**Total Findings:** 5

| Severity | Count |
|----------|-------|
| 🔴 Critical | 1 |
| 🟠 Error | 2 |
| 🟡 Warning | 1 |
| 🔵 Info | 1 |

## 🔍 Detailed Findings

### Failure Analyzer

#### 🔴 Test Finding

**Severity:** Error
**Category:** Failure Pattern
**Job:** `test-job`

Test error message

> 💡 **Suggestion:** Fix the error
```

## GitHub Markdown Reporter (`github-md`)

Generates optimized Markdown for GitHub PR comments and issues.

### Features

- Collapsible details sections
- Summary tables
- Truncated findings (configurable)
- Embedded JSON for full data

### Configuration

```yaml
reporters:
  github-md:
    enabled: true
    config:
      max_findings: 50
      collapse_details: true
    output_dir: "./reports"
```

## PDF Reporter (`pdf`)

Generates professional PDF reports using WeasyPrint.

### Requirements

```bash
# System dependencies (Ubuntu/Debian)
apt-get install libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info

# Python package
pip install weasyprint
```

### Configuration

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

## Selecting Reporters

### CLI

```bash
# Single reporter
pipeline-doctor analyze --format html

# Multiple reporters (run multiple times)
pipeline-doctor analyze --format html --output report.html
pipeline-doctor analyze --format json --output report.json
```

### Configuration

```yaml
reporters:
  html:
    enabled: true
  json:
    enabled: true
  markdown:
    enabled: false  # Disable

default_reporter: "html"  # Used when --format not specified
```

## Custom Templates

### HTML Templates

Create custom templates in `templates/` directory:

```
templates/
├── default.html      # Default template
├── custom.html       # Your custom template
└── minimal.html      # Minimal template
```

Use custom template:

```yaml
reporters:
  html:
    config:
      template: "custom"
```

### Template Variables

Available in all templates:

```python
{
    "report": AnalysisReport,
    "findings_by_severity": Dict[FindingSeverity, int],
    "findings_by_category": Dict[FindingCategory, int],
    "findings_by_analyzer": Dict[str, List[Finding]],
    "total_findings": int,
    "has_critical": bool,
    "severity_order": List[FindingSeverity],
    "category_order": List[FindingCategory],
}
```

## Custom Reporters

Create custom reporters by extending `BaseReporter`:

```python
from pipeline_doctor.reporters.base import BaseReporter, ReporterRegistry
from pipeline_doctor.core.models import AnalysisReport
from pathlib import Path

@ReporterRegistry.register
class MyCustomReporter(BaseReporter):
    name = "my-custom"
    description = "Custom reporter"
    
    async def generate(self, report: AnalysisReport, output_path: Path = None) -> Path:
        # Generate your custom format
        output_path = output_path or self.get_output_path(report, "custom")
        output_path.write_text("Custom report content")
        return output_path
```

Enable in config:

```yaml
reporters:
  my-custom:
    enabled: true
    config:
      custom_option: "value"
```

## Report Storage

Reports are saved to the configured `output_dir` (default: `./reports`).

### Naming Convention

```
{reporter}_report_{timestamp}.{extension}
```

Examples:
- `html_report_20240115_103000.html`
- `json_report_20240115_103000.json`
- `markdown_report_20240115_103000.md`

### Programmatic Access

```python
from pipeline_doctor.reporters import HTMLReporter, JSONReporter
from pipeline_doctor.core.config import load_config

config = load_config()
html_reporter = HTMLReporter(config.reporters.html.config, "./reports")
json_reporter = JSONReporter(config.reporters.json.config, "./reports")

html_path = await html_reporter.generate(report)
json_path = await json_reporter.generate(report)
```