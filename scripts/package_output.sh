#!/usr/bin/env bash
set -euo pipefail
JOBDIR="$1"
OUT="/workspace/downloads/$(basename "$JOBDIR").zip"
cd "$JOBDIR/project"
zip -r "$OUT" .
echo "$OUT"
