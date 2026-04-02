#!/usr/bin/env python3
"""
Phase-2 Deep Health Check (temporary tool).

Purpose:
- Validate governance/rule compliance
- Validate stability
- Validate maintainability
- Validate accuracy
- Validate runtime efficiency

IMPORTANT:
- This is a temporary phase-2 tool.
- Remove it after phase-2 acceptance and handover are complete.
"""

from __future__ import annotations

import argparse
import json
import os
import py_compile
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"
REPORT_PATH = LOGS_DIR / "deep_health_report_phase2.json"

STATUS_ORDER = {"GREEN": 0, "YELLOW": 1, "RED": 2}


@dataclass
class CheckResult:
    name: str
    status: str
    summary: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)


def worst_status(values: list[str]) -> str:
    return max(values, key=lambda item: STATUS_ORDER[item]) if values else "GREEN"


def run_command(args: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output.strip()


def _safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "utf-8"
        print(text.encode(enc, errors="replace").decode(enc, errors="replace"))


def _iter_py_files(base: Path) -> list[Path]:
    files: list[Path] = []
    for path in base.rglob("*.py"):
        if ".pytest_cache" in path.parts or ".pytest_tmp" in path.parts or "__pycache__" in path.parts:
            continue
        files.append(path)
    return files


def check_governance() -> CheckResult:
    result = CheckResult(name="GOVERNANCE", status="GREEN", summary="Governance and rule documents are present.")
    standard = ROOT / "docs" / "system_health_standard.md"
    manual = ROOT / "docs" / "system_health_manual.md"
    protocol_candidates = list(ROOT.glob("*Git版*.md"))
    tasklist_candidates = list(ROOT.glob("*任务清单*.md"))
    required_files = [standard, manual]
    missing = [str(p) for p in required_files if not p.exists()]
    if missing:
        result.status = "RED"
        result.summary = "Required governance/rule documents are missing."
        result.errors.extend(missing)
        return result
    if not protocol_candidates:
        result.status = worst_status([result.status, "YELLOW"])
        result.warnings.append("Cannot locate protocol document matching `*Git版*.md`.")
    if not tasklist_candidates:
        result.status = worst_status([result.status, "YELLOW"])
        result.warnings.append("Cannot locate task list document matching `*任务清单*.md`.")

    standard_text = standard.read_text(encoding="utf-8", errors="replace")
    manual_text = manual.read_text(encoding="utf-8", errors="replace")
    if "system_healthcheck.py" not in standard_text:
        result.status = "YELLOW"
        result.warnings.append("system_health_standard.md does not mention `system_healthcheck.py`.")
    if "system_autofix.py" not in manual_text:
        result.status = worst_status([result.status, "YELLOW"])
        result.warnings.append("system_health_manual.md does not mention `system_autofix.py`.")
    result.evidence.append("required_docs_ok")
    return result


def check_stability() -> CheckResult:
    result = CheckResult(name="STABILITY", status="GREEN", summary="Runtime and compile stability checks passed.")

    py_files = _iter_py_files(ROOT / "scripts") + _iter_py_files(ROOT / "tests")
    compile_failures: list[str] = []
    for f in py_files:
        try:
            py_compile.compile(str(f), doraise=True)
        except Exception as exc:  # noqa: BLE001
            compile_failures.append(f"{f}: {exc}")
    if compile_failures:
        result.status = "RED"
        result.summary = "Python compile check failed."
        result.errors.extend(compile_failures[:20])
        return result
    result.evidence.append(f"compiled_files={len(py_files)}")

    cmd = [sys.executable, "scripts/system_healthcheck.py"]
    code, output = run_command(cmd, ROOT)
    result.commands.append(" ".join(cmd))
    if code != 0:
        result.status = "RED"
        result.summary = "system_healthcheck failed."
        result.errors.append("scripts/system_healthcheck.py returned non-zero.")
        if output:
            result.evidence.append(output.splitlines()[-1])
    else:
        result.evidence.append("system_healthcheck_ok")
    return result


def check_maintainability() -> CheckResult:
    result = CheckResult(name="MAINTAINABILITY", status="GREEN", summary="No critical maintainability anti-patterns detected.")
    files = _iter_py_files(ROOT / "scripts")
    except_exception_count = 0
    utcnow_count = 0
    conflict_marker_hits = 0

    for f in files:
        txt = f.read_text(encoding="utf-8", errors="replace")
        except_exception_count += txt.count("except Exception")
        utcnow_count += txt.count("datetime.utcnow(")
        conflict_marker_hits += txt.count("<<<<<<< ") + txt.count(">>>>>>> ")

    result.evidence.append(f"except_exception_count={except_exception_count}")
    result.evidence.append(f"utcnow_count={utcnow_count}")
    result.evidence.append(f"conflict_marker_hits={conflict_marker_hits}")

    if conflict_marker_hits > 0:
        result.status = "RED"
        result.summary = "Conflict markers detected in source files."
        result.errors.append("Found merge conflict markers in scripts/*.py.")
        return result

    if utcnow_count > 0:
        result.status = worst_status([result.status, "YELLOW"])
        result.warnings.append("Found deprecated datetime.utcnow() usage.")

    if except_exception_count >= 60:
        result.status = "RED"
        result.summary = "Too many broad exception handlers reduce maintainability."
        result.errors.append("Broad `except Exception` handlers >= 60.")
    elif except_exception_count >= 25:
        result.status = worst_status([result.status, "YELLOW"])
        result.warnings.append("Broad `except Exception` handlers are relatively high; consider narrowing.")
    return result


def check_accuracy() -> CheckResult:
    result = CheckResult(name="ACCURACY", status="GREEN", summary="Accuracy-focused regression tests passed.")

    target_tests = [
        "tests/test_intel_modules.py::test_source_ranker_rejects_substring_spoof_domain",
        "tests/test_execution_workflow.py::test_workflow_runner_pending_confirm_then_execute_same_request_id",
        "tests/test_multi_event_arbiter.py::test_multi_event_dedup_normalizes_case_and_trailing_slash",
    ]
    existing_targets = [t for t in target_tests if (ROOT / t.split("::", 1)[0]).exists()]
    if not existing_targets:
        result.status = "YELLOW"
        result.summary = "Accuracy-targeted tests are not present in this branch layout."
        result.warnings.append("Targeted accuracy tests not found; fallback to full pytest is recommended.")
        return result

    cmd = [sys.executable, "-m", "pytest", "-q", *existing_targets]
    code, output = run_command(cmd, ROOT)
    result.commands.append(" ".join(cmd))
    if code != 0:
        result.status = "RED"
        result.summary = "Accuracy-focused tests failed."
        result.errors.append("One or more targeted accuracy tests failed.")
        if output:
            result.evidence.append(output.splitlines()[-1])
    else:
        result.evidence.append(f"targeted_tests_passed={len(existing_targets)}")
    return result


def _benchmark_full_workflow(rounds: int) -> list[float]:
    if str(ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))
    from full_workflow_runner import FullWorkflowRunner  # local import to avoid startup coupling

    payload = {
        "headline": "Fed announces emergency liquidity action after tariff shock",
        "source": "https://www.reuters.com/markets/us/example",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "vix": 28,
        "vix_change_pct": 25,
        "spx_move_pct": 2.2,
        "sector_move_pct": 4.1,
        "sequence": 1,
        "account_equity": 150000,
        "entry_price": 42.5,
        "risk_per_share": 1.5,
        "direction": "long",
    }

    timings: list[float] = []
    for _ in range(rounds):
        runner = FullWorkflowRunner()
        start = time.perf_counter()
        runner.run(payload)
        elapsed_ms = (time.perf_counter() - start) * 1000
        timings.append(elapsed_ms)
    return timings


def check_efficiency(max_avg_ms: float, rounds: int) -> CheckResult:
    result = CheckResult(name="EFFICIENCY", status="GREEN", summary="Runtime efficiency benchmark is within threshold.")
    try:
        timings = _benchmark_full_workflow(rounds=rounds)
    except Exception as exc:  # noqa: BLE001
        result.status = "RED"
        result.summary = "Efficiency benchmark could not run."
        result.errors.append(str(exc))
        return result

    avg_ms = statistics.mean(timings)
    p95_ms = sorted(timings)[max(0, int(len(timings) * 0.95) - 1)]
    result.evidence.append(f"rounds={rounds}")
    result.evidence.append(f"avg_ms={avg_ms:.2f}")
    result.evidence.append(f"p95_ms={p95_ms:.2f}")
    result.evidence.append(f"threshold_avg_ms={max_avg_ms:.2f}")

    if avg_ms > max_avg_ms:
        result.status = "YELLOW"
        result.summary = "Efficiency benchmark exceeds target average latency."
        result.warnings.append(f"avg_ms {avg_ms:.2f} > threshold {max_avg_ms:.2f}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase-2 deep health check (temporary tool).")
    parser.add_argument("--max-avg-ms", type=float, default=1200.0, help="Max acceptable average latency for full workflow benchmark.")
    parser.add_argument("--rounds", type=int, default=3, help="Benchmark rounds.")
    parser.add_argument(
        "--project-complete",
        action="store_true",
        help="Run full deep checks only when the phase-2 project is functionally complete.",
    )
    args = parser.parse_args()

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    checks = [check_governance(), check_maintainability()]
    if args.project_complete:
        checks.extend(
            [
                check_stability(),
                check_accuracy(),
                check_efficiency(max_avg_ms=args.max_avg_ms, rounds=max(1, args.rounds)),
            ]
        )
    else:
        checks.append(
            CheckResult(
                name="RUNTIME_CHECKS",
                status="YELLOW",
                summary="Skipped for preparation stage. Re-run with --project-complete after functional completion.",
            )
        )
    overall = worst_status([c.status for c in checks])

    report = {
        "tool": "deep_healthcheck_phase2",
        "temporary": True,
        "preparation_mode": not args.project_complete,
        "remove_after_phase2_completion": True,
        "overall_status": overall,
        "checks": [asdict(c) for c in checks],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    _safe_print("OVERALL: " + overall)
    _safe_print("NOTE: This is a temporary phase-2 tool. Remove it after phase-2 acceptance.")
    if not args.project_complete:
        _safe_print("NOTE: Preparation mode only. Run again with --project-complete when project is complete.")
    for c in checks:
        _safe_print(f"[{c.status}] {c.name}: {c.summary}")
        for e in c.errors:
            _safe_print(f"  ERROR: {e}")
        for w in c.warnings:
            _safe_print(f"  WARN: {w}")
    _safe_print(f"REPORT: {REPORT_PATH}")
    return 0 if overall == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
