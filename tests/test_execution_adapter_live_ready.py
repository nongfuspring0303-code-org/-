import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from execution_adapter import ExecutionAdapter


def _base_order(request_id: str = "REQ-BASE-1"):
    return {
        "request_id": request_id,
        "action": "OPEN_LONG",
        "symbol": "AAPL",
        "notional": 10000,
        "entry_price": 100.0,
        "stop_loss": 98.0,
        "take_profit_levels": [101.0, 102.0, 103.0],
    }


def test_execution_adapter_paper_accepts_order(tmp_path):
    adapter = ExecutionAdapter(mode="paper", audit_dir=str(tmp_path))
    out = adapter.execute(_base_order())
    assert out["mode"] == "paper"
    assert out["status"] == "accepted"
    assert out["broker_order_id"].startswith("PAPER-")


def test_execution_adapter_blocks_duplicate_request_id(tmp_path):
    adapter = ExecutionAdapter(mode="paper", audit_dir=str(tmp_path))
    first = adapter.execute(_base_order("REQ-DUP-1"))
    second = adapter.execute(_base_order("REQ-DUP-1"))
    assert first["status"] == "accepted"
    assert second["status"] == "duplicate_ignored"


def test_execution_adapter_blocks_concurrent_duplicate_request_id(tmp_path, monkeypatch):
    adapter = ExecutionAdapter(mode="paper", audit_dir=str(tmp_path))
    original_place_order = adapter.broker.place_order

    def slow_place_order(order):
        time.sleep(0.2)
        return original_place_order(order)

    monkeypatch.setattr(adapter.broker, "place_order", slow_place_order)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(adapter.execute, _base_order("REQ-CONCURRENT-1")) for _ in range(2)]
        results = [future.result() for future in futures]

    statuses = sorted(result["status"] for result in results)
    assert statuses == ["accepted", "duplicate_ignored"]


def test_execution_adapter_blocks_by_risk_limit(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        """
modules:
  ExecutionAdapter:
    params:
      risk_controls:
        max_notional_per_order: 1000
        max_daily_notional: 5000
        max_open_orders: 5
        blocked_symbols: ["TSLA"]
""".strip(),
        encoding="utf-8",
    )

    adapter = ExecutionAdapter(mode="paper", audit_dir=str(tmp_path), config_path=str(cfg))
    out = adapter.execute(_base_order("REQ-RISK-1"))
    assert out["status"] == "blocked_by_risk"
    assert "max_notional_per_order" in out["reason"]


def test_execution_adapter_rejects_non_finite_numeric_fields(tmp_path):
    adapter = ExecutionAdapter(mode="paper", audit_dir=str(tmp_path))
    order = _base_order("REQ-NAN-1")
    order["notional"] = float("nan")
    out = adapter.execute(order)
    assert out["status"] == "blocked_by_risk"
    assert "finite" in out["reason"]


def test_execution_adapter_live_mode_uses_stub(tmp_path):
    adapter = ExecutionAdapter(mode="live", audit_dir=str(tmp_path))
    out = adapter.execute(_base_order("REQ-LIVE-STUB"))
    assert out["mode"] == "live"
    assert out["status"] == "not_implemented"
