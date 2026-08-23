"""Prompt loading & templating.

All LLM prompts live as versioned, reviewable files in the top-level `prompts/`
directory — never as string literals in code. Templates use `{{TOKEN}}`
placeholders and are filled with plain string replacement (NOT str.format),
because prompt bodies legitimately contain JSON braces.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# Placeholders are UPPERCASE by convention; validation runs against the
# TEMPLATE (before substitution), so brace-like text inside substituted user
# content ("uses {{jinja}} syntax" in a tech doc) can never trip it.
_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")


class PromptNotFound(FileNotFoundError):
    """A prompt file referenced by code is missing from prompts/."""


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    """Load a prompt file (without extension) from prompts/, cached."""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise PromptNotFound(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def render_prompt(name: str, **tokens: str) -> str:
    """Fill {{TOKEN}} placeholders in a prompt template.

    Raises ValueError if the template declares a placeholder the caller didn't
    supply — a template/code mismatch should fail loudly, not reach the model
    half-rendered. Validation happens on the template itself, never on the
    substituted content.
    """
    template = load_prompt(name)
    declared = set(_PLACEHOLDER_RE.findall(template))
    missing = declared - tokens.keys()
    if missing:
        raise ValueError(f"Prompt '{name}' has unfilled placeholder(s): "
                         f"{sorted(missing)}")
    for key in declared:
        template = template.replace("{{" + key + "}}", tokens[key])
    return template
