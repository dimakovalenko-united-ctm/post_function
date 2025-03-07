#!/bin/bash
set -o errexit -o nounset -o pipefail

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up test environment...${NC}"

# Make the current directory the project root
PROJECT_ROOT=$(pwd)
export PYTHONPATH=$PROJECT_ROOT

# Check if virtual environment exists, create if not
if [ ! -d ".venv" ]; then
  echo -e "${YELLOW}Creating virtual environment...${NC}"
  python -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt

# Create symlink to common directory if it doesn't exist
if [ ! -d "common" ]; then
  echo -e "${YELLOW}Creating symlink to common directory...${NC}"
  ln -s ../../common common
fi

# Run the tests
if [ "$#" -eq 0 ]; then
  echo -e "${YELLOW}Running all tests...${NC}"
  python -m pytest tests/
else
  echo -e "${YELLOW}Running specified tests...${NC}"
  python -m pytest "$@"
fi

# Display completion message
if [ $? -eq 0 ]; then
  echo -e "${GREEN}Tests completed successfully!${NC}"
else
  echo -e "${RED}Tests failed.${NC}"
  exit 1
fi