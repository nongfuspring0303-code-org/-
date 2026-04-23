import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from market_data_adapter import MarketDataAdapter


def test_market_data_adapter_batch_cache_and_failover():
    # Rule ID: R-S4-001/R-S4-002/R-S4-003
    calls = {"primary": 0, "fallback": 0}

    def primary_provider(symbols):
        calls["primary"] += 1
        # primary only serves AAPL; TSLA must failover
        return {"AAPL": 190.0} if "AAPL" in symbols else {}

    def fallback_provider(symbols):
        calls["fallback"] += 1
        out = {}
        if "TSLA" in symbols:
            out["TSLA"] = 240.5
        return out

    now = {"ts": 1_000.0}

    def now_fn():
        return now["ts"]

    cfg = {
        "runtime.price_fetch.cache_ttl_seconds": 120,
        "runtime.price_fetch.max_batch_size": 2,
        "runtime.price_fetch.providers.active": ["primary"],
        "runtime.price_fetch.providers.fallback": ["fallback"],
        "runtime.price_fetch.providers.deprecated": [],
    }

    adapter = MarketDataAdapter(
        config_getter=lambda k, d=None: cfg.get(k, d),
        providers={"primary": primary_provider, "fallback": fallback_provider},
        now_fn=now_fn,
    )

    # first call: primary + fallback
    out1 = adapter.quote_many(["AAPL", "TSLA"])
    assert out1["AAPL"] == 190.0
    assert out1["TSLA"] == 240.5
    assert calls["primary"] == 1
    assert calls["fallback"] == 1
    assert adapter.last_meta.succeeded == ["primary", "fallback"]

    # second call within ttl: served from cache
    now["ts"] += 30
    out2 = adapter.quote_many(["AAPL", "TSLA"])
    assert out2 == out1
    assert calls["primary"] == 1
    assert calls["fallback"] == 1
    assert adapter.last_meta.from_cache == 2

    # expire cache -> providers called again
    now["ts"] += 200
    out3 = adapter.quote_many(["AAPL", "TSLA"])
    assert out3 == out1
    assert calls["primary"] == 2
    assert calls["fallback"] == 2
