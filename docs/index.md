# Pipeline Doctor Documentation

Welcome to the Pipeline Doctor documentation! Pipeline Doctor is an open-source CI/CD pipeline diagnostics and health monitoring tool.

## 🚀 Quick Links

- [Getting Started](getting-started.md) - Installation and first steps
- [Configuration](configuration.md) - Configuration file reference
- [Platform Guides](platforms/) - Platform-specific setup guides
- [Analyzers](analyzers.md) - Built-in analyzers reference
- [Reporters](reporters.md) - Output formats and customization
- [Integrations](integrations.md) - Notification and ticketing integrations
- [API Reference](api-reference.md) - Python API documentation
- [Architecture](architecture.md) - System design and internals

## 🏥 What is Pipeline Doctor?

Pipeline Doctor is a comprehensive tool for analyzing, monitoring, and improving your CI/CD pipelines. It supports multiple platforms and provides actionable insights into pipeline health, performance, security, and cost.

### Key Features

- **Multi-Platform Support**: GitHub Actions, GitLab CI, Jenkins, Azure DevOps, CircleCI
- **Real-time Diagnostics**: Analyze pipeline runs for failures, bottlenecks, and anomalies
- **Root Cause Analysis**: Automated failure classification and suggested fixes
- **Performance Tracking**: Monitor pipeline duration trends and resource usage
- **Security Scanning**: Detect secrets, vulnerable dependencies, and misconfigurations
- **Cost Optimization**: Identify wasteful runs and optimize resource allocation
- **Smart Alerting**: Configurable notifications via Slack, Email, Webhooks, PagerDuty
- **Comprehensive Reports**: HTML, JSON, Markdown, and PDF report generation
- **Extensible Architecture**: Plugin system for custom analyzers and integrations

## 📦 Installation

```bash
# Via pip (recommended)
pip install pipeline-doctor

# Via Docker
docker pull ghcr.io/your-org/pipeline-doctor:latest

# From source
git clone https://github.com/your-org/pipeline-doctor.git
cd pipeline-doctor
pip install -e .
```

## 🎯 Quick Start

```bash
# Analyze a GitHub Actions workflow
pipeline-doctor analyze --platform github --repo owner/repo --workflow ci.yml

# Generate health report
pipeline-doctor report --repo owner/repo --days 30 --format html --output report.html

# Monitor pipeline in real-time
pipeline-doctor monitor --repo owner/repo --platform github --webhook-url https://your-webhook
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](../CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

## 🙏 Support

- **Issues**: [GitHub Issues](https://github.com/your-org/pipeline-doctor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/pipeline-doctor/discussions)
- **Discord**: [Join our community](https://discord.gg/pipeline-doctor)
- **Email**: support@pipeline-doctor.io