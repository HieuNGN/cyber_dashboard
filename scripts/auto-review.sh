#!/usr/bin/env bash
# ponytail: minimal auto-review+upgrade runner. One bash script, one cron line.
# Runs tests, lets opencode review+upgrade the code, commits to `auto-review` branch.
set -euo pipefail

REPO="/home/amd-rig/projs/cybersec_dashboard_server"
BRANCH="auto-review"
BASE="master"
LOG_DIR="$REPO/logs"
TS="$(date +%Y%m%d-%H%M%S)"
LOG="$LOG_DIR/auto-review-$TS.log"
CONDA_ENV="cyberdashboard"
OPENCODE="/home/amd-rig/.opencode/bin/opencode"
export PATH="/home/amd-rig/miniconda3/bin:$PATH"

mkdir -p "$LOG_DIR"
cd "$REPO"

{
  echo "=== $(date -Is) auto-review start ==="

  # 1. Fetch latest base in case master moved elsewhere.
  git fetch origin "$BASE" 2>&1 || echo "fetch failed (offline?), continuing"

  # 2. Reset auto-review branch to master. Discard previous auto commits each run.
  if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git checkout "$BRANCH" >/dev/null 2>&1
    git reset --hard "$BASE" >/dev/null 2>&1
  else
    git checkout -b "$BRANCH" "$BASE" >/dev/null 2>&1
  fi

  # 3. Tests before opencode — baseline.
  # ponytail: env python is /usr/bin/python (no pytest module); pytest lives in ~/.local.
  # Call pytest binary directly via conda run so it lands on the env's PATH.
  echo "--- pytest baseline ---"
  if conda run -n "$CONDA_ENV" --no-capture-output pytest tests/ -q >/tmp/ar-base.out 2>&1; then
    BASELINE_OK=1
  else
    BASELINE_OK=0
    echo "baseline tests failed; opencode will see this"
  fi
  cat /tmp/ar-base.out

  # 4. opencode review + upgrade. --auto approves tool calls non-interactively.
  # ponytail: one prompt, let opencode do its thing in one shot.
  echo "--- opencode review ---"
  if [ "${DRY_RUN:-0}" = "1" ]; then
    echo "DRY_RUN=1 — skipping opencode"
  else
  "$OPENCODE" run --auto --print-logs --log-level INFO \
    "Review this codebase and apply improvements. First run the test suite (conda run -n cyberdashboard pytest tests/ -q) and fix any failures. Then scan for over-engineering, dead code, and any bugs. Make minimal changes following the conventions in AGENTS.md, CONTEXT.md, and the ponytail skill. Do NOT write to Obsidian Vault, do NOT commit, push, or create a branch — leave changes in the working tree for the runner script to commit. Stop when done." \
    2>&1 || echo "opencode exited non-zero"
  fi

  # 5. Commit anything opencode changed.
  echo "--- git commit ---"
  git add -A
  if git diff --cached --quiet; then
    echo "no changes produced; skipping commit"
  else
    git commit -m "auto: review+upgrade $(date +%Y-%m-%d_%H:%M)" >/dev/null 2>&1
    echo "committed on $BRANCH"
  fi

  # 6. Tests after — confirm we didn't make things worse.
  echo "--- pytest after ---"
  if conda run -n "$CONDA_ENV" --no-capture-output pytest tests/ -q >/tmp/ar-after.out 2>&1; then
    AFTER_OK=1
  else
    AFTER_OK=0
    echo "post-opencode tests failed — review $BRANCH manually"
  fi
  cat /tmp/ar-after.out

  echo "baseline_ok=$BASELINE_OK after_ok=$AFTER_OK"
  echo "=== $(date -Is) auto-review end ==="
} >"$LOG" 2>&1

# Tail last 20 lines to stdout for cron mail if any.
tail -20 "$LOG"