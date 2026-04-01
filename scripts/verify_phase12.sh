#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[verify_phase12] running intel and phase1 smoke tests"
python3 -m pytest -q tests/test_intel_modules.py tests/test_config_center.py

echo "[verify_phase12] passed"
