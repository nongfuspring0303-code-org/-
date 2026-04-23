# Member A Stage3A Contract & Gate Sign-off

**Version**: v1.0  
**Date**: 2026-04-23  
**Owner**: Member A

## 1) Scope

This document is the A-side closure evidence for Stage3A:
- replay primary key contract freeze
- replay/join validation contract freeze
- Gate-to-execution boundary consistency

Stage3A implementation owner is Member C, while contract/gate closure owner is Member A.

## 2) A-side Contract Decisions

### 2.1 Replay join required keys (frozen)

`REPLAY_JOIN_REQUIRED_KEYS` must be:
- `event_trace_id`
- `request_id`
- `batch_id`
- `event_hash`

No key may be removed or renamed without A/B/C joint review.

### 2.2 Event hash fallback policy (frozen)

When upstream does not provide `event_hash`, runtime may synthesize `EVH-*` hash to keep joinability.
This is compatibility behavior, not a replacement for upstream canonical IDs.

### 2.3 replay_join_validation output contract (frozen)

`replay_join_validation` must contain at least:
- `required_keys`
- `missing_required_keys`
- `replay_primary_key_complete`
- `replay_primary_key_completeness_ratio`
- `orphan_replay_count`
- `execution_emit_expected`
- `execution_joinable_to_replay`
- `orphan_execution_count`
- `replay_write_ok`
- `validation_status`

## 3) Gate/Execution Boundary Decisions

### 3.1 tradeable=false boundary

If `tradeable=false`, output gate must block execution path:
- no `EXECUTE` final action
- no new `execution_emit` record
- replay evidence and join validation still recorded

### 3.2 Idempotency boundary

For same `request_id`, runtime must return `DUPLICATE_IGNORED` on retry and must not duplicate:
- replay writes
- execution emits

## 4) Rules -> Tests Mapping (A-side closure)

| Rule ID | Rule Statement | Test Anchor |
| --- | --- | --- |
| R-A-S3A-001 | Replay required key set is frozen to 4 keys and exact names. | `tests/test_member_a_stage3a_contract_signoff.py::test_stage3a_a_required_keys_contract_frozen` |
| R-A-S3A-002 | `tradeable=false` cannot reach execute path and must keep replay/join evidence. | `tests/test_member_a_stage3a_contract_signoff.py::test_stage3a_a_tradeable_false_blocks_execute_and_keeps_join_evidence` |
| R-A-S3A-003 | Retry with same `request_id` must not duplicate replay/execution records. | `tests/test_member_c_stage3a_replay_join_integrity.py::test_stage3a_retry_same_request_id_no_duplicate_replay_or_execution` |
| R-A-S3A-004 | Replay/join validator must expose primary-key completeness and orphan visibility. | `tests/test_member_c_stage3a_replay_join_integrity.py::test_stage3a_replay_primary_keys_complete_without_input_event_hash` |
| R-A-S3A-005 | Replay write failure must be visible as orphan replay evidence. | `tests/test_member_c_stage3a_replay_join_integrity.py::test_stage3a_reports_orphan_replay_when_replay_write_fails` |

## 5) A-side Sign-off Criteria

Member A may sign off Stage3A only when:
- contract decisions in Section 2 are reflected in runtime,
- boundary decisions in Section 3 are protected by tests,
- rule-to-test anchors in Section 4 are green.
