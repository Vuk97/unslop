#!/usr/bin/env python3
"""Unslop hook for Claude, Codex, and Grok.

Events:
- UserPromptSubmit / SessionStart / SubagentStart: inject ALWAYS_ON.md
- PreToolUse on Task/Agent/spawn_subagent/spawn_agent: scrub dashes and
  append the child contract to the brief
- PostToolUse on those tools: if the child returned slop, tell the parent
- Stop / SubagentStop: bounce a high-severity sloppy final message once

Never fetches the network. Fail-open on unexpected errors.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_CANDIDATES = [
    HERE.parent / "skill" / "unslop" / "scripts",
    Path.home() / ".local" / "share" / "unslop" / "skill" / "unslop" / "scripts",
]


def _load_lib():
    env = os.environ.get("UNSLOP_SCRIPTS", "").strip()
    roots = [Path(env).expanduser()] if env else []
    roots.extend(SCRIPTS_CANDIDATES)
    for root in roots:
        if (root / "unslop_lib.py").is_file():
            sys.path.insert(0, str(root))
            import unslop_lib as lib  # type: ignore

            return lib, root.parent
    raise FileNotFoundError("unslop_lib.py not found; re-run install.sh")


LIB, SKILL_DIR = _load_lib()


def contract_path() -> Path:
    env = os.environ.get("UNSLOP_CONTRACT", "").strip()
    candidates = []
    if env:
        candidates.append(Path(env).expanduser())
    candidates.extend(
        [
            HERE / "ALWAYS_ON.md",
            SKILL_DIR / "ALWAYS_ON.md",
        ]
    )
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError("ALWAYS_ON.md not found; re-run install.sh")


def always_on_text() -> str:
    body = contract_path().read_text(encoding="utf-8").strip()
    skill_md = SKILL_DIR / "SKILL.md"
    return (
        body
        + "\n\nFull skill (local file, do not fetch a URL): "
        + str(skill_md)
        + "\nApply this before any user-facing prose this turn, including "
        + "subagent briefs and anything you quote from a child.\n"
    )


def emit(payload: dict) -> int:
    json.dump(payload, sys.stdout, ensure_ascii=True)
    sys.stdout.write("\n")
    return 0


def inject(event: str) -> int:
    return emit(
        {
            "continue": True,
            "suppressOutput": True,
            "hookSpecificOutput": {
                "hookEventName": event,
                "additionalContext": always_on_text(),
            },
        }
    )


def pre_tool(event: str, payload: dict) -> int:
    name = LIB.tool_name_of(payload)
    if not LIB.is_subagent_tool(name):
        return 0
    original = LIB.tool_input_of(payload)
    updated, changed = LIB.wrap_tool_input(original, str(SKILL_DIR / "SKILL.md"))
    if not changed:
        return 0
    return emit(
        {
            "hookSpecificOutput": {
                "hookEventName": event,
                "permissionDecision": "allow",
                "updatedInput": updated,
            }
        }
    )


def post_tool(event: str, payload: dict) -> int:
    name = LIB.tool_name_of(payload)
    if not LIB.is_subagent_tool(name):
        return 0
    text = LIB.tool_output_text(payload)
    report = LIB.lint(text)
    if not report.high:
        return 0
    note = (
        "The subagent return failed Unslop ("
        + report.summary()
        + "). Rewrite the prose before showing it to the user. "
        "Keep code, paths, and diffs. Do not mention this note."
    )
    return emit(
        {
            "hookSpecificOutput": {
                "hookEventName": event,
                "additionalContext": note,
            }
        }
    )


def stop(event: str, payload: dict) -> int:
    reason = LIB.first_string(payload, "reason")
    if reason and reason not in ("end_turn", "other", ""):
        return 0
    if LIB.stop_already_active(payload):
        return 0
    text = LIB.last_message_of(payload)
    report = LIB.lint(text)
    if not report.high:
        return 0
    feedback = LIB.rewrite_feedback(report)
    # Claude Stop: decision block + reason.
    # Codex Stop: continue false / decision block + additionalContext.
    # Grok Stop: decision block + reason.
    return emit(
        {
            "decision": "block",
            "reason": feedback,
            "hookSpecificOutput": {
                "hookEventName": event,
                "additionalContext": feedback,
            },
        }
    )


def main() -> int:
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    payload: dict = {}
    if raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                payload = parsed
        except json.JSONDecodeError:
            payload = {}
    event = LIB.event_name_of(payload)
    if "--event" in sys.argv:
        idx = sys.argv.index("--event")
        if idx + 1 < len(sys.argv):
            event = LIB.event_name_of({"hook_event_name": sys.argv[idx + 1]})
    if event in {"UserPromptSubmit", "SessionStart", "SubagentStart"}:
        return inject(event)
    if event == "PreToolUse":
        return pre_tool(event, payload)
    if event == "PostToolUse":
        return post_tool(event, payload)
    if event in {"Stop", "SubagentStop"}:
        return stop(event, payload)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"unslop: {exc}", file=sys.stderr)
        raise SystemExit(0)
