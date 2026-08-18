#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "install.py"


class InstallTests(unittest.TestCase):
    def test_dry_run(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(INSTALL), "--dry-run"],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))

    def test_isolated_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp) / "home"
            dest = Path(tmp) / "unslop"
            env = os.environ.copy()
            env["HOME"] = str(fake_home)
            env["UNSLOP_HOME"] = str(dest)
            proc = subprocess.run(
                [sys.executable, str(INSTALL)],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))
            settings = json.loads((fake_home / ".claude" / "settings.json").read_text())
            blob = json.dumps(settings)
            self.assertIn("unslop.py", blob)
            self.assertIn("UserPromptSubmit", settings["hooks"])
            self.assertIn("PreToolUse", settings["hooks"])
            self.assertIn("Stop", settings["hooks"])
            self.assertTrue((fake_home / ".grok" / "rules" / "unslop.md").is_file())
            self.assertTrue((fake_home / ".claude" / "skills" / "unslop").is_symlink())
            self.assertIn("unslop:start", (fake_home / ".claude" / "CLAUDE.md").read_text())
            proc = subprocess.run(
                [sys.executable, str(INSTALL), "--uninstall"],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))
            after = json.loads((fake_home / ".claude" / "settings.json").read_text())
            self.assertNotIn("unslop.py", json.dumps(after))


if __name__ == "__main__":
    unittest.main()
