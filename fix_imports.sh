#!/bin/bash

# Activate the virtual environment
source .venv/bin/activate

# Run autoflake on all Python files in src and tests directories
autoflake --in-place --remove-all-unused-imports --recursive src/ tests/

echo "Unused imports removed successfully!"
