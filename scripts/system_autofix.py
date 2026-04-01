#!/usr/bin/env python3
"""
Low-risk auto-fix entrypoint for project health.

Scope is intentionally narrow:
- create missing runtime directories
- repair UTF-8 config loading in edt_module_base.py
- switch workflow_runner.py to the formal signal_scorer import
"""

from __future__ import annotations

import argparse
import json
import py_compile
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"
REPORT_PATH = LOGS_DIR / "system_autofix_report.json"
DOCS_DIR = ROOT / "docs"

STANDARD_DOC_TEMPLATE = """# System Health Standard

> 恢复模板：若正式说明缺失，可由自动修复恢复最小版本。  
> 主入口：`python scripts/system_healthcheck.py`
"""

MANUAL_DOC_TEMPLATE = """# System Health Manual

> 恢复模板：若正式说明缺失，可由自动修复恢复最小版本。  
> 日常入口：
>
> `python scripts/system_healthcheck.py`
> `python scripts/system_autofix.py --apply`
"""


@dataclass
class FixAction:
    name: str
    changed: bool
    status: str
    details: str


def apply_replacement(path: Path, old: str, new: str, apply: bool) -> FixAction:
    content = path.read_text(encoding="utf-8")
    if new in content:
        return FixAction(path.name, False, "SKIP", "Target content already present.")
    if old not in content:
        return FixAction(path.name, False, "SKIP", "Expected source pattern not found.")
    if apply:
        path.write_text(content.replace(old, new), encoding="utf-8")
        return FixAction(path.name, True, "FIXED", "Patched file.")
    return FixAction(path.name, True, "PLAN", "Patch available but not applied.")


def ensure_runtime_dirs(apply: bool) -> FixAction:
    target = LOGS_DIR
    docs_target = DOCS_DIR
    if target.exists() and docs_target.exists():
        return FixAction("runtime_dirs", False, "SKIP", "Logs and docs directories already exist.")
    if apply:
        target.mkdir(parents=True, exist_ok=True)
        docs_target.mkdir(parents=True, exist_ok=True)
        return FixAction("runtime_dirs", True, "FIXED", "Created required runtime directories.")
    return FixAction("runtime_dirs", True, "PLAN", "Would create required runtime directories.")


def fix_utf8_loader(apply: bool) -> FixAction:
    path = ROOT / "scripts" / "edt_module_base.py"
    old = "            with open(config_path, 'r') as f:\n"
    new = "            with open(config_path, 'r', encoding='utf-8') as f:\n"
    return apply_replacement(path, old, new, apply)


def fix_signal_scorer_import(apply: bool) -> list[FixAction]:
    path = ROOT / "scripts" / "workflow_runner.py"
    actions = [
        apply_replacement(
            path,
            "from edt_module_base import ModuleStatus, SignalScorer\n",
            "from edt_module_base import ModuleStatus\nfrom signal_scorer import SignalScorer\n",
            apply,
        )
    ]
    return actions


def ensure_doc_file(path: Path, template: str, apply: bool) -> FixAction:
    if path.exists() and path.stat().st_size > 0:
        return FixAction(path.name, False, "SKIP", "Documentation file already exists.")
    if apply:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(template, encoding="utf-8")
        return FixAction(path.name, True, "FIXED", "Restored missing documentation file.")
    return FixAction(path.name, True, "PLAN", "Would restore missing documentation file.")


def check_script_compile(path: Path) -> FixAction:
    try:
        py_compile.compile(str(path), doraise=True)
        return FixAction(path.name, False, "OK", "Script compiles successfully.")
    except Exception as exc:  # noqa: BLE001
        return FixAction(path.name, False, "WARN", f"Script compile failed: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply low-risk automatic fixes for both the health system and the project.")
    parser.add_argument("--apply", action="store_true", help="Write changes instead of dry-run planning.")
    parser.add_argument("--self-only", action="store_true", help="Only repair health-system files and metadata.")
    args = parser.parse_args()

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    actions: list[FixAction] = [
        ensure_runtime_dirs(args.apply),
        ensure_doc_file(DOCS_DIR / "system_health_standard.md", STANDARD_DOC_TEMPLATE, args.apply),
        ensure_doc_file(DOCS_DIR / "system_health_manual.md", MANUAL_DOC_TEMPLATE, args.apply),
    ]
    if not args.self_only:
        actions.extend(
            [
                fix_utf8_loader(args.apply),
                *fix_signal_scorer_import(args.apply),
            ]
        )
    actions.extend(
        [
            check_script_compile(ROOT / "scripts" / "system_healthcheck.py"),
            check_script_compile(ROOT / "scripts" / "system_autofix.py"),
        ]
    )

    report = {
        "mode": "apply" if args.apply else "dry-run",
        "self_only": args.self_only,
        "actions": [asdict(item) for item in actions],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"MODE: {'apply' if args.apply else 'dry-run'}")
    for item in actions:
        print(f"[{item.status}] {item.name}: {item.details}")
    print(f"REPORT: {REPORT_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
