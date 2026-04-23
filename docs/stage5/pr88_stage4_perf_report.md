# PR88 Stage4 Provider/Performance Benchmark Report

- Date: 2026-04-24
- Scope: Stage4 C-side provider adapter + batch/cache/failover performance evidence
- Script: `scripts/bench_stage4_provider_perf.py`
- Artifact: `docs/stage5/artifacts/pr88_stage4_perf_benchmark.json`

## 1) Method

- Baseline model: serial single-symbol fetch (`primary -> fallback`), no batch/cache reuse.
- Stage4 model: `MarketDataAdapter` batch fetch + cache + failover chain.
- Parameters:
  - rounds: 60
  - symbols per round: 40
  - timeout threshold: 10ms per quote operation budget

Command:

```bash
python3 scripts/bench_stage4_provider_perf.py --rounds 60 --symbols 40 --timeout-ms 10
```

## 2) Measured Results

- Baseline
  - throughput: `211.80 qps`
  - P95 latency: `190.63 ms`
  - P99 latency: `192.41 ms`
  - failure_rate: `2.50%`
  - timeout_rate: `0.00%`
- Stage4
  - throughput: `4551.59 qps`
  - P95 latency: `8.89 ms`
  - P99 latency: `8.95 ms`
  - failure_rate: `2.50%`
  - timeout_rate: `0.00%`

## 3) Improvement Summary

- Throughput gain: `+2048.98%` (about `21.49x`)
- P95 latency reduction: `95.34%`
- P99 latency reduction: `95.35%`
- Failure rate reduction: `0.00%` (unchanged under same data availability assumptions)
- Timeout rate reduction: `0.00%` (both 0 in this run)

## 4) Semantics Safety Checks (no regression)

- Stage4 gate tests:
  - `tests/test_member_c_stage4_provider_perf.py::test_dual_write_backward_compat_test`
  - `tests/test_member_c_stage4_provider_perf.py::test_priority_queue_order_semantics_test`
  - `tests/test_member_c_stage4_provider_perf.py::test_idempotent_replay_write_test`
- Provider behavior tests:
  - `tests/test_market_data_adapter.py`
- Config-runtime alignment guard:
  - `tests/test_opportunity_score.py::test_price_fetch_disabled_does_not_call_adapter`

Validation command:

```bash
python3 -m pytest -q \
  tests/test_market_data_adapter.py \
  tests/test_member_c_stage4_provider_perf.py \
  tests/test_opportunity_score.py::test_price_fetch_disabled_does_not_call_adapter
```

Result: `11 passed`

## 5) Conclusion

- Stage4 C-side performance objective is met with clear improvement on throughput and tail latency.
- Queue/idempotency/compatibility checks pass under current test gate.
- No new config-runtime bypass found for `price_fetch.enabled=false` after guard test.
