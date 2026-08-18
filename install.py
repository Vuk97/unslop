#!/usr/bin/env python3
"""Install Unslop: local skill + force-hooks. No network fetch at runtime."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

SKILL_NAME = "unslop"
SENTINEL_START = "<!-- unslop:start -->"
SENTINEL_END = "<!-- unslop:end -->"
HOOK_MARK = "unslop.py"

AGENTS_BLOCK = """<!-- unslop:start -->
## User-facing prose (every reply)

Follow Unslop. The compact contract lives on disk and is injected each turn.
Do not fetch https://developers.google.com/style. If a hook missed, read
the local skill's ALWAYS_ON.md. Same contract for subagent briefs and returns.
<!-- unslop:end -->
"""

SUBAGENT_MATCHER = "Task|Agent|spawn_subagent|spawn_agent"


def repo_root() -> Path:
    return Path(__file__).resolve().parent


def home() -> Path:
    return Path.home()


def install_home() -> Path:
    override = os.environ.get("UNSLOP_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return home() / ".local" / "share" / "unslop"


def python_bin() -> str:
    return sys.executable or "python3"


def copy_tree(src: Path, dest: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"copy {src} -> {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        else:
            shutil.rmtree(dest)
    shutil.copytree(src, dest)


def write_text(path: Path, text: str, dry_run: bool) -> None:
    if dry_run:
        print(f"write {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def replace_or_append_sentinel(path: Path, block: str, dry_run: bool) -> None:
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    if SENTINEL_START in existing and SENTINEL_END in existing:
        before, rest = existing.split(SENTINEL_START, 1)
        _mid, after = rest.split(SENTINEL_END, 1)
        new = before.rstrip() + "\n\n" + block.strip() + "\n" + after.lstrip("\n")
    else:
        new = existing.rstrip() + "\n\n" + block.strip() + "\n" if existing else block
    write_text(path, new if new.endswith("\n") else new + "\n", dry_run)


def remove_sentinel(path: Path, dry_run: bool) -> None:
    if not path.is_file():
        return
    existing = path.read_text(encoding="utf-8")
    if SENTINEL_START not in existing or SENTINEL_END not in existing:
        return
    before, rest = existing.split(SENTINEL_START, 1)
    _mid, after = rest.split(SENTINEL_END, 1)
    new = (before.rstrip() + "\n" + after.lstrip("\n")).strip() + "\n"
    write_text(path, new, dry_run)


def symlink_skill(target: Path, link: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"symlink {link} -> {target}")
        return
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.is_file():
        link.unlink()
    elif link.exists():
        shutil.rmtree(link)
    os.symlink(target, link)


def hook_handler(inject: Path) -> dict:
    return {
        "type": "command",
        "command": f"{python_bin()} {inject}",
        "timeout": 8,
    }


def claude_group(inject: Path, matcher: str | None = None) -> dict:
    group: dict = {"hooks": [hook_handler(inject)]}
    if matcher:
        group["matcher"] = matcher
    return group


def merge_event(hooks: dict, event: str, group: dict) -> None:
    groups = hooks.get(event, [])
    groups = [g for g in groups if HOOK_MARK not in json.dumps(g)]
    groups.insert(0, group)
    hooks[event] = groups


def merge_claude_settings(settings_path: Path, inject: Path, dry_run: bool) -> None:
    data: dict = {}
    if settings_path.is_file():
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    hooks = data.setdefault("hooks", {})
    for event in ("SessionStart", "UserPromptSubmit", "SubagentStart"):
        merge_event(hooks, event, claude_group(inject))
    merge_event(hooks, "PreToolUse", claude_group(inject, SUBAGENT_MATCHER))
    merge_event(hooks, "PostToolUse", claude_group(inject, SUBAGENT_MATCHER))
    for event in ("Stop", "SubagentStop"):
        merge_event(hooks, event, claude_group(inject))
    write_text(settings_path, json.dumps(data, indent=2, ensure_ascii=True) + "\n", dry_run)


def strip_marked(settings_like: dict, dry_run: bool, path: Path) -> None:
    hooks = settings_like.get("hooks", settings_like)
    if not isinstance(hooks, dict):
        return
    changed = False
    for event in list(hooks):
        groups = hooks.get(event)
        if not isinstance(groups, list):
            continue
        filtered = [g for g in groups if HOOK_MARK not in json.dumps(g)]
        if filtered != groups:
            changed = True
            if filtered:
                hooks[event] = filtered
            else:
                hooks.pop(event, None)
    if changed:
        write_text(path, json.dumps(settings_like, indent=2, ensure_ascii=True) + "\n", dry_run)


def merge_codex_hooks(hooks_path: Path, inject: Path, dry_run: bool) -> None:
    data: dict = {"description": "Unslop lifecycle hooks", "hooks": {}}
    if hooks_path.is_file():
        data = json.loads(hooks_path.read_text(encoding="utf-8"))
        data.setdefault("hooks", {})
    handler = {
        **hook_handler(inject),
        "statusMessage": "Unslop",
        "additionalContextLimit": 1600,
    }
    group = {"hooks": [handler]}
    matched = {"hooks": [handler], "matcher": SUBAGENT_MATCHER}
    for event in ("SessionStart", "UserPromptSubmit", "SubagentStart", "Stop", "SubagentStop"):
        merge_event(data["hooks"], event, group)
    merge_event(data["hooks"], "PreToolUse", matched)
    merge_event(data["hooks"], "PostToolUse", matched)
    write_text(hooks_path, json.dumps(data, indent=2, ensure_ascii=True) + "\n", dry_run)


def write_grok_hook(path: Path, inject: Path, dry_run: bool) -> None:
    data = {
        "hooks": {
            "SessionStart": [claude_group(inject)],
            "UserPromptSubmit": [claude_group(inject)],
            "SubagentStart": [claude_group(inject)],
            "PreToolUse": [claude_group(inject, SUBAGENT_MATCHER)],
            "PostToolUse": [claude_group(inject, SUBAGENT_MATCHER)],
            "Stop": [claude_group(inject)],
            "SubagentStop": [claude_group(inject)],
        }
    }
    write_text(path, json.dumps(data, indent=2, ensure_ascii=True) + "\n", dry_run)


def install(dry_run: bool) -> int:
    root = repo_root()
    dest = install_home()
    skill_src = root / "skill" / SKILL_NAME
    hook_src = root / "hooks" / "unslop.py"
    if not skill_src.is_dir() or not hook_src.is_file():
        print("install.py must run from a complete checkout.", file=sys.stderr)
        return 1

    skill_dest = dest / "skill" / SKILL_NAME
    hook_dest = dest / "hooks" / "unslop.py"
    copy_tree(skill_src, skill_dest, dry_run)
    if dry_run:
        print(f"copy {hook_src} -> {hook_dest}")
    else:
        hook_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(hook_src, hook_dest)
        hook_dest.chmod(0o755)
        shutil.copy2(skill_dest / "ALWAYS_ON.md", hook_dest.parent / "ALWAYS_ON.md")

    for skills_root in (
        home() / ".claude" / "skills",
        home() / ".codex" / "skills",
        home() / ".grok" / "skills",
        home() / ".agents" / "skills",
    ):
        symlink_skill(skill_dest, skills_root / SKILL_NAME, dry_run)

    merge_claude_settings(home() / ".claude" / "settings.json", hook_dest, dry_run)
    merge_codex_hooks(home() / ".codex" / "hooks.json", hook_dest, dry_run)
    write_grok_hook(home() / ".grok" / "hooks" / "unslop.json", hook_dest, dry_run)

    always_on = (skill_src if dry_run else skill_dest).joinpath("ALWAYS_ON.md")
    rule_body = always_on.read_text(encoding="utf-8")
    for rules_dir in (home() / ".grok" / "rules", home() / ".claude" / "rules"):
        write_text(rules_dir / f"{SKILL_NAME}.md", rule_body, dry_run)

    replace_or_append_sentinel(home() / ".claude" / "CLAUDE.md", AGENTS_BLOCK, dry_run)
    replace_or_append_sentinel(home() / ".codex" / "AGENTS.md", AGENTS_BLOCK, dry_run)

    print(f"Installed to {dest}")
    print("Claude CLI + Desktop Code: inject, wrap Task/Agent, bounce slop")
    print("Codex CLI + Desktop: inject, wrap spawn_agent, bounce slop")
    print("Grok: home rule + wrap spawn_subagent (UserPromptSubmit stdout is ignored)")
    print()
    print("Codex: run /hooks and trust unslop.py")
    print("Restart Claude / Codex / Grok so hooks reload")
    return 0


def uninstall(dry_run: bool) -> int:
    dest = install_home()
    claude_settings = home() / ".claude" / "settings.json"
    if claude_settings.is_file():
        strip_marked(
            json.loads(claude_settings.read_text(encoding="utf-8")),
            dry_run,
            claude_settings,
        )
    codex_hooks = home() / ".codex" / "hooks.json"
    if codex_hooks.is_file():
        strip_marked(json.loads(codex_hooks.read_text(encoding="utf-8")), dry_run, codex_hooks)
    grok_hook = home() / ".grok" / "hooks" / "unslop.json"
    if grok_hook.exists():
        if dry_run:
            print(f"remove {grok_hook}")
        else:
            grok_hook.unlink()
    for path in (
        home() / ".grok" / "rules" / f"{SKILL_NAME}.md",
        home() / ".claude" / "rules" / f"{SKILL_NAME}.md",
    ):
        if path.is_file():
            if dry_run:
                print(f"remove {path}")
            else:
                path.unlink()
    for skills_root in (
        home() / ".claude" / "skills",
        home() / ".codex" / "skills",
        home() / ".grok" / "skills",
        home() / ".agents" / "skills",
    ):
        link = skills_root / SKILL_NAME
        if link.exists() or link.is_symlink():
            if dry_run:
                print(f"remove {link}")
            elif link.is_symlink() or link.is_file():
                link.unlink()
            else:
                shutil.rmtree(link)
    remove_sentinel(home() / ".claude" / "CLAUDE.md", dry_run)
    remove_sentinel(home() / ".codex" / "AGENTS.md", dry_run)
    if dest.exists():
        if dry_run:
            print(f"remove {dest}")
        else:
            shutil.rmtree(dest)
    print("Uninstalled Unslop.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    if args.uninstall:
        return uninstall(args.dry_run)
    return install(args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
