#!/bin/bash
# Validation script for Call Center Audio Intelligence
# Run this script to verify all services are working correctly

set -e

echo "=========================================="
echo "Call Center Audio Intelligence - Validation"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"

passed=0
failed=0

check() {
    local name="$1"
    local cmd="$2"
    
    echo -n "Checking $name... "
    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((passed++))
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((failed++))
    fi
}

echo "1. Database Connectivity"
echo "------------------------"
check "PostgreSQL is running" "docker exec call-center-db pg_isready -U call_center"
check "Database exists" "docker exec call-center-db psql -U call_center -d call_center_ai -c 'SELECT 1'"

echo ""
echo "2. Redis Connectivity"
echo "---------------------"
check "Redis is running" "docker exec call-center-redis redis-cli ping"

echo ""
echo "3. Backend API"
echo "--------------"
check "Health endpoint" "curl -sf ${BACKEND_URL}/health"
check "Readiness endpoint" "curl -sf ${BACKEND_URL}/ready"
check "API docs available" "curl -sf ${BACKEND_URL}/docs"
check "Agents endpoint" "curl -sf ${BACKEND_URL}/api/agents"
check "Calls endpoint" "curl -sf ${BACKEND_URL}/api/calls"
check "Dashboard overview" "curl -sf ${BACKEND_URL}/api/dashboard/overview"

echo ""
echo "4. Frontend"
echo "-----------"
check "Frontend is accessible" "curl -sf ${FRONTEND_URL}"

echo ""
echo "5. API Response Validation"
echo "--------------------------"

# Test health response structure
health_response=$(curl -sf ${BACKEND_URL}/health 2>/dev/null || echo "{}")
if echo "$health_response" | grep -q '"status":"healthy"'; then
    echo -e "Health response structure: ${GREEN}✓ VALID${NC}"
    ((passed++))
else
    echo -e "Health response structure: ${RED}✗ INVALID${NC}"
    ((failed++))
fi

# Test agents response is array
agents_response=$(curl -sf ${BACKEND_URL}/api/agents 2>/dev/null || echo "null")
if echo "$agents_response" | grep -qE '^\['; then
    echo -e "Agents response is array: ${GREEN}✓ VALID${NC}"
    ((passed++))
else
    echo -e "Agents response is array: ${RED}✗ INVALID${NC}"
    ((failed++))
fi

echo ""
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo -e "Passed: ${GREEN}${passed}${NC}"
echo -e "Failed: ${RED}${failed}${NC}"
echo ""

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}All checks passed! System is ready.${NC}"
    exit 0
else
    echo -e "${YELLOW}Some checks failed. Please review the output above.${NC}"
    exit 1
fi
