"""Headless UI test using Streamlit's AppTest: drives the real app through
load-sample → chat refinement → accept → undo → export state.

Run:  python scripts/ui_test.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# The demo-mode assertions require no live key in this process. Import the
# config first (it loads .env into os.environ), THEN scrub the key so a real
# key on this machine can't flip the app to live mode mid-test.
import backend.config  # noqa: E402  (side effect: loads .env)

os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("OPENAI_BASE_URL", None)

from streamlit.testing.v1 import AppTest

FAILURES: list[str] = []


def check(name: str, cond: bool) -> None:
    print(f"[{'ok ' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILURES.append(name)


def no_exception(at: AppTest, stage: str) -> None:
    if at.exception:
        for exc in at.exception:
            print(f"    exception at {stage}: {exc.value}")
    check(f"no exception after {stage}", not at.exception)


at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "streamlit_app.py"),
                       default_timeout=30)
at.run()
no_exception(at, "initial load")
check("demo mode auto-on without key", at.session_state["demo_mode"] is True)
check("onboarding shown before chart load",
      any("Fastest path" in str(el.value) for el in at.info))

# Load the sample chart + docs
sample_btn = next(b for b in at.sidebar.button if "sample" in b.label.lower())
sample_btn.click()
at.run()
no_exception(at, "sample load")
check("chart loaded (3 rows)", len(at.session_state["store"].current.rows) == 3)
check("2 sample docs loaded", len(at.session_state["docs"]) == 2)

# Send the assignment's example refinement message
at.chat_input[0].set_value(
    "The AI reasoning for the ML algorithm element is weak - add more technical details"
).run()
no_exception(at, "chat message")
chat = at.session_state["chat"]
check("assistant replied with a suggestion",
      chat[-1].role == "assistant" and len(chat[-1].suggestions) == 1)

# Accept the suggestion via its button
accept_btn = next(b for b in at.main.button if b.label == "✅ Accept")
accept_btn.click()
at.run()
no_exception(at, "accept")
store = at.session_state["store"]
check("chart advanced to v1 after accept", len(store.history) == 2)
check("changed cells highlighted", len(store.changed_cells()) > 0)
check("confirmation message in chat",
      "Applied" in at.session_state["chat"][-1].content)

# Undo by typing in chat (edge case b)
at.chat_input[0].set_value("undo").run()
no_exception(at, "undo via chat")
check("undo reverted the chart", len(at.session_state["store"].history) == 1)

# Ask for evidence that doesn't exist (edge case c)
at.chat_input[0].set_value(
    "Strengthen the evidence that the thermostat uses homomorphic encryption").run()
no_exception(at, "needs-input path")
last = at.session_state["chat"][-1]
check("needs-input card asks for doc/URL",
      bool(last.suggestions) and last.suggestions[0].action == "needs_input")

print()
if FAILURES:
    print(f"FAILED: {len(FAILURES)} check(s): {FAILURES}")
    sys.exit(1)
print("ALL PASSED")
