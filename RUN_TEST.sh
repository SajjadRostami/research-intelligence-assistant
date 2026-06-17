#!/bin/bash
#
# Quick test runner for the End-to-End MVP Test
#
# Usage:
#   ./RUN_TEST.sh
#

set -e

echo "=========================================="
echo "Research Intelligence Assistant MVP Test"
echo "=========================================="
echo ""

# Load environment variables from .env if it exists
if [ -f .env ]; then
    echo "Loading environment from .env"
    export $(grep -v '^#' .env | xargs)
elif [ -f ~/.env ]; then
    echo "Loading environment from ~/.env"
    export $(grep -v '^#' ~/.env | xargs)
fi

# Check if environment variables are set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "ERROR: OPENAI_API_KEY environment variable is not set"
    echo ""
    echo "Please set your API credentials:"
    echo "  export OPENAI_API_KEY=your-api-key"
    echo "  export OPENAI_BASE_URL=https://your-api-endpoint.com/v1"
    echo ""
    exit 1
fi

if [ -z "$OPENAI_BASE_URL" ]; then
    echo "ERROR: OPENAI_BASE_URL environment variable is not set"
    echo ""
    echo "Please set your API endpoint:"
    echo "  export OPENAI_BASE_URL=https://your-api-endpoint.com/v1"
    echo ""
    exit 1
fi

echo "Environment Configuration:"
echo "  API Key: ${OPENAI_API_KEY:0:20}***"
echo "  Base URL: ${OPENAI_BASE_URL}"
echo "  Model: ${LLM_MODEL:-claude-haiku}"
echo ""

# Check if SerpAPI key is set
if [ -z "$SERPAPI_API_KEY" ]; then
    echo "NOTE: SERPAPI_API_KEY not set"
    echo "  Using MockPatentAdapter for synthetic patent data"
    echo "  For real patents, set: export SERPAPI_API_KEY=your-key"
    echo ""
else
    echo "SerpAPI: Configured (${SERPAPI_API_KEY:0:10}***)"
    echo ""
fi

echo "Starting test..."
echo ""

# Run the test
python3 test_mvp_e2e.py

echo ""
echo "=========================================="
echo "Test complete!"
echo "=========================================="
