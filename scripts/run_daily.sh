#!/usr/bin/env bash
# Unattended daily run (macOS / Linux). Called by cron - see README "Scheduling".
# Same locked-down permissions as run_daily.ps1: read, run the checker, write to output/ only.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p output/logs
LOG="output/logs/$(date +%F).log"

# Deterministic checks first: stop if the inputs are broken (exit 2 = input error, see INPUT_ERROR.md)
if ! python3 scripts/run_checks.py >> "$LOG" 2>&1; then
  python3 scripts/build_dashboard.py >> "$LOG" 2>&1
  exit 2
fi

# Claude step, stopped after 15 minutes (coreutils timeout); see run_daily.ps1 for the retrying Windows version
timeout 900 claude -p "Run the solar job exceptions check. Follow SKILL.md in this folder exactly. This is an unattended scheduled run: do not ask questions; put anything uncertain under Needs human review." \
  --permission-mode dontAsk \
  --allowedTools "Read" "Glob" "Grep" "Bash(python3 scripts/run_checks.py:*)" "Bash(python scripts/run_checks.py:*)" \
                 "Edit(./output/**)" \
  >> "$LOG" 2>&1 || echo "Claude step failed or timed out" >> "$LOG"
python3 scripts/build_dashboard.py >> "$LOG" 2>&1
