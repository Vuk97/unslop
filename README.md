# Unslop: clear technical English for agent output

Coding agents pad replies with chatbot filler, long dashes, and fake
structure. Unslop is a writing skill plus hooks that make the **main thread**,
**subagents**, and **their outputs** speak like a person writing technical docs:
direct, active voice, second person, present tense. Briefs you send to
subagents use the same style.

It is a local digest of the [Google developer documentation style guide](https://developers.google.com/style).
The skill lives on disk. Agents do not need that website at runtime.

`./install.sh` does three jobs:

1. **Installs the skill** on Claude, Codex, and Grok (CLI and desktop).
2. **Writes always-on rules** so the style is in context every session.
3. **Installs hooks** that inject the style, wrap child briefs, and bounce a
   sloppy final reply once.

A skill alone is optional. Models skip it. Hooks are what force the behavior
on Code, Codex, and Grok.

## Where it is installed

| Surface | Skill | Always-on | Hooks |
| --- | --- | --- | --- |
| Claude Code (CLI and the Code panel in Desktop) | Copied to `~/.claude/skills/unslop` | `~/.claude/CLAUDE.md` and `~/.claude/rules/unslop.md` | Yes. `~/.claude/settings.json` |
| Codex CLI and Desktop | Copied to `~/.codex/skills/unslop` | `~/.codex/AGENTS.md` | Yes. `~/.codex/hooks.json`. Trust `unslop.py` once in `/hooks` |
| Grok | Copied to `~/.grok/skills/unslop` | `~/.grok/rules/unslop.md` and `~/.grok/AGENTS.md` | Yes. Home rule plus child-brief wrap |
| Claude Desktop Chat / Cowork | Auto-installed into the Desktop skill list and **enabled** | Always-on rules plus the enabled skill | No hook API. Skill is on; hooks are not |
| claude.ai in the browser | Zip at `~/.local/share/unslop/unslop.zip` if the account list does not sync | Upload that zip once, leave Unslop on | No |

Claude Code and Claude chat are different products. Chat will not run hooks.
On Desktop, `./install.sh` still registers Unslop as an enabled skill. In a
browser, upload `unslop.zip` once if the account list did not sync.

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

Apache-2.0. Style digest from the Google developer documentation style guide, CC BY 4.0. See [NOTICE](NOTICE).
