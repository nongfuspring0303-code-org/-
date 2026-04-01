#!/usr/bin/env python3
"""
Approximate coverage runner using Python stdlib trace.
"""

from __future__ import annotations

import ast
import sys
import trace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"

import run_analysis_interface_checks
import run_analysis_layer_integration
import run_analysis_layer_tests


TARGETS = {
    str((ROOT / "scripts" / "lifecycle_manager.py").resolve()),
    str((ROOT / "scripts" / "fatigue_calculator.py").resolve()),
    str((ROOT / "scripts" / "conduction_mapper.py").resolve()),
    str((ROOT / "scripts" / "market_validator.py").resolve()),
    str((ROOT / "scripts" / "signal_scorer.py").resolve()),
}


def _is_main_guard(node: ast.If) -> bool:
    test = node.test
    return (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == "__name__"
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.Eq)
        and len(test.comparators) == 1
        and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value == "__main__"
    )


def executable_line_set(path: Path) -> set[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    lines: set[int] = set()

    def visit(node: ast.AST) -> None:
        if isinstance(node, ast.If) and _is_main_guard(node):
            return
        if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant) and isinstance(node.value.value, str):
            return
        if isinstance(node, ast.stmt) and hasattr(node, "lineno"):
            lines.add(node.lineno)
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(tree)
    return lines


def main() -> int:
    tracer = trace.Trace(count=True, trace=False)
    tracer.runfunc(run_analysis_layer_tests.main)
    tracer.runfunc(run_analysis_layer_integration.main)
    tracer.runfunc(run_analysis_interface_checks.main)

    results = tracer.results()
    total_exec = 0
    total_hit = 0

    covered_by_file = {}
    for (path, lineno), _count in results.counts.items():
        normalized = str(Path(path).resolve())
        covered_by_file.setdefault(normalized, set()).add(lineno)

    print("Analysis-layer approximate coverage:")
    for normalized in sorted(TARGETS):
        file_path = Path(normalized)
        exec_line_numbers = executable_line_set(file_path)
        exec_lines = len(exec_line_numbers)
        hit_lines = len(exec_line_numbers & covered_by_file.get(normalized, set()))
        pct = 0.0 if exec_lines == 0 else (hit_lines / exec_lines) * 100
        total_exec += exec_lines
        total_hit += hit_lines
        print(f"- {file_path.name}: {hit_lines}/{exec_lines} ({pct:.1f}%)")

    total_pct = 0.0 if total_exec == 0 else (total_hit / total_exec) * 100
    print(f"TOTAL {total_hit}/{total_exec} ({total_pct:.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
