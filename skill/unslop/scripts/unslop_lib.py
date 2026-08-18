#!/usr/bin/env python3
"""Shared Unslop lint, scrub, and subagent-brief wrapping.

This is the mechanical half of the skill. Hooks and the CLI linter import it.
Keep rule text here; ALWAYS_ON.md is the prose contract the model reads.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

EM_DASH = "\u2014"
EN_DASH = "\u2013"
MINUS = "-"

SENTINEL = "<!-- unslop:subagent-contract -->"

PROMPT_KEYS = {
    "prompt",
    "instructions",
    "task",
    "message",
    "query",
    "input",
    "body",
}
DESCRIPTION_KEYS = {"description"}
SUBAGENT_TOOLS = {
    "task",
    "agent",
    "spawn_subagent",
    "spawn_agent",
    "tasktool",
}

FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]+`")

# High-severity chatbot padding. Applied to prose with code stripped.
# Openers match at the start of the text or a paragraph.
OPENER_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("great_question", re.compile(r"(?im)^(?:great question)\b")),
    ("absolutely_opener", re.compile(r"(?im)^(?:absolutely)[!.]")),
    ("of_course_opener", re.compile(r"(?im)^(?:of course)[!,.]")),
    ("happy_to", re.compile(r"(?i)\bi(?:'d| would) be happy to\b")),
    ("lets_dive", re.compile(r"(?i)\blet'?s dive\b")),
    ("lets_unpack", re.compile(r"(?i)\blet'?s unpack\b")),
    ("lets_break_this_down", re.compile(r"(?i)\blet'?s break this down\b")),
    ("heres_the_thing", re.compile(r"(?i)\bhere'?s the thing\b")),
    ("youre_absolutely_right", re.compile(r"(?i)\byou(?:'re| are) absolutely right\b")),
    ("hope_this_helps", re.compile(r"(?i)\bi hope this helps\b")),
    ("certainly_opener", re.compile(r"(?im)^(?:certainly)[!.]")),
    ("sure_thing", re.compile(r"(?im)^(?:sure thing)\b")),
    ("no_problem_opener", re.compile(r"(?im)^(?:no problem)[!.]")),
    ("happy_to_help_opener", re.compile(r"(?im)^(?:happy to help)\b")),
]

BODY_HIGH: list[tuple[str, re.Pattern[str]]] = [
    ("worth_noting", re.compile(r"(?i)\bit'?s worth noting\b")),
    ("important_to_note", re.compile(r"(?i)\bit'?s important to note\b")),
    ("in_todays_world", re.compile(r"(?i)\bin today'?s world\b")),
    ("when_it_comes_to", re.compile(r"(?i)\bwhen it comes to\b")),
    ("at_the_end_of_the_day", re.compile(r"(?i)\bat the end of the day\b")),
    ("make_no_mistake", re.compile(r"(?i)\bmake no mistake\b")),
    ("at_its_core", re.compile(r"(?i)\bat its core\b")),
    ("the_bottom_line", re.compile(r"(?i)\bthe bottom line\b")),
    ("in_conclusion", re.compile(r"(?i)\bin conclusion\b")),
    ("please_note", re.compile(r"(?i)\bplease note\b")),
    ("as_of_this_writing", re.compile(r"(?i)\bas of this writing\b")),
    ("delve", re.compile(r"(?i)\bdelve(?:s|d|ing)?\b")),
    ("dive_deep", re.compile(r"(?i)\bdive deep\b")),
    ("game_changing", re.compile(r"(?i)\bgame-changing\b")),
    ("cutting_edge", re.compile(r"(?i)\bcutting-edge\b")),
    ("seamless", re.compile(r"(?i)\bseamless(?:ly)?\b")),
    ("robust_triplet", re.compile(r"(?i)\brobust,?\s+scalable,?\s+and\s+\w+")),
    ("not_x_its_y", re.compile(r"(?i)\bthis isn'?t\s+[^.]{0,40}\s*[—–-]\s*it'?s\b")),
    ("tldr", re.compile(r"(?i)\btl;dr\b")),
    ("ymmv", re.compile(r"(?i)\bymmv\b")),
]

BODY_MEDIUM: list[tuple[str, re.Pattern[str]]] = [
    ("leverage", re.compile(r"(?i)\bleverage(?:s|d|ing)?\b")),
    ("utilize", re.compile(r"(?i)\butilize(?:s|d|ing)?\b")),
    ("lets_general", re.compile(r"(?i)\blet'?s\b")),
    ("simply", re.compile(r"(?i)\bsimply\b")),
    ("its_easy", re.compile(r"(?i)\bit'?s (?:that )?simple\b|\bit'?s easy\b")),
    ("click_here", re.compile(r"(?i)\bclick here\b")),
    ("in_order_to", re.compile(r"(?i)\bin order to\b")),
    ("allows_you_to", re.compile(r"(?i)\ballows you to\b")),
    ("enable_you_to", re.compile(r"(?i)\benable(?:s)? you to\b")),
]


@dataclass
class Hit:
    rule: str
    severity: str
    count: int
    excerpt: str = ""


@dataclass
class Report:
    hits: list[Hit] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.hits

    @property
    def high(self) -> list[Hit]:
        return [h for h in self.hits if h.severity == "high"]

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "high": bool(self.high),
            "hits": [
                {
                    "rule": h.rule,
                    "severity": h.severity,
                    "count": h.count,
                    "excerpt": h.excerpt,
                }
                for h in self.hits
            ],
        }

    def summary(self) -> str:
        if self.ok:
            return "unslop: clean"
        parts = [f"{h.rule}={h.count}" for h in self.hits]
        return "unslop: " + ", ".join(parts)


def strip_code(text: str) -> str:
    without_fences = FENCE_RE.sub(" ", text)
    return INLINE_CODE_RE.sub(" ", without_fences)


def _count(pattern: re.Pattern[str], text: str) -> tuple[int, str]:
    matches = list(pattern.finditer(text))
    if not matches:
        return 0, ""
    excerpt = matches[0].group(0)
    return len(matches), excerpt[:80]


def lint(text: str) -> Report:
    report = Report()
    if not text or not text.strip():
        return report
    prose = strip_code(text)

    em = prose.count(EM_DASH)
    if em:
        report.hits.append(Hit("em_dash", "high", em, EM_DASH))
    en = prose.count(EN_DASH)
    if en:
        report.hits.append(Hit("en_dash", "high", en, EN_DASH))
    bangs = len(re.findall(r"(?<!\[)!(?!\()", prose))
    # Allow a single bang in a URL or code already stripped. Flag remaining.
    if bangs:
        # Don't flag != leftovers; those should be in code. Remaining ! are prose.
        report.hits.append(Hit("exclamation", "high", bangs, "!"))

    for rule, pattern in OPENER_PATTERNS + BODY_HIGH:
        count, excerpt = _count(pattern, prose)
        if count:
            report.hits.append(Hit(rule, "high", count, excerpt))
    for rule, pattern in BODY_MEDIUM:
        count, excerpt = _count(pattern, prose)
        if count:
            report.hits.append(Hit(rule, "medium", count, excerpt))
    return report


def scrub_dashes(text: str) -> str:
    """Replace em/en dashes outside code with hyphen-minus forms."""

    if EM_DASH not in text and EN_DASH not in text:
        return text

    pieces: list[str] = []
    last = 0
    protected = list(FENCE_RE.finditer(text)) + list(INLINE_CODE_RE.finditer(text))
    protected.sort(key=lambda m: m.start())
    merged: list[re.Match[str]] = []
    for match in protected:
        if merged and match.start() < merged[-1].end():
            continue
        merged.append(match)

    def scrub_chunk(chunk: str) -> str:
        chunk = chunk.replace(EM_DASH, " - ")
        chunk = re.sub(r" - {2,}", " - ", chunk)
        # En dash between digits is a range: keep as hyphen. Elsewhere, hyphen.
        chunk = re.sub(r"(?<=\d)" + EN_DASH + r"(?=\d)", MINUS, chunk)
        return chunk.replace(EN_DASH, MINUS)

    for match in merged:
        pieces.append(scrub_chunk(text[last : match.start()]))
        pieces.append(match.group(0))
        last = match.end()
    pieces.append(scrub_chunk(text[last:]))
    return "".join(pieces)


def subagent_contract(skill_path: str = "") -> str:
    lines = [
        SENTINEL,
        "Write every sentence of your return message in Google developer",
        "documentation style (https://developers.google.com/style).",
        "This return message is user-facing. The parent will quote it.",
        "",
        "Hard rules:",
        "- No em dashes and no en dashes. Use a hyphen-minus or recast.",
        "- No chatbot padding (Great question, Let's dive in, It's worth noting).",
        "- Lead with the answer. Active voice. Present tense. Second person",
        "  or imperative.",
        "- No please in instructions. No let's. No simply / just / easy.",
        "- No exclamation marks except quoted UI or code.",
        "- If a phrase can vanish without changing the facts, drop it.",
    ]
    if skill_path:
        lines.append(f"- Full skill: {skill_path}")
    return "\n".join(lines) + "\n"


def wrap_prompt(prompt: str, skill_path: str = "") -> str:
    scrubbed = scrub_dashes(prompt)
    if SENTINEL in scrubbed:
        return scrubbed
    return scrubbed.rstrip() + "\n\n" + subagent_contract(skill_path)


def is_subagent_tool(name: str) -> bool:
    folded = name.replace("-", "_").lower()
    if folded in SUBAGENT_TOOLS:
        return True
    # MCP-style names
    return folded.endswith("__spawn_subagent") or folded.endswith("__task")


def _mutate(obj: Any, skill_path: str) -> bool:
    changed = False
    if isinstance(obj, dict):
        for key, value in list(obj.items()):
            lower = str(key).lower()
            if isinstance(value, str) and lower in PROMPT_KEYS:
                new = wrap_prompt(value, skill_path)
                if new != value:
                    obj[key] = new
                    changed = True
            elif isinstance(value, str) and lower in DESCRIPTION_KEYS:
                new = scrub_dashes(value)
                if new != value:
                    obj[key] = new
                    changed = True
            elif isinstance(value, (dict, list)):
                if _mutate(value, skill_path):
                    changed = True
    elif isinstance(obj, list):
        for item in obj:
            if _mutate(item, skill_path):
                changed = True
    return changed


def wrap_tool_input(tool_input: Any, skill_path: str = "") -> tuple[Any, bool]:
    if not isinstance(tool_input, (dict, list)):
        return tool_input, False
    import copy

    cloned = copy.deepcopy(tool_input)
    changed = _mutate(cloned, skill_path)
    return cloned, changed


def first_string(payload: dict, *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def tool_name_of(payload: dict) -> str:
    return first_string(payload, "tool_name", "toolName", "tool")


def event_name_of(payload: dict, default: str = "UserPromptSubmit") -> str:
    raw = first_string(payload, "hook_event_name", "hookEventName") or default
    folded = raw.replace("-", "_")
    table = {
        "userpromptsubmit": "UserPromptSubmit",
        "user_prompt_submit": "UserPromptSubmit",
        "sessionstart": "SessionStart",
        "session_start": "SessionStart",
        "subagentstart": "SubagentStart",
        "subagent_start": "SubagentStart",
        "subagentstop": "SubagentStop",
        "subagent_stop": "SubagentStop",
        "pretooluse": "PreToolUse",
        "pre_tool_use": "PreToolUse",
        "posttooluse": "PostToolUse",
        "post_tool_use": "PostToolUse",
        "stop": "Stop",
    }
    key = folded.replace("_", "").lower()
    return table.get(key, table.get(folded.lower(), raw))


def tool_input_of(payload: dict) -> Any:
    for key in ("tool_input", "toolInput", "input", "params", "arguments"):
        value = payload.get(key)
        if isinstance(value, (dict, list)):
            return value
    return {}


def tool_output_text(payload: dict) -> str:
    chunks: list[str] = []
    for key in (
        "tool_response",
        "toolResponse",
        "toolResult",
        "tool_result",
        "last_assistant_message",
        "lastAssistantMessage",
    ):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            chunks.append(value)
        elif isinstance(value, dict):
            for inner in ("content", "output", "text", "message", "result"):
                item = value.get(inner)
                if isinstance(item, str) and item.strip():
                    chunks.append(item)
    return "\n".join(chunks)


def last_message_of(payload: dict) -> str:
    return first_string(
        payload, "last_assistant_message", "lastAssistantMessage"
    ) or tool_output_text(payload)


def stop_already_active(payload: dict) -> bool:
    value = payload.get("stop_hook_active")
    if value is None:
        value = payload.get("stopHookActive")
    return bool(value)


def rewrite_feedback(report: Report) -> str:
    rules = ", ".join(sorted({h.rule for h in report.high or report.hits}))
    return (
        "Rewrite the entire reply. Same facts. Unslop failed: "
        f"{rules}. "
        "No em dashes, no en dashes, no chatbot padding. "
        "Lead with the answer. Follow the Google developer documentation "
        "style guide. Do not mention this rewrite instruction."
    )


def collect_text(values: Iterable[str]) -> str:
    return "\n".join(v for v in values if v)
