#!/usr/bin/env bash
# Prep a fresh OpsScout worktree (typically created by claude-squad) so it
# can run the test suite immediately. Run from inside the worktree.
#
# What it does:
#   1. Sanity-checks we're in an opsscout worktree (models.py + pytest.ini)
#   2. Creates .venv via Python 3.11 if missing
#   3. Installs runtime + dev deps + the tdd-guard-pytest reporter
#   4. Patches pytest.ini's tdd_guard_project_root to the worktree's
#      absolute path AND tells git to skip-worktree on it so the change
#      stays local
#   5. Prints the env vars to export
#
# Usage:
#   cd ~/.cs/<branch-worktree>
#   bash /path/to/opsscout/tools/cs-prep-worktree.sh
#
# Or, if you copied this into a fresh worktree's tools/ dir:
#   bash tools/cs-prep-worktree.sh
#
# Idempotent — safe to re-run.

set -euo pipefail

WORKTREE="$(pwd -P)"
PYTHON_BIN="${PYTHON_BIN:-/Users/rizal/.local/bin/python3.11}"
VLLM_URL="${AMD_VLLM_BASE_URL_DEFAULT:-http://localhost:8001/v1}"
DB_URL="${DATABASE_URL_DEFAULT:-postgresql:///opsscout}"

say() { printf '\033[1;36m→\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m⚠\033[0m %s\n' "$*"; }
ok() { printf '\033[1;32m✓\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m✗\033[0m %s\n' "$*" >&2; exit 1; }

# 1. Sanity check
[ -f "$WORKTREE/models.py" ] || fail "models.py not found — run from an opsscout worktree root"
[ -f "$WORKTREE/pytest.ini" ] || fail "pytest.ini not found — wrong directory"
[ -f "$WORKTREE/requirements.txt" ] || fail "requirements.txt not found — wrong directory"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "not a git worktree"

ok "Worktree: $WORKTREE"

# 2. venv
if [ ! -d "$WORKTREE/.venv" ]; then
    [ -x "$PYTHON_BIN" ] || fail "python 3.11 not found at $PYTHON_BIN — set PYTHON_BIN=/path/to/python3.11"
    say "Creating .venv with $PYTHON_BIN"
    "$PYTHON_BIN" -m venv "$WORKTREE/.venv"
else
    ok ".venv already exists"
fi

PIP="$WORKTREE/.venv/bin/pip"
PY="$WORKTREE/.venv/bin/python"

# 3. deps
say "Upgrading pip"
"$PIP" install --quiet --upgrade pip

say "Installing requirements.txt"
"$PIP" install --quiet -r "$WORKTREE/requirements.txt"

say "Installing dev/test extras (tdd-guard-pytest, psycopg[binary])"
"$PIP" install --quiet "tdd-guard-pytest==0.1.2" "psycopg[binary]==3.2.3"

# Sanity import
"$PY" -c "import pydantic, pytest, openai; print('  pydantic', pydantic.VERSION, '| pytest', pytest.__version__, '| openai', openai.__version__)"

# 4. patch pytest.ini for THIS worktree's path, then mark skip-worktree
# Use sed in-place; macOS sed needs '' after -i
say "Patching pytest.ini → tdd_guard_project_root = $WORKTREE"
if grep -q '^tdd_guard_project_root' "$WORKTREE/pytest.ini"; then
    sed -i '' "s|^tdd_guard_project_root = .*|tdd_guard_project_root = $WORKTREE|" "$WORKTREE/pytest.ini"
else
    # Insert after [pytest] line
    sed -i '' "/^\[pytest\]/a\\
tdd_guard_project_root = $WORKTREE
" "$WORKTREE/pytest.ini"
fi

# Tell git to ignore future changes to pytest.ini in this worktree only
if ! git ls-files --error-unmatch pytest.ini >/dev/null 2>&1; then
    warn "pytest.ini not tracked by git — skip-worktree skipped"
else
    git update-index --skip-worktree pytest.ini || true
    ok "pytest.ini marked skip-worktree (your local path won't pollute commits)"
fi

# 5. quick smoke
say "Running fast tests (excluding live + postgres markers)"
if "$WORKTREE/.venv/bin/pytest" -q -m "not live and not postgres" >/tmp/cs-prep-pytest.log 2>&1; then
    ok "fast tests pass — $(tail -1 /tmp/cs-prep-pytest.log)"
else
    warn "fast tests failed — see /tmp/cs-prep-pytest.log"
fi

cat <<EOF

──────────────────────────────────────────────────────────────────────
${WORKTREE} is ready.

Add these to your shell to run the full test suite (postgres + live):

  export AMD_VLLM_BASE_URL=$VLLM_URL
  export DATABASE_URL=$DB_URL

Then:

  source .venv/bin/activate
  pytest -m "not live"          # postgres-marked, skips if DB unreachable
  pytest -m live                # live-marked, skips without AMD_VLLM_BASE_URL

Slice plan: docs/plans/slice-N-*.md
──────────────────────────────────────────────────────────────────────
EOF
