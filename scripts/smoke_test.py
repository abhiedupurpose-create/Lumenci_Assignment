"""Offline end-to-end backend test (demo engine — no network, no key needed).

Run:  python scripts/smoke_test.py
Exit code 0 + "ALL PASSED" means the backend loop works: load → refine →
accept → add row → correct wrong evidence → undo → needs-input → export,
plus regression checks for every audited fix.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.pop("OPENAI_API_KEY", None)  # deterministic demo-mode behavior

from backend.chart_store import ChartStore
from backend.demo_engine import handle_user_message_demo
from backend.exporter import export_docx, export_filename
from backend.models import ChatMessage, Citation
from backend.parsers import clean_text, parse_claim_chart
from backend.refinement_engine import (SessionMetrics, accept_suggestion,
                                       check_decision_intent, check_undo_intent,
                                       parse_llm_response, reject_suggestion,
                                       verify_citation)
from backend.sample_data import DEFAULT_SYSTEM_PROMPT, sample_chart, sample_docs
from backend.service import respond

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "ok " if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


store = ChartStore()
store.load(sample_chart())
docs = sample_docs()
metrics = SessionMetrics()
history: list[ChatMessage] = []


def ask(text: str):
    resp = handle_user_message_demo(text, store=store, docs=docs, history=history)
    history.append(ChatMessage(role="user", content=text))
    history.append(ChatMessage(role="assistant", content=resp.reply,
                               suggestions=resp.suggestions))
    metrics.record_new(resp.suggestions)
    return resp


# 0. Prompts load from prompts/ (not literals)
check("system prompt loads from prompts/", "iLumos" in DEFAULT_SYSTEM_PROMPT
      and "Evidence discipline" in DEFAULT_SYSTEM_PROMPT)

# 0b. Brace-like text in uploaded content must not break prompt rendering
from backend.models import DocFile
from backend.refinement_engine import build_messages

jinja_doc = DocFile(name="dev_docs.txt",
                    text="The template system uses {{jinja}} syntax throughout.")
msgs = build_messages(DEFAULT_SYSTEM_PROMPT, store.current, [jinja_doc], [], "hello")
check("braces in uploaded docs don't break prompt render",
      "{{jinja}}" in msgs[0]["content"])

# 1. Strengthen weak element (assignment's example message)
r = ask("The AI reasoning for the ML algorithm element is weak - add more technical details")
check("strengthen returns a revision", bool(r.suggestions)
      and r.suggestions[0].action == "revise")
check("revision targets element 3 (ML row)",
      bool(r.suggestions) and r.suggestions[0].target_row_id == store.current.rows[2].row_id)
check("revision is grounded (verified citations)",
      bool(r.suggestions) and r.suggestions[0].grounded)

msg = accept_suggestion(store, r.suggestions[0], metrics)
check("accept applies and reports", "Applied" in msg)
check("stop-signal progress note present", "🎉" in msg or "below" in msg)

# Regression: improving an already-strong row must never downgrade it
r_strong = ask("Strengthen the evidence for element 1")
check("no strength downgrade on improvement",
      not r_strong.suggestions
      or r_strong.suggestions[0].action != "revise"
      or r_strong.suggestions[0].proposed_strength in (None, "strong"))
check("double-accept is a no-op", "already accepted"
      in accept_suggestion(store, r.suggestions[0], metrics))
check("chart advanced to v1", store.version_number == 1)
check("changed cells recorded", len(store.changed_cells()) > 0)

# 2. Undo intent precision (regression: false-positive undo = data loss)
check("bare 'undo' detected", check_undo_intent("undo"))
check("'don't undo anything, strengthen element 2' NOT undo",
      not check_undo_intent("Don't undo anything, just strengthen element 2"))
check("'revert to formal language in element 1' NOT undo",
      not check_undo_intent("please revert to formal language in element 1"))

# 3. Add missing feature (assignment's flagship phrasing)
r = ask("You missed that Acme also has a temperature sensor array")
check("missing feature returns add_row", bool(r.suggestions)
      and r.suggestions[0].action == "add_row")
check("add_row element is the feature itself, not the sentence tail",
      bool(r.suggestions) and (r.suggestions[0].proposed_element or "")
      .lower().startswith("temperature sensor array"))
accept_suggestion(store, r.suggestions[0], metrics)
check("row added", len(store.current.rows) == 4)
check("added row highlighted", len(store.added_row_ids) == 1)

# 4. Orphaned suggestion guard (regression: crash + corrupted metrics)
r = ask("Strengthen the evidence for element 4")
orphan = r.suggestions[0] if r.suggestions else None
store.undo()  # removes the row the pending suggestion targets
if orphan is not None:
    before_accepted = metrics.accepted
    guard_msg = accept_suggestion(store, orphan, metrics)
    check("orphaned accept blocked with friendly message",
          "no longer exists" in guard_msg)
    check("orphaned accept leaves metrics untouched",
          metrics.accepted == before_accepted and orphan.status == "rejected")
else:
    check("orphaned accept blocked with friendly message", False,
          "no suggestion produced for element 4")

# 5. Wrong-evidence correction (edge case a) — targets the last-suggested row
r = ask("That quote is wrong - it isn't from that document")
check("correction returns alternative", bool(r.suggestions))
if r.suggestions and r.suggestions[0].action == "revise":
    reject_suggestion(r.suggestions[0], metrics)

# 6. Undo via chat (edge case b)
before = len(store.history)
r = ask("undo")
check("undo handled deterministically", r.handled_intent == "undo")
check("undo popped a version", len(store.history) == before - 1)

# 7. No evidence available → needs_input (edge case c)
r = ask("Strengthen the evidence that the thermostat uses homomorphic encryption")
check("no-evidence asks for docs/URL", bool(r.suggestions)
      and r.suggestions[0].action == "needs_input"
      and "URL" in (r.suggestions[0].needs_from_user or ""))

# 8. Grounding rigor (regression: trivial/misattributed verification)
fake = Citation(doc_name="acme_tech_spec.txt", quote="quantum entanglement module v9")
check("fabricated quote flagged unverified", not verify_citation(fake, docs))
short = Citation(doc_name="acme_tech_spec.txt", quote="temperature")
check("single-word quote never verifies", not verify_citation(short, docs))
misattr = Citation(doc_name="nonexistent.txt",
                   quote="Built-in motion sensor detects when people are home")
check("misattributed doc name corrected on verify",
      verify_citation(misattr, docs)
      and misattr.doc_name in {d.name for d in docs})

# 9. LLM JSON parsing (tolerant path) — simulates live-engine output
raw = ('Here you go:\n```json\n{"reply": "Suggestion ready.", "suggestions": '
       '[{"action": "revise", "target_row": 2, "proposed_reasoning": "Better.", '
       '"rationale": "test", "confidence": "high", "citations": '
       '[{"doc": "acme_tech_spec.txt", "quote": "Built-in motion sensor detects '
       'when people are home"}]}, {"action": "add_row", "proposed_feature": "x", '
       '"rationale": "no element given"}]}\n```')
parsed = parse_llm_response(raw, store.current, docs)
check("fenced JSON parsed", len(parsed.suggestions) == 1)
check("add_row without element dropped", all(
    s.action != "add_row" for s in parsed.suggestions))
check("live-path citation verified", parsed.suggestions[0].grounded)

# 10. Typed accept through the service facade (decision via conversation)
check("'accept' recognized as decision", check_decision_intent("accept") == "accept")
check("'reject that' recognized", check_decision_intent("reject that") == "reject")
check("long sentence not a decision",
      check_decision_intent("accept that patents are hard and move on") is None)
svc_resp = respond("The AI reasoning for the ML algorithm element is weak",
                   demo_mode=True, system_prompt=DEFAULT_SYSTEM_PROMPT,
                   store=store, docs=docs, history=history, metrics=metrics)
history.append(ChatMessage(role="assistant", content=svc_resp.reply,
                           suggestions=svc_resp.suggestions))
rows_before = store.version_number
acc = respond("accept", demo_mode=True, system_prompt=DEFAULT_SYSTEM_PROMPT,
              store=store, docs=docs, history=history, metrics=metrics)
check("typed 'accept' applies the pending suggestion",
      acc.handled_intent == "accept" and store.version_number == rows_before + 1)

# 11. CSV parsing + control-character sanitization (regression: docx crash)
csv_bytes = ("Patent Claim Element,Accused Product Feature (Evidence),AI Reasoning\n"
             "\"An element\",\"A feat\x0bure\",\"Some reasoning\"\n").encode()
chart = parse_claim_chart("my_chart.csv", csv_bytes)
check("CSV parsed", len(chart.rows) == 1 and chart.rows[0].element == "An element")
check("control chars stripped at parse", "\x0b" not in chart.rows[0].feature)
check("clean_text strips XML-invalid chars", clean_text("a\x00b\x0bc") == "abc")

# 12. Export
data = export_docx(store)
check("docx exported", data[:2] == b"PK" and len(data) > 2000)
check("export filename derived safely",
      export_filename(store).endswith("_refined.docx"))
check("change log present", len(store.change_log()) >= 1)

# 13. Metrics
check("metrics tracked", metrics.suggestions_made >= 3 and metrics.accepted >= 2
      and metrics.grounded >= 2)

print()
if FAILURES:
    print(f"FAILED: {len(FAILURES)} check(s): {FAILURES}")
    sys.exit(1)
print("ALL PASSED")
