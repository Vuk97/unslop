#!/usr/bin/env python3
"""Lint prose for Unslop violations. Does not fetch anything."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from unslop_lib import lint  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path)
    parser.add_argument("--text")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--high-only", action="store_true")
    args = parser.parse_args()
    if args.file and args.text is not None:
        print("use --file or --text, not both", file=sys.stderr)
        return 2
    if args.file:
        text = args.file.read_text(encoding="utf-8")
    elif args.text is not None:
        text = args.text
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        print("pass --file, --text, or stdin", file=sys.stderr)
        return 2
    report = lint(text)
    if args.high_only:
        report.hits = report.high
    if args.json:
        json.dump(report.as_dict(), sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(report.summary())
        for hit in report.hits:
            print(f"  {hit.severity:6} {hit.rule:24} x{hit.count}  {hit.excerpt}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
