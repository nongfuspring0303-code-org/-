import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from data_adapter import DataAdapter


def test_data_adapter_fetch():
    data = DataAdapter().fetch()
    assert "news" in data
    assert "market_data" in data
    assert "headline" in data["news"]
    assert "vix_level" in data["market_data"]
    assert "sector_data" in data
    assert isinstance(data["sector_data"], list)
    assert data["market_data"].get("is_test_data") is True


def test_data_adapter_health_report_records_snapshots(tmp_path):
    adapter = DataAdapter(audit_dir=str(tmp_path))
    adapter.fetch()
    adapter.fetch()

    report = adapter.health_report()
    assert report["total_fetches"] >= 2
    assert "live_news_count" in report
    assert "fallback_news_count" in report
    assert (tmp_path / "data_health.jsonl").exists()
    assert (tmp_path / "data_health_summary.json").exists()
