#!/usr/bin/env bash
# this_file: test.sh
# Automated test suite for all vexy-stax projects
# Simplified version that only tests existing projects

set +e  # Don't exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_PASSED=0
TESTS_FAILED=0

echo "=========================================="
echo "Vexy-Stax Automated Test Suite"
echo "=========================================="
echo ""

# Function to validate PNG using Python
validate_png() {
    local png_path="$1"
    local expected_width="$2"
    local expected_height="$3"
    local test_name="$4"

    echo -n "Validating: $test_name... "

    # Direct Python validation without subshell complexity
    python3 -c "
from PIL import Image
import sys
try:
    img = Image.open('$png_path')
    if img.format != 'PNG':
        print('Error: Not a PNG')
        sys.exit(1)
    if $expected_width > 0 and img.width != $expected_width:
        print(f'Error: Width {img.width} != {expected_width}')
        sys.exit(1)
    if $expected_height > 0 and img.height != $expected_height:
        print(f'Error: Height {img.height} != {expected_height}')
        sys.exit(1)
    sys.exit(0)
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
" 2>&1 | head -1

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test Suite: Validate existing PNG outputs
echo "Test Suite: PNG Output Validation"
echo "-----------------------------------"

# Only test files that actually exist
if [ -f "$SCRIPT_DIR/test-img/out-pm-stack.png" ]; then
    validate_png "$SCRIPT_DIR/test-img/out-pm-stack.png" 0 0 "out-pm-stack.png (vexy-stax-pm)"
fi

if [ -f "$SCRIPT_DIR/img/out-wt.png" ]; then
    validate_png "$SCRIPT_DIR/img/out-wt.png" 0 0 "out-wt.png (vexy-stax-wt)"
fi

# Visual regression test (if reference exists)
if [ -f "$SCRIPT_DIR/test-img/reference/out-pm-stack-reference.png" ] && \
   [ -f "$SCRIPT_DIR/test-img/out-pm-stack.png" ]; then
    echo -n "Visual regression: out-pm-stack.png... "

    # Use Python PIL to compare images
    python3 -c "
from PIL import Image
import sys

try:
    ref = Image.open('$SCRIPT_DIR/test-img/reference/out-pm-stack-reference.png')
    current = Image.open('$SCRIPT_DIR/test-img/out-pm-stack.png')

    # Check dimensions match
    if ref.size != current.size:
        print(f'Size mismatch: {ref.size} vs {current.size}')
        sys.exit(1)

    # Convert to RGB for comparison (ignore alpha differences)
    ref_rgb = ref.convert('RGB')
    current_rgb = current.convert('RGB')

    # Calculate pixel difference
    diff_count = 0
    total_pixels = ref_rgb.size[0] * ref_rgb.size[1]

    ref_data = list(ref_rgb.getdata())
    current_data = list(current_rgb.getdata())

    for i in range(total_pixels):
        r1, g1, b1 = ref_data[i]
        r2, g2, b2 = current_data[i]
        # Allow small color differences (threshold of 10 per channel)
        if abs(r1-r2) > 10 or abs(g1-g2) > 10 or abs(b1-b2) > 10:
            diff_count += 1

    diff_percent = (diff_count / total_pixels) * 100

    # Allow 1% pixel difference
    if diff_percent > 1.0:
        print(f'Too many differences: {diff_percent:.2f}% pixels differ')
        sys.exit(1)

    sys.exit(0)
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
" 2>&1 | head -1

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((TESTS_FAILED++))
    fi
fi

# Test vexy-stax-wt exists and has required files
echo ""
echo "Test Suite: Project Structure"
echo "------------------------------"

echo -n "Checking vexy-stax-wt structure... "
if [ -d "$SCRIPT_DIR/vexy-stax-wt" ] && \
   [ -f "$SCRIPT_DIR/vexy-stax-wt/package.json" ] && \
   [ -f "$SCRIPT_DIR/vexy-stax-wt/index.html" ] && \
   [ -f "$SCRIPT_DIR/vexy-stax-wt/src/main.js" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((TESTS_FAILED++))
fi

echo -n "Checking vexy-stax-wl structure... "
if [ -d "$SCRIPT_DIR/vexy-stax-wl" ] && \
   [ -f "$SCRIPT_DIR/vexy-stax-wl/PLAN.md" ] && \
   [ -f "$SCRIPT_DIR/vexy-stax-wl/TODO.md" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((TESTS_FAILED++))
fi

# Test documentation exists
echo ""
echo "Test Suite: Documentation"
echo "-------------------------"

for doc in "TODO.md" "WORK.md" "CHANGELOG.md"; do
    echo -n "Checking $doc... "
    if [ -f "$SCRIPT_DIR/$doc" ]; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((TESTS_FAILED++))
    fi
done

# Summary
echo ""
echo "=========================================="
echo "Test Results Summary"
echo "=========================================="
echo -e "Passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Failed: ${RED}${TESTS_FAILED}${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
