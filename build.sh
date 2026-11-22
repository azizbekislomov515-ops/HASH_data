#!/usr/bin/env bash
# Build a native Linux binary. Windows releases must be built on Windows.
set -euo pipefail

case "${1:-}" in
    ""|--onedir) export HASHFORGE_ONEFILE=0 ;;
    --onefile) export HASHFORGE_ONEFILE=1 ;;
    *) echo "Usage: bash build.sh [--onedir|--onefile]" >&2; exit 2 ;;
esac
if [[ $# -gt 1 ]]; then
    echo "Usage: bash build.sh [--onedir|--onefile]" >&2
    exit 2
fi

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ "$(uname -s)" != Linux ]]; then
    echo "This script builds on Linux. Use build.bat on Windows." >&2
    exit 1
fi
if [[ ! -f main.py ]]; then
    echo "Missing application entry point: main.py" >&2
    exit 1
fi

python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else "Python 3.11+ is required.")'
python3 -m venv .venv-build
.venv-build/bin/python -m pip install -r requirements.txt
export QT_QPA_PLATFORM=offscreen
.venv-build/bin/python -m pytest
.venv-build/bin/python -m PyInstaller --noconfirm --clean hashforge.spec

if [[ "$HASHFORGE_ONEFILE" == 1 ]]; then
    echo "Built Linux executable: dist/HashForge"
else
    echo "Built Linux application: dist/HashForge/HashForge"
fi
