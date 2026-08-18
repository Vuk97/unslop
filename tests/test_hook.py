#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "unslop.py"
SCRIPTS = ROOT / "skill" / "unslop" / "scripts"
CONTRACT = ROOT / "skill" / "unslop" / "ALWAYS_ON.md"


class HookTests(unittest.TestCase):
    def _run(self, payload: dict) -> tuple[int, dict | None, str]:
        env = os.environ.copy()
        env["UNSLOP_SCRIPTS"] = str(SCRIPTS)
        env["UNSLOP_CONTRACT"] = str(CONTRACT)
        proc = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=env,
        )
        out = proc.stdout.decode("utf-8").strip()
        parsed = json.loads(out) if out else None
        return proc.returncode, parsed, proc.stderr.decode("utf-8")

    def test_user_prompt_injects_local_contract(self) -> None:
        rc, data, err = self._run({"hook_event_name": "UserPromptSubmit", "prompt": "hi"})
        self.assertEqual(rc, 0, err)
        assert data is not None
        ctx = data["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Unslop", ctx)
        self.assertIn("Do not fetch", ctx)
        self.assertNotIn("curl", ctx.lower())

    def test_pretooluse_wraps_task_prompt(self) -> None:
        rc, data, err = self._run(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Task",
                "tool_input": {
                    "description": "Find retries",
                    "prompt": "Please thoroughly investigate this — unpack it.",
                },
            }
        )
        self.assertEqual(rc, 0, err)
        assert data is not None
        prompt = data["hookSpecificOutput"]["updatedInput"]["prompt"]
        self.assertNotIn("\u2014", prompt)
        self.assertIn("unslop:subagent-contract", prompt)

    def test_pretooluse_grok_spawn(self) -> None:
        rc, data, err = self._run(
            {
                "hookEventName": "pre_tool_use",
                "toolName": "spawn_subagent",
                "toolInput": {"prompt": "Map the retry config.", "description": "map retries"},
            }
        )
        self.assertEqual(rc, 0, err)
        assert data is not None
        self.assertIn("unslop:subagent-contract", data["hookSpecificOutput"]["updatedInput"]["prompt"])

    def test_stop_blocks_em_dash(self) -> None:
        rc, data, err = self._run(
            {
                "hook_event_name": "Stop",
                "reason": "end_turn",
                "last_assistant_message": "This is done — ship it.",
            }
        )
        self.assertEqual(rc, 0, err)
        assert data is not None
        self.assertEqual(data["decision"], "block")

    def test_stop_does_not_loop(self) -> None:
        rc, data, err = self._run(
            {
                "hook_event_name": "Stop",
                "reason": "end_turn",
                "stop_hook_active": True,
                "last_assistant_message": "This is done — ship it.",
            }
        )
        self.assertEqual(rc, 0, err)
        self.assertIsNone(data)

    def test_post_tool_flags_child_slop(self) -> None:
        rc, data, err = self._run(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Task",
                "tool_response": "Great question. Let's dive in.",
            }
        )
        self.assertEqual(rc, 0, err)
        assert data is not None
        self.assertIn("failed Unslop", data["hookSpecificOutput"]["additionalContext"])


if __name__ == "__main__":
    unittest.main()
