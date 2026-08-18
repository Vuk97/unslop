# Unslop

Force Claude, Codex, and Grok to write Google developer-docs English instead of chatbot padding.

The skill is a local digest. Agents do not open https://developers.google.com/style. Hooks inject a short on-disk contract before every reply, wrap every subagent brief, and bounce sloppy returns.

## Why a skill alone is not enough

Skills are optional. Models skip them. That is how you get em dashes, `Great question`, and `Let's dive in` after you already asked for clean prose.

Unslop has three layers:

1. **Local contract.** `skill/unslop/ALWAYS_ON.md` is the whole turn rule. No link to follow.
2. **Force hooks.** Claude and Codex inject that file on `UserPromptSubmit`, `SessionStart`, and `SubagentStart`.
3. **Subagent wrap and bounce.** `PreToolUse` on `Task` / `Agent` / `spawn_subagent` / `spawn_agent` scrubs long dashes and appends a child contract. `PostToolUse` flags a sloppy child. `Stop` / `SubagentStop` bounce a high-severity final message once.

Grok ignores `UserPromptSubmit` stdout. Grok still gets the contract as a home rule (`~/.grok/rules/unslop.md`) and the child wrap on `spawn_subagent`.

## Install

```bash
git clone https://github.com/Vuk97/unslop
cd unslop
./install.sh
```

Then:

- Restart Claude Code (CLI or Desktop), Codex (CLI or Desktop), and Grok.
- In Codex, run `/hooks` and trust `unslop.py`.

`./install.sh --dry-run` prints the plan. `./uninstall.sh` removes the wiring.

## What install changes

| Surface | What happens |
| --- | --- |
| `~/.claude/settings.json` | Hooks on prompt, session, Task/Agent, stop |
| `~/.codex/hooks.json` | Same events for Codex CLI and Desktop |
| `~/.grok/hooks/unslop.json` | Child wrap plus stop bounce |
| `~/.grok/rules/unslop.md` | Always-on parent contract for Grok |
| `~/.claude/rules/unslop.md` | Same file for Claude/Grok rule loaders |
| `~/.../skills/unslop` | Symlink of the skill into Claude, Codex, Grok, Agents |
| `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md` | Short fallback if a hook is not trusted yet |

Existing hooks stay. Unslop adds groups. It does not replace yours.

## Test

```bash
python3 -m unittest discover -s tests -v
python3 skill/unslop/scripts/lint.py --text "Great question. Ship it."
```

The linter should exit 1 on that sample. A clean sentence exits 0.

How to test it yourself after install:

1. Ask Claude or Codex: `Explain how to delete a file in one sentence.`
2. If the reply has an em dash or `Great question`, the Stop hook missed. Check `/hooks`.
3. Ask it to spawn a subagent. Open the child brief. You should see `<!-- unslop:subagent-contract -->` and no em dash.

## Why not ASD-STE100

STE100 restricts vocabulary for translation. Chat agents then sound like a parts catalog. Unslop keeps natural English and bans chatbot padding. Google developer documentation style is the source digest. The house rule that beats Google: no em dashes. That mark is how you spot Claude-lish.

## Files

```
skill/unslop/ALWAYS_ON.md     Turn contract (injected)
skill/unslop/SKILL.md         Procedure. Points at local files only
skill/unslop/scripts/         Linter and shared library
skill/unslop/references/      Loaded only when ALWAYS_ON is not enough
hooks/unslop.py               One hook for every host
```

## License

Code is Apache-2.0. The style digest is adapted from the
[Google developer documentation style guide](https://developers.google.com/style),
CC BY 4.0. See [NOTICE](NOTICE).
