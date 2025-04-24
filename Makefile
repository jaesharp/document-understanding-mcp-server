# Document Understanding MCP Server Makefile
# This Makefile provides commands for setting up, testing, and maintaining the project

# Python version and paths
PYTHON := python3
VENV := .venv
VENV_BIN := $(VENV)/bin
VENV_PYTHON := $(VENV_BIN)/python
VENV_PIP := $(VENV_BIN)/pip
UV := uv

# Dependency files
PYPROJECT_TOML := pyproject.toml
UV_LOCK := uv.lock

# Project paths
SRC_DIR := src
TEST_DIR := tests
DOCS_DIR := docs

# Test and coverage settings
COVERAGE_REPORT_DIR := coverage_report
COVERAGE_HTML_DIR := $(COVERAGE_REPORT_DIR)/html
COVERAGE_XML := $(COVERAGE_REPORT_DIR)/coverage.xml

# Default target
.PHONY: all
all: check-deps setup-dev test lint coverage

# Help command
.PHONY: help
help:
	@echo "Document Understanding MCP Server Makefile"
	@echo ""
	@echo "Available commands:"
	@echo "  make setup              Setup virtual environment and install dependencies"
	@echo "  make setup-dev          Setup virtual environment with development dependencies"
	@echo "  make test               Run all tests"
	@echo "  make test-unit          Run unit tests only"
	@echo "  make test-integration   Run integration tests only"
	@echo "  make coverage           Run tests with coverage and generate reports"
	@echo "  make lint               Run all linting checks"
	@echo "  make format             Format code with Black"
	@echo "  make typecheck          Run type checking with mypy"
	@echo "  make clean              Remove build artifacts and temporary files"
	@echo "  make clean-all          Remove build artifacts, temporary files, and virtual environment"
	@echo "  make check-deps         Check and validate dependencies"
	@echo "  make update-deps        Update dependencies and regenerate lock file"
	@echo "  make help               Show this help message"

# Setup virtual environment and install dependencies
.PHONY: setup
setup: check-deps
	@echo "Setting up virtual environment..."
	$(UV) venv
	@echo "Installing dependencies..."
	$(UV) pip sync $(PYPROJECT_TOML)
	@echo "Setup complete."

# Setup virtual environment with development dependencies
.PHONY: setup-dev
setup-dev: setup
	@echo "Installing development dependencies..."
	$(UV) pip install -e '.[dev,test]'
	@echo "Development setup complete."

# Run all tests
.PHONY: test
test: verify-env
	@echo "Running all tests..."
	$(VENV_PYTHON) -m pytest $(TEST_DIR)

# Run unit tests only
.PHONY: test-unit
test-unit: verify-env
	@echo "Running unit tests..."
	$(VENV_PYTHON) -m pytest $(TEST_DIR)/unit

# Run integration tests only
.PHONY: test-integration
test-integration: verify-env
	@echo "Running integration tests..."
	$(VENV_PYTHON) -m pytest $(TEST_DIR)/integration

# Run tests with coverage and generate reports
.PHONY: coverage
coverage: verify-env
	@echo "Running tests with coverage..."
	mkdir -p $(COVERAGE_REPORT_DIR)
	$(VENV_PYTHON) -m pytest --cov=$(SRC_DIR) --cov-report=term --cov-report=html:$(COVERAGE_HTML_DIR) --cov-report=xml:$(COVERAGE_XML) $(TEST_DIR)
	@echo "Coverage report generated in $(COVERAGE_HTML_DIR)"

# Run all linting checks
.PHONY: lint
lint: verify-env format-check typecheck
	@echo "Running flake8..."
	$(VENV_PYTHON) -m flake8 $(SRC_DIR) $(TEST_DIR)

# Format code with Black
.PHONY: format
format: verify-env
	@echo "Formatting code with Black..."
	$(VENV_PYTHON) -m black $(SRC_DIR) $(TEST_DIR)

# Fix unused imports with autoflake
.PHONY: fix-imports
fix-imports: verify-env
	@echo "Removing unused imports with autoflake..."
	$(VENV_PYTHON) -m autoflake --in-place --remove-all-unused-imports --recursive $(SRC_DIR) $(TEST_DIR)

# Check code formatting with Black
.PHONY: format-check
format-check: verify-env
	@echo "Checking code formatting with Black..."
	$(VENV_PYTHON) -m black --check $(SRC_DIR) $(TEST_DIR)

# Run type checking with mypy
.PHONY: typecheck
typecheck: verify-env
	@echo "Running type checking with mypy..."
	$(VENV_PYTHON) -m mypy --ignore-missing-imports --no-namespace-packages $(SRC_DIR)

# Clean build artifacts and temporary files
.PHONY: clean
clean:
	@echo "Cleaning build artifacts and temporary files..."
	rm -rf build dist .eggs *.egg-info
	rm -rf .coverage $(COVERAGE_REPORT_DIR)
	rm -rf .pytest_cache .pytest_manual_workspace_stdio
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	@echo "Clean complete."

# Clean build artifacts, temporary files, and virtual environment
.PHONY: clean-all
clean-all: clean
	@echo "Removing virtual environment..."
	rm -rf $(VENV)
	@echo "Clean all complete."


# Generate documentation
.PHONY: docs
docs: verify-env
	@echo "Generating documentation..."
	# Add documentation generation commands here
	@echo "Documentation generated."

# Check for security vulnerabilities
.PHONY: security-check
security-check: verify-env
	@echo "Checking for security vulnerabilities..."
	$(UV) pip install bandit
	$(VENV_PYTHON) -m bandit -r $(SRC_DIR)
	@echo "Security check complete."


# Check and validate dependencies
.PHONY: check-deps
check-deps:
	@echo "Checking dependencies..."
	@if [ ! -f $(PYPROJECT_TOML) ]; then \
		echo "Error: $(PYPROJECT_TOML) not found"; \
		exit 1; \
	fi
	@if [ ! -f $(UV_LOCK) ]; then \
		echo "Warning: $(UV_LOCK) not found. Run 'make update-deps' to generate it."; \
	else \
		echo "Validating lock file against $(PYPROJECT_TOML)..."; \
		$(UV) pip check; \
	fi
	@echo "Checking for outdated dependencies..."
	$(UV) pip list --outdated
	@echo "Dependency check complete."

# Update dependencies and regenerate lock file
.PHONY: update-deps
update-deps:
	@echo "Updating dependencies and regenerating lock file..."
	$(UV) pip compile $(PYPROJECT_TOML) -o $(UV_LOCK)
	@echo "Lock file regenerated."

# Verify environment is properly set up
.PHONY: verify-env
verify-env:
	@echo "Verifying environment..."
	@if [ ! -d $(VENV) ]; then \
		echo "Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "Checking Python version..."
	$(VENV_PYTHON) --version
	@echo "Checking installed packages..."
	$(UV) pip list
	@echo "Environment verification complete."
