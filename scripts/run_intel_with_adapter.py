#!/usr/bin/env python3
"""
Run intel pipeline with DataAdapter payload.
"""

from __future__ import annotations

import json

from data_adapter import DataAdapter
from intel_modules import IntelPipeline


def _num_or_default(value, default=0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def main() -> None:
    payload = DataAdapter().fetch()
    news = payload["news"]
    market = payload["market_data"]

    intel_input = {
        "headline": news["headline"],
        "source": news["source_url"],
        "timestamp": news["timestamp"],
        "vix": _num_or_default(market.get("vix_level"), 0),
        "vix_change_pct": _num_or_default(market.get("vix_change_pct"), 0),
        "spx_move_pct": _num_or_default(market.get("spx_change_pct"), 0),
        "sector_move_pct": _num_or_default(market.get("etf_volatility", {}).get("change_pct"), 0),
        "sequence": 1,
    }
    out = IntelPipeline().run(intel_input)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
