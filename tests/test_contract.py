#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "unslop"
sys.path.insert(0, str(SKILL / "scripts"))
from unslop_lib import lint  # noqa: E402

BANNED_CHARS = ("\u2014", "\u2013")
QUOTE_FILES = {
    "examples.md",
    "slop-patterns.md",
    "word-list.md",
    "google-style.md",
    "subagents.md",
}


class ContractTests(unittest.TestCase):
    def test_no_em_or_en_dashes_in_repo_prose(self) -> None:
        offenders = []
        for path in [ROOT / "README.md", *SKILL.rglob("*.md")]:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            for ch in BANNED_CHARS:
                if ch in text:
                    offenders.append(f"{path.relative_to(ROOT)} U+{ord(ch):04X}")
        self.assertEqual(offenders, [])

    def test_skill_frontmatter(self) -> None:
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("name: unslop", text)
        self.assertIn("Do not fetch", text)

    def test_always_on_forbids_network(self) -> None:
        text = (SKILL / "ALWAYS_ON.md").read_text(encoding="utf-8")
        self.assertIn("Do not open a URL", text)
        self.assertIn("Do not fetch", text)

    def test_always_on_lints_clean(self) -> None:
        text = (SKILL / "ALWAYS_ON.md").read_text(encoding="utf-8")
        report = lint(text)
        self.assertTrue(report.ok, report.summary())

    def test_skill_md_lints_clean(self) -> None:
        report = lint((SKILL / "SKILL.md").read_text(encoding="utf-8"))
        self.assertTrue(report.ok, report.summary())

    def test_readme_lints_clean(self) -> None:
        report = lint((ROOT / "README.md").read_text(encoding="utf-8"))
        high = [h for h in report.hits if h.severity == "high"]
        self.assertEqual(high, [], report.summary())


if __name__ == "__main__":
    unittest.main()
