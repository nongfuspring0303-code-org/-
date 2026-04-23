# Member B Stage4 Consumption Validation
**Version**: v1.0  
**Date**: 2026-04-24  
**Role**: Member B review / sign-off for Stage4 consumption-side validation  
**Scope**: Consumer impact only after Stage4 provider/batch/cache/failover/queue improvements

## 1) Purpose and boundary

This document defines B-side validation scope for Stage4 outputs after C-side provider and performance changes.

- B validates consumer-side stability and quality.
- B does not own Stage4 provider/queue/perf implementation.

Out-of-scope implementation ownership:

- `MarketDataAdapter`
- batch price fetch
- cache internals
- provider failover internals
- queue/idempotency core implementation
- performance benchmark implementation

## 2) Validation objects

- `sector_candidates`
- `ticker_candidates`
- `A1` (consumed as score signal context)
- `theme_tags`

## 3) Validation dimensions

### 3.1 Field presence

- Required fields must remain present in consumer-facing records.

### 3.2 Type stability

- `sector_candidates` / `ticker_candidates` / `theme_tags` stay as list.
- `A1` stays readable numeric context (`a1_score` in gate summary, `A1` in execution input context).

### 3.3 Null/empty rate

- Null/empty leakage for required consumer fields must not regress unexpectedly.

### 3.4 fallback/default_used ratio

- `market_data_default_used` / `market_data_fallback_used` remain observable.
- Ratio changes can happen for runtime reasons, but semantics must remain interpretable.

### 3.5 manual review ratio

- `WATCH` / `PENDING_CONFIRM` / `BLOCK` paths remain distinguishable from `EXECUTE`.
- Consumer must still be able to explain why a record requires review.

### 3.6 Output quality non-regression

- Provider optimization must not silently break B mapping consumption:
  - fields still readable
  - semantics still interpretable
  - no hidden collapse into unusable placeholders

## 4) Evidence sources for PR88

- C-side Stage4 implementation and gate tests:
  - `tests/test_market_data_adapter.py`
  - `tests/test_member_c_stage4_provider_perf.py`
- B-side Stage4 consumption fixture and validation tests:
  - `tests/fixtures/edt_goldens/member_b_stage4_consumption_cases.json`
  - `tests/test_member_b_stage4_consumption_validation.py`

## 5) Sign-off template

> B-side sign-off: PASS / PASS WITH NOTE / FAIL  
> Date: YYYY-MM-DD  
> PR: #<number>  
> Evidence: fixture cases + validation test output + risk notes

