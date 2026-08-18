#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skill" / "unslop" / "scripts"))
from unslop_lib import lint, scrub_dashes, wrap_prompt, SENTINEL  # noqa: E402


class LintTests(unittest.TestCase):
    def test_em_dash_is_high(self) -> None:
        report = lint("This is fine — except it is not.")
        self.assertFalse(report.ok)
        self.assertTrue(any(h.rule == "em_dash" for h in report.high))

    def test_en_dash_is_high(self) -> None:
        report = lint("See pages 10–20 for details.")
        self.assertTrue(any(h.rule == "en_dash" for h in report.hits))

    def test_code_fence_dashes_ignored(self) -> None:
        report = lint("Use this:\n```\nfoo — bar\n```\nThen run the tests.")
        self.assertTrue(report.ok)

    def test_inline_code_dashes_ignored(self) -> None:
        report = lint("The flag is `foo—bar`.")
        self.assertTrue(report.ok)

    def test_chatbot_opener(self) -> None:
        report = lint("Great question. The server sends an ack.")
        self.assertTrue(any(h.rule == "great_question" for h in report.high))

    def test_lets_dive(self) -> None:
        report = lint("Let's dive in and look at the logs.")
        self.assertTrue(any(h.rule == "lets_dive" for h in report.high))

    def test_clean_prose(self) -> None:
        report = lint("To delete the document, click **Delete**.")
        self.assertTrue(report.ok)

    def test_scrub_em_dash(self) -> None:
        out = scrub_dashes("This is fine — except it is not.")
        self.assertNotIn("\u2014", out)
        self.assertIn(" - ", out)

    def test_scrub_preserves_code(self) -> None:
        src = "See `a—b` and keep it."
        self.assertIn("a—b", scrub_dashes(src))

    def test_wrap_prompt_appends_once(self) -> None:
        once = wrap_prompt("Find the retry limit.")
        self.assertIn(SENTINEL, once)
        twice = wrap_prompt(once)
        self.assertEqual(once.count(SENTINEL), twice.count(SENTINEL))


if __name__ == "__main__":
    unittest.main()
