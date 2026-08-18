# Subagents

Load this only when you spawn a child, resume one, or quote a child's return.

## Why this file exists

Claude (`Task` / `Agent`), Codex (`spawn_agent`), and Grok (`spawn_subagent`)
all send a `prompt` string to a new model. That string is the child's first
user message. If it is full of em dashes and "please provide a comprehensive
analysis," the child copies the voice.

Hooks already:

1. Scrub em dashes and en dashes in `prompt` and `description`.
2. Append `<!-- unslop:subagent-contract -->` plus the hard rules.
3. Inject ALWAYS_ON.md on `SubagentStart` (Claude and Codex).
4. Lint the child's return on `PostToolUse` and `SubagentStop`.

You still write a clean brief. Hooks cannot invent a good task.

## Brief

Recommended shape:

1. One-line goal.
2. Numbered steps or a short bullet list of checks.
3. What to return: paths, commands, verdicts. Not an essay.
4. What not to do.

Do not write:

- Let's thoroughly explore this and unpack the nuances.
- Provide a comprehensive, robust, and elegant analysis.
- Any em dash.

Grok home rules cover the parent. Grok ignores `UserPromptSubmit` stdout.
The PreToolUse wrap is the Grok child path. Do not strip the appended
contract.

## Return

Quote code and paths as the child produced them. Rewrite the prose wrapper
so it passes ALWAYS_ON. If a Stop / SubagentStop hook bounced you, rewrite
the whole message. Do not mention the bounce.
