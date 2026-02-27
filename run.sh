#!/usr/bin/env bash

# run.sh – Launch transcode.py in the background, immune to terminal close.
# Usage:
#   chmod +x run.sh
#   ./run.sh            # uses default preset settings
#   HB_PRESET_NAME=MyPreset ./run.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/transcode.log"
PID_FILE="$SCRIPT_DIR/transcode.pid"

if [[ -f "$PID_FILE" ]]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "A transcode session is already running (PID $OLD_PID)."
        echo "To stop it: kill $OLD_PID"
        exit 1
    fi
fi

echo "Starting transcode session. Log: $LOG_FILE"
nohup python3 "$SCRIPT_DIR/transcode.py" >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "Running in background (PID $!). Monitor with:"
echo "  tail -f $LOG_FILE"
