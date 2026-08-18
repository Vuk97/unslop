# Unslop

Stops Claude, Codex, and Grok from writing like chatbots.

Unslop is a local writing skill plus force hooks. It is a digest of the
[Google developer documentation style guide](https://developers.google.com/style).
Agents do not open that page. A short file on disk is the whole contract.

Skills are optional. Models skip them. Hooks are not:

- Before every reply, inject the local contract.
- Before every subagent, scrub long dashes out of the brief and append the same rules.
- After a sloppy child return or a sloppy final message, bounce it once for a rewrite.

Works on Claude Code (CLI and Desktop), Codex (CLI and Desktop), and Grok. Grok
ignores prompt-hook stdout, so Grok also gets a home rule. Codex skips the hook
until you trust it.

```bash
git clone https://github.com/Vuk97/unslop
cd unslop
./install.sh
```

Restart Claude, Codex, and Grok. In Codex, run `/hooks` and trust `unslop.py`.
`./uninstall.sh` removes the wiring. Existing hooks stay.

Apache-2.0. Style digest CC BY 4.0. See [NOTICE](NOTICE).
