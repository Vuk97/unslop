# Unslop

Stops coding agents from writing like chatbots.

Local skill plus hooks. The skill is optional. Models skip it. Hooks force
the style on the main thread, on subagents, and on their outputs. Nothing
fetches a URL.

## Where it works

| Surface | Skill | Forced |
| --- | --- | --- |
| Claude **Code** (CLI, and the Code panel in Desktop) | Yes | Yes. Hooks in `~/.claude/settings.json` |
| Codex CLI and Desktop | Yes | Yes. Hooks in `~/.codex/hooks.json`. Trust `unslop.py` in `/hooks` |
| Grok | Yes | Yes. Home rule plus child-brief wrap. Grok ignores prompt-hook stdout |
| Claude **chat** (claude.ai, or the Chat tab in Desktop) | Upload `SKILL.md` if you want `/unslop` | No. Chat has no hook API |

Claude Code and Claude chat are different products. Chat will not read
`~/.claude/settings.json`. For always-on Chat, paste `skill/unslop/ALWAYS_ON.md`
into custom instructions.

## How to force it

```bash
git clone https://github.com/Vuk97/unslop
cd unslop
./install.sh
```

1. Restart Claude Code, Codex, and Grok. Old sessions do not load new hooks.
2. In Codex, run `/hooks` and trust `unslop.py`. Until you do, Codex skips it.
3. Test in **Code**, not Chat. Ask for a two-sentence answer. You should not
   get chatbot padding.

`./uninstall.sh` removes the wiring. Existing hooks stay.

Apache-2.0. Style digest from the [Google developer documentation style guide](https://developers.google.com/style), CC BY 4.0. See [NOTICE](NOTICE).
