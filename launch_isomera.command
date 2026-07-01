#!/bin/zsh
set -u

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR" || exit 1

clear
echo "Opening Isomera v2..."
echo
echo "Launcher starting. Diagnostics will appear below."
echo "If this window stays here for more than 10 seconds, close it and run:"
echo "  python3.11 main/scripts/launch_isomera_macos.py --check-only"
echo

if command -v python3.11 >/dev/null 2>&1; then
  python3.11 -u main/scripts/launch_isomera_macos.py
elif [[ -x "/opt/homebrew/bin/python3.11" ]]; then
  /opt/homebrew/bin/python3.11 -u main/scripts/launch_isomera_macos.py
else
  python3 -u main/scripts/launch_isomera_macos.py
fi

STATUS=$?
echo
if [[ "$STATUS" -ne 0 ]]; then
  echo "Isomera did not start. Read the diagnostic above."
  echo "Press ENTER to close this window."
  read
fi
exit "$STATUS"
