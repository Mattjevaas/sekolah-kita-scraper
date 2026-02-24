#!/usr/bin/env bash

set -e

echo "=================================================="
echo "  Building Sekolah Kita Scraper for macOS/Linux"
echo "=================================================="
echo

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found."
    exit 1
fi

echo "[1/4] Creating virtual environment..."
VENV_DIR="venv_build"
if [ -d "$VENV_DIR" ]; then
    rm -rf "$VENV_DIR"
fi
python3 -m venv "$VENV_DIR"

echo "[2/4] Activating venv and installing requirements..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

echo
echo "[3/4] Building executable with PyInstaller..."
# --onefile: bundle everything into a single binary
# --console: show console window (needed for TUI)
# --name: output filename
# --clean: clean cache

# Set cache dir to local to avoid permission issues in some environments
export PYINSTALLER_CONFIG_DIR="$(pwd)/.pyinstaller_cache"

pyinstaller --noconfirm --onefile --console --clean --name "sekolah-kita-scraper" "scrape_sekolah_kita.py"

echo
echo "[4/4] Cleaning up..."
deactivate
# Optional: Remove build artifacts
# rm -rf build
# rm -rf "$VENV_DIR"
# rm -f sekolah-kita-scraper.spec
# rm -rf .pyinstaller_cache

echo
echo "=================================================="
echo "  Build Success!"
echo "=================================================="
echo "The executable is located at:"
echo "  dist/sekolah-kita-scraper"
echo
echo "You can copy this binary to any compatible macOS/Linux machine."
