import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from realtime_news_monitor import RealtimeNewsMonitor


def test_worker_node_skips_main_chain_push(monkeypatch):
    monitor = RealtimeNewsMonitor()
    monitor.node_role = "worker"

    called = {"value": False}

    def boom(*args, **kwargs):  # pragma: no cover - should not be reached
        called["value"] = True
        raise AssertionError("urlopen should not be called for worker nodes")

    monkeypatch.setattr("urllib.request.urlopen", boom)

    monitor._push_sectors_to_c({"analysis": {}, "intel": {}})

    assert called["value"] is False
