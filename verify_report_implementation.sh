#!/bin/bash
set -e

echo "=========================================="
echo "ReportRenderer Implementation Verification"
echo "=========================================="
echo ""

echo "1. Testing with MVP workspace (patents only)..."
python test_report_generation.py > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ MVP workspace test passed"
else
    echo "   ✗ MVP workspace test failed"
    exit 1
fi

echo ""
echo "2. Testing with synthetic data (papers + patents)..."
python test_report_with_papers.py > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ Synthetic data test passed"
else
    echo "   ✗ Synthetic data test failed"
    exit 1
fi

echo ""
echo "3. Testing integration with WorkspaceManager..."
python test_report_integration.py > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ Integration test passed"
else
    echo "   ✗ Integration test failed"
    exit 1
fi

echo ""
echo "4. Verifying generated report files..."
if [ -f "test_mvp_workspace/xpbd-soft-body-simulation-algorithm/report.md" ]; then
    echo "   ✓ MVP workspace report exists"
else
    echo "   ✗ MVP workspace report missing"
    exit 1
fi

if [ -f "test_report_output/report.md" ]; then
    echo "   ✓ Test report exists"
else
    echo "   ✗ Test report missing"
    exit 1
fi

echo ""
echo "5. Validating report structure..."
REPORT="test_mvp_workspace/xpbd-soft-body-simulation-algorithm/report.md"

SECTIONS=(
    "# Research Intelligence Report:"
    "## Executive Summary"
    "## Top Patents"
    "## Top Papers"
    "## Benchmark Metrics"
    "## References"
)

ALL_FOUND=true
for section in "${SECTIONS[@]}"; do
    if grep -q "$section" "$REPORT"; then
        echo "   ✓ Found: $section"
    else
        echo "   ✗ Missing: $section"
        ALL_FOUND=false
    fi
done

if [ "$ALL_FOUND" = false ]; then
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ All verification tests passed!"
echo "=========================================="
echo ""
echo "Implementation Summary:"
echo "  - ReportRenderer class: ria/report.py"
echo "  - Test scripts: 3 tests, all passing"
echo "  - Generated reports: 2 examples"
echo "  - Integration: WorkspaceManager compatible"
echo ""
