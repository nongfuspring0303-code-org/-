# PR95 Rule-Test Mapping

Head: 1b7acb5 (provider_untrusted gate hardening split from PR94)

## R-A-S2-ProviderTrustGate
- Rule statement: when `provider_untrusted=true`, output gate must block `EXECUTE`.
- Code anchor: `scripts/workflow_runner.py::_evaluate_output_gate` (`provider_untrusted` blocker).
- Test ID: `T-C-S2-ProviderUntrusted-Block`
- Test anchor: `tests/test_member_c_stage2_blocker_evidence.py::test_stage2_c_provider_untrusted_is_blocked_by_output_gate`
- Assertion summary: final action is non-`EXECUTE`; `decision_gate.output_gate.blockers` includes `provider_untrusted`.

## R-C-S2-DecisionGateEvidence
- Rule statement: blocker path must retain structured gate evidence in `decision_gate.jsonl`.
- Code anchor: `scripts/workflow_runner.py::_log_decision_gate`.
- Test ID: `T-C-S2-DecisionGate-BlockerEvidence`
- Test anchor: `tests/test_member_c_stage2_blocker_evidence.py::test_stage2_c_decision_gate_has_blocker_evidence`
- Assertion summary: blocker event persists request/batch/event_hash and gate blockers in decision gate log.
