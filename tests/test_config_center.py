import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from config_center import ConfigCenter


def test_config_center_loads_modules():
    center = ConfigCenter()
    assert "modules" in center.data
    assert center.module_enabled("SignalScorer") is True


def test_config_center_required_modules():
    center = ConfigCenter()
    ok, missing = center.validate_required_modules(
        ["SignalScorer", "LiquidityChecker", "RiskGatekeeper", "PositionSizer", "ExitManager"]
    )
    assert ok is True
    assert missing == []

