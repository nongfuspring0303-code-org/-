#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[verify_fullchain] analysis module tests"
python3 tests/run_analysis_layer_tests.py

echo "[verify_fullchain] analysis interface checks"
python3 tests/run_analysis_interface_checks.py

echo "[verify_fullchain] analysis integration"
python3 tests/run_analysis_layer_integration.py

echo "[verify_fullchain] execution + e2e regression"
python3 -m pytest -q tests/test_execution_workflow.py tests/test_e2e_workflow.py tests/test_e2e_regression.py

echo "[verify_fullchain] passed"
