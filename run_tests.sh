#!/bin/bash
set -o errexit -o nounset -o pipefail

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up test environment...${NC}"

# Check if virtual environment exists, create if not
if [ ! -d ".venv" ]; then
  echo -e "${YELLOW}Creating virtual environment...${NC}"
  python -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install in development mode for proper imports
echo -e "${YELLOW}Installing package in development mode...${NC}"
pip install -e . --quiet

# Install test dependencies
echo -e "${YELLOW}Installing test dependencies...${NC}"
pip install pytest pytest-cov --quiet

# Create __init__.py in tests directory if it doesn't exist
mkdir -p tests
if [ ! -f "tests/__init__.py" ]; then
  echo "# Test package" > tests/__init__.py
  echo -e "${GREEN}Created tests/__init__.py${NC}"
fi

# Run the tests
echo -e "${YELLOW}Running tests...${NC}"
PYTHONPATH=. pytest "$@"

# Display completion message
if [ $? -eq 0 ]; then
  echo -e "${GREEN}Tests completed successfully!${NC}"
else
  echo -e "${RED}Tests failed.${NC}"
  exit 1
fi