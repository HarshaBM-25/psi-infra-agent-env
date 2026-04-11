#!/usr/bin/env bash
set -uo pipefail
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
PING_URL="${1:-}"; REPO_DIR="${2:-.}"
if [ -z "$PING_URL" ]; then echo "Usage: $0 <ping_url> [repo_dir]"; exit 1; fi
REPO_DIR="$(cd "$REPO_DIR" && pwd)"; PING_URL="${PING_URL%/}"; PASS=0
log()  { printf "[%s] %b\n" "$(date -u +%H:%M:%S)" "$*"; }
pass() { log "${GREEN}PASSED${NC} -- $1"; PASS=$((PASS + 1)); }
fail() { log "${RED}FAILED${NC} -- $1"; }
stop_at() { printf "\n${RED}${BOLD}Stopped at %s. Fix above before continuing.${NC}\n" "$1"; exit 1; }
printf "\n${BOLD}========================================${NC}\n"
printf "${BOLD}  OpenEnv Submission Validator${NC}\n"
printf "${BOLD}========================================${NC}\n"
log "Repo: $REPO_DIR"; log "Ping URL: $PING_URL"; printf "\n"
log "${BOLD}Step 1/3: Pinging HF Space${NC} ..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{}' "$PING_URL/reset" --max-time 30 || echo "000")
if [ "$HTTP_CODE" = "200" ]; then pass "HF Space is live and responds to /reset"
else fail "HF Space /reset returned HTTP $HTTP_CODE (expected 200)"; stop_at "Step 1"; fi
log "${BOLD}Step 2/3: Running docker build${NC} ..."
if [ -f "$REPO_DIR/Dockerfile" ]; then DOCKER_CONTEXT="$REPO_DIR"; else fail "No Dockerfile found"; stop_at "Step 2"; fi
docker build "$DOCKER_CONTEXT" > /dev/null 2>&1 && pass "Docker build succeeded" || { fail "Docker build failed"; stop_at "Step 2"; }
log "${BOLD}Step 3/3: Running openenv validate${NC} ..."
command -v openenv &>/dev/null || { fail "openenv not found. Run: pip install openenv-core"; stop_at "Step 3"; }
cd "$REPO_DIR" && openenv validate > /dev/null 2>&1 && pass "openenv validate passed" || { fail "openenv validate failed"; stop_at "Step 3"; }
printf "\n${GREEN}${BOLD}All 3/3 checks passed! Ready to submit.${NC}\n\n"
