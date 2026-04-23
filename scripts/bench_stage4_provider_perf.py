#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import time
from pathlib import Path
from typing import Dict, List, Tuple

from market_data_adapter import MarketDataAdapter


def _symbols(n: int) -> List[str]:
    return [f"SYM{i:03d}" for i in range(1, n + 1)]


def _percentile(sorted_values: List[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * p
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return sorted_values[lo]
    weight = rank - lo
    return sorted_values[lo] * (1.0 - weight) + sorted_values[hi] * weight


def _fake_primary(symbols: List[str]) -> Dict[str, float]:
    time.sleep(0.003)
    out: Dict[str, float] = {}
    for sym in symbols:
        idx = int(sym[-3:])
        if idx % 5 != 0:
            out[sym] = 100.0 + idx * 0.1
    return out


def _fake_fallback(symbols: List[str]) -> Dict[str, float]:
    time.sleep(0.004)
    out: Dict[str, float] = {}
    for sym in symbols:
        idx = int(sym[-3:])
        if idx % 7 != 0:
            out[sym] = 99.5 + idx * 0.1
    return out


def _baseline_fetch(symbols: List[str], timeout_s: float) -> Tuple[Dict[str, float], int]:
    prices: Dict[str, float] = {}
    timeout_count = 0
    for sym in symbols:
        started = time.perf_counter()
        one = _fake_primary([sym])
        if sym in one:
            prices[sym] = one[sym]
        else:
            two = _fake_fallback([sym])
            if sym in two:
                prices[sym] = two[sym]
        elapsed = time.perf_counter() - started
        if elapsed > timeout_s:
            timeout_count += 1
    return prices, timeout_count


def _build_stage4_adapter() -> MarketDataAdapter:
    cfg = {
        "runtime.price_fetch.cache_ttl_seconds": 120,
        "runtime.price_fetch.max_batch_size": 40,
        "runtime.price_fetch.timeout_seconds": 5,
        "runtime.price_fetch.providers.active": ["primary"],
        "runtime.price_fetch.providers.fallback": ["fallback"],
        "runtime.price_fetch.providers.deprecated": [],
    }
    return MarketDataAdapter(
        config_getter=lambda k, d=None: cfg.get(k, d),
        providers={"primary": _fake_primary, "fallback": _fake_fallback},
    )


def _run_baseline(rounds: int, symbols: List[str], timeout_s: float) -> Dict[str, float]:
    durations_ms: List[float] = []
    failures = 0
    timeouts = 0
    total_quotes = rounds * len(symbols)

    for _ in range(rounds):
        t0 = time.perf_counter()
        fetched, timeout_count = _baseline_fetch(symbols, timeout_s)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        durations_ms.append(elapsed_ms)
        failures += len(symbols) - len(fetched)
        timeouts += timeout_count

    sorted_d = sorted(durations_ms)
    total_seconds = sum(durations_ms) / 1000.0
    return {
        "rounds": rounds,
        "quotes": total_quotes,
        "throughput_qps": total_quotes / max(total_seconds, 1e-9),
        "latency_ms_p95": _percentile(sorted_d, 0.95),
        "latency_ms_p99": _percentile(sorted_d, 0.99),
        "failure_rate": failures / max(total_quotes, 1),
        "timeout_rate": timeouts / max(total_quotes, 1),
        "avg_latency_ms": statistics.mean(durations_ms),
    }


def _run_stage4(rounds: int, symbols: List[str], timeout_s: float) -> Dict[str, float]:
    durations_ms: List[float] = []
    failures = 0
    timeouts = 0
    total_quotes = rounds * len(symbols)

    adapter = _build_stage4_adapter()
    adapter.quote_many(symbols)

    for _ in range(rounds):
        t0 = time.perf_counter()
        fetched = adapter.quote_many(symbols)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        durations_ms.append(elapsed_ms)
        failures += len(symbols) - len(fetched)
        if (elapsed_ms / 1000.0) > timeout_s:
            timeouts += len(symbols)

    sorted_d = sorted(durations_ms)
    total_seconds = sum(durations_ms) / 1000.0
    return {
        "rounds": rounds,
        "quotes": total_quotes,
        "throughput_qps": total_quotes / max(total_seconds, 1e-9),
        "latency_ms_p95": _percentile(sorted_d, 0.95),
        "latency_ms_p99": _percentile(sorted_d, 0.99),
        "failure_rate": failures / max(total_quotes, 1),
        "timeout_rate": timeouts / max(total_quotes, 1),
        "avg_latency_ms": statistics.mean(durations_ms),
    }


def _improvement(base: Dict[str, float], new: Dict[str, float]) -> Dict[str, float]:
    def ratio(b: float, n: float) -> float:
        if b == 0:
            return 0.0
        return (b - n) / b

    return {
        "throughput_gain": 0.0 if base["throughput_qps"] == 0 else (new["throughput_qps"] - base["throughput_qps"]) / base["throughput_qps"],
        "latency_p95_reduction": ratio(base["latency_ms_p95"], new["latency_ms_p95"]),
        "latency_p99_reduction": ratio(base["latency_ms_p99"], new["latency_ms_p99"]),
        "failure_rate_reduction": ratio(base["failure_rate"], new["failure_rate"]),
        "timeout_rate_reduction": ratio(base["timeout_rate"], new["timeout_rate"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage4 provider performance benchmark (baseline vs adapter batch/cache/failover)")
    parser.add_argument("--rounds", type=int, default=60)
    parser.add_argument("--symbols", type=int, default=40)
    parser.add_argument("--timeout-ms", type=float, default=10.0)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/stage5/artifacts/pr88_stage4_perf_benchmark.json"),
    )
    args = parser.parse_args()

    random.seed(42)
    symbols = _symbols(max(1, args.symbols))
    timeout_s = max(0.001, args.timeout_ms / 1000.0)

    baseline = _run_baseline(max(1, args.rounds), symbols, timeout_s)
    stage4 = _run_stage4(max(1, args.rounds), symbols, timeout_s)
    improvements = _improvement(baseline, stage4)

    report = {
        "benchmark": "pr88_stage4_provider_perf",
        "parameters": {
            "rounds": max(1, args.rounds),
            "symbols_per_round": len(symbols),
            "timeout_ms": args.timeout_ms,
            "baseline": "serial single-symbol fetch primary->fallback",
            "stage4": "MarketDataAdapter batch+cache+failover",
        },
        "baseline": baseline,
        "stage4": stage4,
        "improvements": improvements,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
