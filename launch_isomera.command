#!/bin/zsh
set -u

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR" || exit 1

LOG_DIR="$SCRIPT_DIR/main/logs"
mkdir -p "$LOG_DIR"
SESSION_LOG="$LOG_DIR/isomera_launcher_$(date +%Y%m%d_%H%M%S).log"
touch "$SESSION_LOG"
exec > >(tee -a "$SESSION_LOG") 2>&1

clear
echo "Opening Isomera v3 package..."
echo "Full launcher log: $SESSION_LOG"
echo
echo "Launcher starting. Diagnostics will appear below."
echo "Startup progress and diagnostics will appear here; expected maximum wait is about 90 seconds."
echo

if command -v python3.11 >/dev/null 2>&1; then
  LAUNCHER_PYTHON="$(command -v python3.11)"
elif [[ -x "/opt/homebrew/bin/python3.11" ]]; then
  LAUNCHER_PYTHON="/opt/homebrew/bin/python3.11"
else
  LAUNCHER_PYTHON="$(command -v python3)"
fi
LAUNCHER_SCRIPT="main/scripts/launch_isomera_macos.py"

if [[ -z "$LAUNCHER_PYTHON" ]]; then
  echo "Python 3.11+ is required to run the Isomera launcher."
  echo "Install Python 3.11, then try again. Full launcher log: $SESSION_LOG"
  read
  exit 1
fi

"$LAUNCHER_PYTHON" -u "$LAUNCHER_SCRIPT"
STATUS=$?

echo
if [[ "$STATUS" -ne 0 ]]; then
  if [[ "$STATUS" -eq 130 ]]; then
    echo "Startup was interrupted by the user; no recovery retry will be started."
    read
    exit "$STATUS"
  fi
  if [[ "$STATUS" -eq 2 ]]; then
    echo "Startup paused because the local Python environment could not be prepared."
    echo "Check whether Python 3.11 is available and review the full log. The launcher does not download a venv from iCloud."
    echo "No database startup, app launch, or process cleanup was attempted. Full log: $SESSION_LOG"
    read
    exit "$STATUS"
  fi
  echo "Isomera did not start (exit code $STATUS). Full log: $SESSION_LOG"
  echo "Recovery options: [T] retry startup once, [Q] quit. Unrelated processes will not be terminated."
  if ! read -r "RECOVERY_CHOICE?Choose T or Q [T]: "; then
    RECOVERY_CHOICE="q"
  fi
  RECOVERY_CHOICE="${RECOVERY_CHOICE:-T}"
  if [[ "${RECOVERY_CHOICE:l}" == "t" ]]; then
    echo "Starting one retry..."
    "$LAUNCHER_PYTHON" -u "$LAUNCHER_SCRIPT"
    RETRY_STATUS=$?
    if [[ "$RETRY_STATUS" -ne 0 ]]; then
      echo "Retry failed (exit code $RETRY_STATUS). Full log: $SESSION_LOG"
      echo "Latest child log: ls -t main/logs/streamlit_launch_*.log | head -1"
      read
    fi
    exit "$RETRY_STATUS"
  fi
  echo "Retry cancelled. Full log: $SESSION_LOG"
  read
fi
exit "$STATUS"
