#!/bin/bash
# Setup development environment

set -e

echo "Setting up development environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install pre-commit and test dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install --constraint=.github/workflows/constraints.txt pre-commit
pip install -r requirements_test.txt

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
pre-commit install

echo "✓ Development environment setup complete!"
echo ""
echo "Virtual environment created in ./venv"
echo "To activate: source venv/bin/activate"
echo "Pre-commit hooks installed. They will run automatically on git commit."
echo "To run manually: pre-commit run --all-files"
