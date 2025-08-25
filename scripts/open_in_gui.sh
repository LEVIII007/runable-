#!/bin/bash

# Script to open generated code files in GUI applications
# Usage: ./open_in_gui.sh <file_path> [editor]

set -e

FILE_PATH="$1"
EDITOR="${2:-gedit}"

if [ -z "$FILE_PATH" ]; then
    echo "Usage: $0 <file_path> [editor]"
    echo "Available editors: gedit, vim, nano"
    exit 1
fi

if [ ! -f "$FILE_PATH" ]; then
    echo "❌ File not found: $FILE_PATH"
    exit 1
fi

echo "🖥️ Opening $FILE_PATH in $EDITOR..."

# Ensure we have a display
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0
fi

# Open file in the specified GUI editor
case "$EDITOR" in
    "gedit")
        if command -v gedit >/dev/null 2>&1; then
            DISPLAY=:0 gedit "$FILE_PATH" &
            echo "✅ Opened $FILE_PATH in gedit"
        else
            echo "❌ gedit not available, falling back to vim"
            DISPLAY=:0 xterm -e vim "$FILE_PATH" &
        fi
        ;;
    "vim"|"vi")
        DISPLAY=:0 xterm -e vim "$FILE_PATH" &
        echo "✅ Opened $FILE_PATH in vim (terminal)"
        ;;
    "nano")
        DISPLAY=:0 xterm -e nano "$FILE_PATH" &
        echo "✅ Opened $FILE_PATH in nano (terminal)"
        ;;
    *)
        echo "❌ Unknown editor: $EDITOR"
        echo "Available editors: gedit, vim, nano"
        exit 1
        ;;
esac

echo "💡 File is now visible in the VNC desktop at http://localhost:6080"
echo "🔐 VNC Password: ${VNC_PW:-vncpassword}" 