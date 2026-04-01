#!/usr/bin/env python3
"""
Config center loader (T1.3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


class ConfigCenter:
    """Load and provide typed access to module configs."""

    def __init__(self, config_path: str | None = None):
        base = Path(__file__).resolve().parent.parent
        self.config_path = Path(config_path) if config_path else base / "configs" / "edt-modules-config.yaml"
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        if "modules" not in cfg:
            raise ValueError("Invalid config: missing top-level 'modules'")
        return cfg

    def module_config(self, module_name: str) -> Dict[str, Any]:
        return self.data.get("modules", {}).get(module_name, {})

    def module_enabled(self, module_name: str) -> bool:
        return bool(self.module_config(module_name).get("enabled", False))

    def module_timeout(self, module_name: str, default: int = 60) -> int:
        return int(self.module_config(module_name).get("timeout", default))

    def module_params(self, module_name: str) -> Dict[str, Any]:
        return self.module_config(module_name).get("params", {})

    def validate_required_modules(self, required_modules: list[str]) -> tuple[bool, list[str]]:
        missing = []
        modules = self.data.get("modules", {})
        for name in required_modules:
            if name not in modules:
                missing.append(name)
        return len(missing) == 0, missing


if __name__ == "__main__":
    center = ConfigCenter()
    ok, missing = center.validate_required_modules(
        ["SignalScorer", "LiquidityChecker", "RiskGatekeeper", "PositionSizer", "ExitManager"]
    )
    print("config_path:", center.config_path)
    print("required_modules_ok:", ok)
    if not ok:
        print("missing:", missing)

