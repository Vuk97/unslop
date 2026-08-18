#!/usr/bin/env python3
"""Install Unslop: skill, always-on rules, and force-hooks."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

SKILL_NAME = "unslop"
SENTINEL_START = "<!-- unslop:start -->"
SENTINEL_END = "<!-- unslop:end -->"
HOOK_MARK = "unslop.py"
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


def always_on_block(body: str) -> str:
    return f"{SENTINEL_START}\n{body.strip()}\n{SENTINEL_END}\n"


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


def remove_path(path: Path, dry_run: bool) -> None:
    if not (path.exists() or path.is_symlink()):
        return
    if dry_run:
        print(f"remove {path}")
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)


def skill_roots() -> list[Path]:
    roots = [
        home() / ".claude" / "skills",
        home() / ".codex" / "skills",
        home() / ".grok" / "skills",
        home() / ".agents" / "skills",
    ]
    cursor = home() / ".cursor"
    if cursor.is_dir() or os.environ.get("UNSLOP_INSTALL_OPTIONAL") == "1":
        roots.append(home() / ".cursor" / "skills")
    claude_app = home() / "Library" / "Application Support" / "Claude"
    if claude_app.is_dir() or os.environ.get("UNSLOP_INSTALL_OPTIONAL") == "1":
        roots.append(claude_app / "skills")
    extra = os.environ.get("UNSLOP_SKILL_ROOTS", "").strip()
    if extra:
        roots.extend(Path(p).expanduser() for p in extra.split(os.pathsep) if p)
    return roots


def always_on_files() -> list[Path]:
    return [
        home() / ".claude" / "CLAUDE.md",
        home() / ".codex" / "AGENTS.md",
        home() / ".grok" / "AGENTS.md",
    ]


def always_on_rules() -> list[Path]:
    return [
        home() / ".claude" / "rules" / f"{SKILL_NAME}.md",
        home() / ".grok" / "rules" / f"{SKILL_NAME}.md",
    ]


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


def write_skill_zip(skill_dir: Path, zip_path: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"zip {skill_dir} -> {zip_path}")
        return
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in skill_dir.rglob("*"):
            if path.is_file():
                zf.write(path, Path(SKILL_NAME) / path.relative_to(skill_dir))


def skill_description(skill_dir: Path) -> str:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    if "description:" not in text:
        return "Always-on clear English for every reply."
    after = text.split("description:", 1)[1]
    if after.lstrip().startswith(">"):
        lines = []
        for line in after.splitlines()[1:]:
            if line.startswith("---"):
                break
            lines.append(line.strip())
        return " ".join(lines).strip()
    return after.splitlines()[0].strip()


def desktop_plugin_roots() -> list[Path]:
    extra = os.environ.get("UNSLOP_DESKTOP_SKILLS_PLUGIN", "").strip()
    if extra:
        return [Path(extra).expanduser()]
    root = (
        home()
        / "Library"
        / "Application Support"
        / "Claude"
        / "local-agent-mode-sessions"
        / "skills-plugin"
    )
    if not root.is_dir():
        return []
    return [path.parent for path in root.rglob("manifest.json")]


def upsert_desktop_manifest(manifest_path: Path, description: str, dry_run: bool) -> None:
    data: dict = {"skills": []}
    if manifest_path.is_file():
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data.setdefault("skills", [])
    skills = [s for s in data["skills"] if s.get("skillId") != SKILL_NAME and s.get("name") != SKILL_NAME]
    skills.append(
        {
            "skillId": SKILL_NAME,
            "name": SKILL_NAME,
            "description": description,
            "creatorType": "user",
            "updatedAt": None,
            "enabled": True,
        }
    )
    data["skills"] = skills
    write_text(manifest_path, json.dumps(data, indent=2, ensure_ascii=True) + "\n", dry_run)


def strip_desktop_manifest(manifest_path: Path, dry_run: bool) -> None:
    if not manifest_path.is_file():
        return
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    skills = data.get("skills", [])
    filtered = [s for s in skills if s.get("skillId") != SKILL_NAME and s.get("name") != SKILL_NAME]
    if filtered == skills:
        return
    data["skills"] = filtered
    write_text(manifest_path, json.dumps(data, indent=2, ensure_ascii=True) + "\n", dry_run)


def install_desktop_skill(skill_src: Path, dry_run: bool) -> list[Path]:
    description = skill_description(skill_src)
    installed: list[Path] = []
    for plugin_root in desktop_plugin_roots():
        skills_dir = plugin_root / "skills"
        copy_tree(skill_src, skills_dir / SKILL_NAME, dry_run)
        upsert_desktop_manifest(plugin_root / "manifest.json", description, dry_run)
        installed.append(skills_dir / SKILL_NAME)
    return installed


def enable_skill_plugin(settings_path: Path, dry_run: bool) -> None:
    data: dict = {}
    if settings_path.is_file():
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    plugins = data.setdefault("enabledPlugins", {})
    plugins[f"{SKILL_NAME}@skills-dir"] = True
    write_text(settings_path, json.dumps(data, indent=2, ensure_ascii=True) + "\n", dry_run)


def disable_skill_plugin(settings_path: Path, dry_run: bool) -> None:
    if not settings_path.is_file():
        return
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    plugins = data.get("enabledPlugins", {})
    key = f"{SKILL_NAME}@skills-dir"
    if key not in plugins:
        return
    plugins.pop(key, None)
    data["enabledPlugins"] = plugins
    write_text(settings_path, json.dumps(data, indent=2, ensure_ascii=True) + "\n", dry_run)


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
    zip_dest = dest / "unslop.zip"
    copy_tree(skill_src, skill_dest, dry_run)
    if dry_run:
        print(f"copy {hook_src} -> {hook_dest}")
    else:
        hook_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(hook_src, hook_dest)
        hook_dest.chmod(0o755)
        shutil.copy2(skill_dest / "ALWAYS_ON.md", hook_dest.parent / "ALWAYS_ON.md")
    write_skill_zip(skill_src if dry_run else skill_dest, zip_dest, dry_run)

    for skills_root in skill_roots():
        copy_tree(skill_src if dry_run else skill_dest, skills_root / SKILL_NAME, dry_run)
    desktop_paths = install_desktop_skill(skill_src if dry_run else skill_dest, dry_run)

    merge_claude_settings(home() / ".claude" / "settings.json", hook_dest, dry_run)
    enable_skill_plugin(home() / ".claude" / "settings.json", dry_run)
    merge_codex_hooks(home() / ".codex" / "hooks.json", hook_dest, dry_run)
    write_grok_hook(home() / ".grok" / "hooks" / "unslop.json", hook_dest, dry_run)

    always_on = (skill_src if dry_run else skill_dest).joinpath("ALWAYS_ON.md")
    rule_body = always_on.read_text(encoding="utf-8")
    block = always_on_block(rule_body)
    for path in always_on_rules():
        write_text(path, rule_body if rule_body.endswith("\n") else rule_body + "\n", dry_run)
    for path in always_on_files():
        replace_or_append_sentinel(path, block, dry_run)

    print(f"Installed to {dest}")
    print()
    print("Skill auto-installed to:")
    for skills_root in skill_roots():
        print(f"  {skills_root / SKILL_NAME}")
    for path in desktop_paths:
        print(f"  {path}  (Claude Desktop, enabled)")
    print(f"  zip (claude.ai account upload if Desktop list does not sync): {zip_dest}")
    print()
    print("Always-on contract written to:")
    for path in always_on_rules() + always_on_files():
        print(f"  {path}")
    print()
    print("Hooks written for Claude Code, Codex, and Grok.")
    print("Claude Desktop: Unslop is registered and enabled in the local skill list.")
    print("claude.ai web: if the skill is missing, upload the zip once.")
    print("Codex: run /hooks and trust unslop.py once.")
    print("Restart Claude / Codex / Grok so they reload.")
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
    remove_path(home() / ".grok" / "hooks" / "unslop.json", dry_run)
    for path in always_on_rules():
        remove_path(path, dry_run)
    for skills_root in skill_roots():
        remove_path(skills_root / SKILL_NAME, dry_run)
    for plugin_root in desktop_plugin_roots():
        remove_path(plugin_root / "skills" / SKILL_NAME, dry_run)
        strip_desktop_manifest(plugin_root / "manifest.json", dry_run)
    disable_skill_plugin(home() / ".claude" / "settings.json", dry_run)
    for path in always_on_files():
        remove_sentinel(path, dry_run)
    if dest.exists():
        remove_path(dest, dry_run)
    print("Uninstalled Unslop.")
    return 0


def verify() -> int:
    dest = install_home()
    missing = []
    skill_md = dest / "skill" / SKILL_NAME / "SKILL.md"
    if not skill_md.is_file():
        missing.append(str(skill_md))
    for skills_root in skill_roots():
        path = skills_root / SKILL_NAME / "SKILL.md"
        if not path.is_file():
            missing.append(str(path))
    for path in always_on_rules():
        if not path.is_file() or "Do not fetch" not in path.read_text(encoding="utf-8"):
            missing.append(str(path))
    for path in always_on_files():
        if not path.is_file() or SENTINEL_START not in path.read_text(encoding="utf-8"):
            missing.append(str(path))
    zip_path = dest / "unslop.zip"
    if not zip_path.is_file():
        missing.append(str(zip_path))
    for plugin_root in desktop_plugin_roots():
        if not (plugin_root / "skills" / SKILL_NAME / "SKILL.md").is_file():
            missing.append(str(plugin_root / "skills" / SKILL_NAME / "SKILL.md"))
    if missing:
        print("NOT installed:")
        for path in missing:
            print(f"  {path}")
        return 1
    print("Unslop skill + always-on + zip are present.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        return verify()
    if args.uninstall:
        return uninstall(args.dry_run)
    return install(args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
