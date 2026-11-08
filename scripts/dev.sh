#!/usr/bin/env bash
# Pipeline Doctor - Quick start script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Check if running in virtual environment
check_venv() {
    if [[ -z "${VIRTUAL_ENV:-}" ]]; then
        log_warn "Not running in a virtual environment"
        log_info "Consider running: python -m venv venv && source venv/bin/activate"
    fi
}

# Install dependencies
install_deps() {
    log_info "Installing dependencies..."
    pip install -e ".[dev]"
}

# Run tests
run_tests() {
    log_info "Running tests..."
    pytest "$@"
}

# Run linting
run_lint() {
    log_info "Running linter..."
    ruff check src tests
}

# Format code
run_format() {
    log_info "Formatting code..."
    ruff format src tests
}

# Type check
run_typecheck() {
    log_info "Running type checker..."
    mypy src
}

# Build package
build_package() {
    log_info "Building package..."
    python -m build
}

# Build Docker image
build_docker() {
    log_info "Building Docker image..."
    docker build -t pipeline-doctor:latest .
}

# Run pipeline doctor
run_doctor() {
    log_info "Running Pipeline Doctor..."
    pipeline-doctor "$@"
}

# Main
main() {
    case "${1:-help}" in
        install)
            check_venv
            install_deps
            ;;
        test)
            shift
            run_tests "$@"
            ;;
        lint)
            run_lint
            ;;
        format)
            run_format
            ;;
        typecheck)
            run_typecheck
            ;;
        check)
            run_lint
            run_format
            run_typecheck
            ;;
        build)
            build_package
            ;;
        docker-build)
            build_docker
            ;;
        doctor)
            shift
            run_doctor "$@"
            ;;
        *)
            echo "Usage: $0 {install|test|lint|format|typecheck|check|build|docker-build|doctor}"
            echo ""
            echo "Commands:"
            echo "  install      Install package in development mode"
            echo "  test         Run tests"
            echo "  lint         Run linter"
            echo "  format       Format code"
            echo "  typecheck    Run type checker"
            echo "  check        Run all quality checks"
            echo "  build        Build distribution packages"
            echo "  docker-build Build Docker image"
            echo "  doctor       Run pipeline-doctor CLI"
            exit 1
            ;;
    esac
}

main "$@"