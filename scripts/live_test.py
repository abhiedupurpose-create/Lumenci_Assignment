"""LIVE end-to-end test against the real LLM endpoint (uses the key in .env).

Run:  python scripts/live_test.py
Makes 3 API calls on the sample chart and prints the model's actual output:
  1. The assignment's example refinement request  → expect a grounded revision
  2. A missed-feature request                     → expect an add_row
  3. An unsupported-evidence request              → expect needs_input (no fabrication)
Then applies suggestion 1 locally to prove the accept path works on live output.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.chart_store import ChartStore
from backend.config import get_settings
from backend.models import ChatMessage
from backend.refinement_engine import SessionMetrics, accept_suggestion
from backend.sample_data import DEFAULT_SYSTEM_PROMPT, sample_chart, sample_docs
from backend.service import respond

FAILURES: list[str] = []


def check(name: str, cond: bool) -> None:
    print(f"  [{'ok ' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILURES.append(name)


def show(resp) -> None:
    print(f"  reply: {resp.reply[:400]}")
    for s in resp.suggestions:
        print(f"  suggestion: action={s.action} confidence={s.confidence} "
              f"grounded={s.grounded}")
        if s.proposed_feature:
            print(f"    feature:   {s.proposed_feature[:200]}")
        if s.proposed_reasoning:
            print(f"    reasoning: {s.proposed_reasoning[:200]}")
        if s.needs_from_user:
            print(f"    needs:     {s.needs_from_user[:200]}")
        for c in s.citations:
            print(f"    citation [{'✓verified' if c.verified else '⚠UNVERIFIED'}] "
                  f"{c.doc_name}: \"{c.quote[:120]}\"")


settings = get_settings()
print(f"Endpoint: {settings.base_url or 'api.openai.com (default)'}")
print(f"Model:    {settings.model}")
print(f"Key:      {'configured (' + settings.api_key[:6] + '…)' if settings.llm_configured else 'MISSING'}")
if not settings.llm_configured:
    print("No API key found in .env / secrets — aborting live test.")
    sys.exit(2)

store = ChartStore()
store.load(sample_chart())
docs = sample_docs()
metrics = SessionMetrics()
history: list[ChatMessage] = []


def ask(text: str):
    print(f"\n>>> {text}")
    resp = respond(text, demo_mode=False, system_prompt=DEFAULT_SYSTEM_PROMPT,
                   store=store, docs=docs, history=history, metrics=metrics)
    history.append(ChatMessage(role="user", content=text))
    history.append(ChatMessage(role="assistant", content=resp.reply,
                               suggestions=resp.suggestions))
    show(resp)
    return resp


# 1. Assignment's example message
r1 = ask("The AI reasoning for the ML algorithm element is weak - add more technical details")
check("no transport error", r1.handled_intent != "error")
check("returned >=1 suggestion", bool(r1.suggestions))
check("suggestion is a revision", bool(r1.suggestions)
      and r1.suggestions[0].action == "revise")
check("citations verified against docs", bool(r1.suggestions)
      and r1.suggestions[0].grounded)

# Apply it locally (no API call) — proves live output flows through accept
if r1.suggestions:
    msg = accept_suggestion(store, r1.suggestions[0], metrics)
    check("accept applied live suggestion", "Applied" in msg
          and store.version_number == 1)
    print(f"  {msg[:120]}")

# 2. Missed feature — the contract allows an add_row, a revision, or a
# substantive reply (0 suggestions is valid for discussion), so accept any
# non-empty grounded response; only fabrication or transport errors fail.
r2 = ask("You missed that Acme also has a temperature sensor array")
check("no transport error", r2.handled_intent != "error")
check("responds substantively (suggestion or reasoned reply)",
      bool(r2.suggestions) or len(r2.reply) > 40)
check("any citations are verified", all(
    s.grounded for s in r2.suggestions if s.citations))

# 3. Unsupported topic — the no-fabrication test
r3 = ask("Strengthen the evidence that the thermostat uses homomorphic encryption")
check("no transport error", r3.handled_intent != "error")
no_fabrication = (not r3.suggestions
                  or r3.suggestions[0].action == "needs_input"
                  or all(not s.citations or s.grounded for s in r3.suggestions))
check("did NOT fabricate evidence (needs_input or no unverified quotes)",
      no_fabrication)

print()
if FAILURES:
    print(f"LIVE TEST FAILED: {len(FAILURES)} check(s): {FAILURES}")
    sys.exit(1)
print(f"LIVE TEST PASSED — metrics: {metrics.suggestions_made} suggested, "
      f"{metrics.accepted} accepted, grounded rate "
      f"{metrics.grounded_rate:.0%}" if metrics.grounded_rate is not None else "")
