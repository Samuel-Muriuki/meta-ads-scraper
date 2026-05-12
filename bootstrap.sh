#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# Meta Ads Scraper — Bootstrap Script
# Run this ONCE after cloning/unzipping.
# It is idempotent — safe to re-run.
# ─────────────────────────────────────────────────────────────────

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}━━━ Meta Ads Scraper Bootstrap ━━━${NC}"
echo ""

# ─── Step 1: Verify Python version ────────────────────────────────
echo -e "${YELLOW}[1/9]${NC} Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo -e "${RED}ERROR: Python 3.11+ required, found $PYTHON_VERSION${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION"

# ─── Step 2: Set git author (interactive, skip if already configured) ──
echo -e "${YELLOW}[2/9]${NC} Checking git author configuration..."

CURRENT_NAME=$(git config user.name 2>/dev/null || echo "")
CURRENT_EMAIL=$(git config user.email 2>/dev/null || echo "")

if [ -z "$CURRENT_NAME" ] || [ -z "$CURRENT_EMAIL" ]; then
    echo -e "${YELLOW}Git author identity not set for this repository.${NC}"
    echo -e "${YELLOW}Please enter your git author details (these will be used for commits):${NC}"

    read -p "Your name: " GIT_USER_NAME
    read -p "Your email: " GIT_USER_EMAIL

    if [ -z "$GIT_USER_NAME" ] || [ -z "$GIT_USER_EMAIL" ]; then
        echo -e "${RED}Error: Both name and email are required.${NC}"
        exit 1
    fi

    git config user.name "$GIT_USER_NAME"
    git config user.email "$GIT_USER_EMAIL"
    echo -e "${GREEN}✓${NC} Git author set to $GIT_USER_NAME <$GIT_USER_EMAIL>"
else
    echo -e "${GREEN}✓${NC} Git author already configured: $CURRENT_NAME <$CURRENT_EMAIL>"
fi

# ─── Step 3: Initialize git if needed ─────────────────────────────
echo -e "${YELLOW}[3/9]${NC} Verifying git repository..."
if [ ! -d ".git" ]; then
    git init
    git checkout -b main
    git commit --allow-empty -m "🎉 chore(repo): initialize repository"
    git checkout -b develop
    echo -e "${GREEN}✓${NC} Initialized fresh git repo with main + develop branches"
else
    echo -e "${GREEN}✓${NC} Git repo exists"
fi

# ─── Step 4: Create virtualenv ────────────────────────────────────
echo -e "${YELLOW}[4/9]${NC} Creating virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
echo -e "${GREEN}✓${NC} Virtualenv activated"

# ─── Step 5: Upgrade pip ──────────────────────────────────────────
echo -e "${YELLOW}[5/9]${NC} Upgrading pip..."
pip install --upgrade pip --quiet
echo -e "${GREEN}✓${NC} pip upgraded"

# ─── Step 6: Install package + dev deps ───────────────────────────
echo -e "${YELLOW}[6/9]${NC} Installing dependencies..."
pip install -e ".[dev]" --quiet
echo -e "${GREEN}✓${NC} Dependencies installed"

# ─── Step 7: Install Playwright browsers ──────────────────────────
echo -e "${YELLOW}[7/9]${NC} Installing Playwright Chromium..."
playwright install chromium --with-deps 2>/dev/null || playwright install chromium
echo -e "${GREEN}✓${NC} Playwright Chromium ready"

# ─── Step 8: Verify linting ───────────────────────────────────────
echo -e "${YELLOW}[8/9]${NC} Running ruff check..."
if ruff check src/ tests/ 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Lint clean"
else
    echo -e "${YELLOW}⚠${NC}  Lint issues found (expected before code is written)"
fi

# ─── Step 9: Run tests ────────────────────────────────────────────
echo -e "${YELLOW}[9/9]${NC} Running pytest..."
if pytest --no-cov -q 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Tests passed"
else
    echo -e "${YELLOW}⚠${NC}  No tests yet (expected on first bootstrap)"
fi

echo ""
echo -e "${GREEN}━━━ Bootstrap Complete ━━━${NC}"
echo ""
echo "Next steps:"
echo "  1. Activate the venv:   source .venv/bin/activate"
echo "  2. Read BUILD-PLAN.md for the phase prompts"
echo "  3. Begin Phase 0"
echo ""
