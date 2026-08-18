#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
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
        out = proc.stdout.decode("utf-8")
        self.assertIn("Skill copied to", out)
        self.assertIn("Always-on contract written to", out)

    def test_isolated_home_installs_skill_and_always_on(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp) / "home"
            dest = Path(tmp) / "unslop"
            env = os.environ.copy()
            env["HOME"] = str(fake_home)
            env["UNSLOP_HOME"] = str(dest)
            env["UNSLOP_INSTALL_OPTIONAL"] = "1"
            proc = subprocess.run(
                [sys.executable, str(INSTALL)],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))

            for rel in (
                Path(".claude") / "skills" / "unslop" / "SKILL.md",
                Path(".codex") / "skills" / "unslop" / "SKILL.md",
                Path(".grok") / "skills" / "unslop" / "SKILL.md",
                Path(".agents") / "skills" / "unslop" / "SKILL.md",
                Path(".cursor") / "skills" / "unslop" / "SKILL.md",
                Path("Library") / "Application Support" / "Claude" / "skills" / "unslop" / "SKILL.md",
            ):
                path = fake_home / rel
                self.assertTrue(path.is_file(), path)

            zpath = dest / "unslop.zip"
            self.assertTrue(zpath.is_file())
            with zipfile.ZipFile(zpath) as zf:
                names = zf.namelist()
            self.assertIn("unslop/SKILL.md", names)
            self.assertIn("unslop/ALWAYS_ON.md", names)

            claude_md = (fake_home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("unslop:start", claude_md)
            self.assertIn("Do not fetch", claude_md)
            self.assertIn("Do not open a URL", claude_md)
            agents = (fake_home / ".codex" / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("Do not fetch", agents)
            grok_rule = (fake_home / ".grok" / "rules" / "unslop.md").read_text(encoding="utf-8")
            self.assertIn("Do not fetch", grok_rule)
            grok_agents = (fake_home / ".grok" / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("Do not fetch", grok_agents)

            settings = json.loads((fake_home / ".claude" / "settings.json").read_text())
            self.assertIn("unslop.py", json.dumps(settings))

            proc = subprocess.run(
                [sys.executable, str(INSTALL), "--verify"],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout.decode("utf-8") + proc.stderr.decode("utf-8"))

            proc = subprocess.run(
                [sys.executable, str(INSTALL), "--uninstall"],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))
            self.assertFalse((fake_home / ".claude" / "skills" / "unslop").exists())
            after = json.loads((fake_home / ".claude" / "settings.json").read_text())
            self.assertNotIn("unslop.py", json.dumps(after))
            self.assertNotIn("unslop:start", (fake_home / ".claude" / "CLAUDE.md").read_text())


if __name__ == "__main__":
    unittest.main()
