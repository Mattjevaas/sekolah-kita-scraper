#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ "$#" -eq 0 ]; then
  python3 "scrape_sekolah_kita.py" --tui
else
  python3 "scrape_sekolah_kita.py" "$@"
fi
