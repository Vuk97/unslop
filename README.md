# Unslop

Stops Claude, Codex, and Grok from writing like chatbots.

`./install.sh` installs three things for you:

1. **The skill** on Claude, Codex, and Grok (CLI and desktop).
2. **Always-on rules** so the contract is in context every session.
3. **Hooks** so the main thread, subagents, and outputs stay on voice.

Nothing fetches a URL. The contract is a local file.

## What install does

| Surface | Skill | Always-on | Hooks |
| --- | --- | --- | --- |
| Claude Code (CLI and the Code panel in Desktop) | Copied to `~/.claude/skills/unslop` | `~/.claude/CLAUDE.md` and `~/.claude/rules/unslop.md` | Yes. `~/.claude/settings.json` |
| Codex CLI and Desktop | Copied to `~/.codex/skills/unslop` | `~/.codex/AGENTS.md` | Yes. `~/.codex/hooks.json`. Trust `unslop.py` once in `/hooks` |
| Grok | Copied to `~/.grok/skills/unslop` | `~/.grok/rules/unslop.md` and `~/.grok/AGENTS.md` | Yes. Home rule plus child-brief wrap |
| Claude Desktop Chat / Cowork | Auto-installed into the Desktop skill list and **enabled** | Always-on rules plus the enabled skill | No hook API. Skill is on; hooks are not |
| claude.ai in the browser | Zip at `~/.local/share/unslop/unslop.zip` if the account list does not sync | Upload that zip once, leave Unslop on | No |

`./install.sh` copies the skill. It also registers Unslop as enabled in Claude
Desktop's local skill catalog, so you should not have to zip-upload on Desktop.
claude.ai in a browser is a cloud account list. If the skill is missing there,
upload the zip once.

## Install

```bash
git clone https://github.com/Vuk97/unslop
cd unslop
./install.sh
python3 install.py --verify
```

Restart Claude, Codex, and Grok. Old sessions do not reload hooks, skills, or rules.
In Codex, run `/hooks` and trust `unslop.py`.

`./uninstall.sh` removes the skill copies, always-on blocks, and hooks.
Existing unrelated hooks stay.

Apache-2.0. Style digest from the [Google developer documentation style guide](https://developers.google.com/style), CC BY 4.0. See [NOTICE](NOTICE).
