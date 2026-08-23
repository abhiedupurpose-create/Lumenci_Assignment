"""The refinement engine: turns analyst chat messages into structured,
grounded suggestions, and applies accepted suggestions to the chart.

Flow per message:
  1. Deterministic intents first (undo) — no LLM call, no ambiguity.
  2. Otherwise build a context-rich prompt (system instructions + numbered
     chart + document excerpts + recent conversation) and ask the LLM for a
     JSON reply with suggestion objects.
  3. Parse tolerantly, resolve element numbers to row ids, and run the
     grounding check: every cited quote must appear in an uploaded document,
     otherwise the citation is flagged unverified in the UI.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from backend.chart_store import ChartStore
from backend.llm_client import LLMClient, LLMError
from backend.models import (ChatMessage, Citation, ClaimChart, DocFile,
                            EngineResponse, Suggestion)
from backend.prompts import load_prompt, render_prompt

# Deterministic intents fire only on short, imperative messages — a mention of
# "undo"/"accept" inside a longer request ("don't undo anything, strengthen
# element 2") must reach the engine, not trigger an irreversible action.
_INTENT_MAX_WORDS = 4
_UNDO_RE = re.compile(r"^\s*(?:please\s+|now\s+)?(?:undo|revert|roll\s?back)\b",
                      re.IGNORECASE)
_ACCEPT_RE = re.compile(r"^\s*(?:please\s+)?(?:accept|apply|approve)\b(?:\s+(?:it|that|"
                        r"this|the\s+suggestion))?\s*[.!]*\s*$", re.IGNORECASE)
_REJECT_RE = re.compile(r"^\s*(?:please\s+)?(?:reject|discard|dismiss)\b(?:\s+(?:it|that|"
                        r"this|the\s+suggestion))?\s*[.!]*\s*$", re.IGNORECASE)

_MAX_DOC_CHARS = 9000
_HISTORY_TURNS = 8


@dataclass
class SessionMetrics:
    """Chat-quality signals surfaced in the sidebar (and proposed in the PRD)."""
    suggestions_made: int = 0
    accepted: int = 0
    rejected: int = 0
    modified: int = 0
    grounded: int = 0
    llm_failures: int = 0

    @property
    def decided(self) -> int:
        return self.accepted + self.rejected + self.modified

    @property
    def acceptance_rate(self) -> float | None:
        return (self.accepted + self.modified) / self.decided if self.decided else None

    @property
    def grounded_rate(self) -> float | None:
        return self.grounded / self.suggestions_made if self.suggestions_made else None

    def record_new(self, suggestions: list[Suggestion]) -> None:
        actionable = [s for s in suggestions if s.action != "needs_input"]
        self.suggestions_made += len(actionable)
        self.grounded += sum(1 for s in actionable if s.grounded)


# --------------------------------------------------------------------------
# Prompt building
# --------------------------------------------------------------------------

def _chart_as_text(chart: ClaimChart) -> str:
    lines = [f"CLAIM CHART: {chart.title}"]
    for i, row in enumerate(chart.rows, start=1):
        lines.append(
            f"\nElement {i} [evidence strength: {row.strength}]\n"
            f"  Patent Claim Element: {row.element}\n"
            f"  Accused Product Feature (Evidence): {row.feature}\n"
            f"  AI Reasoning: {row.reasoning}")
    return "\n".join(lines)


def _docs_as_text(docs: list[DocFile]) -> str:
    if not docs:
        return ("(No product documents uploaded yet. Any evidence suggestion must use "
                "action 'needs_input' to request documentation or a URL.)")
    parts = []
    for doc in docs:
        body = doc.text[:_MAX_DOC_CHARS]
        truncated = " …[truncated]" if len(doc.text) > _MAX_DOC_CHARS else ""
        parts.append(f"--- DOCUMENT: {doc.name} ---\n{body}{truncated}")
    return "\n\n".join(parts)


def build_messages(system_prompt: str, chart: ClaimChart, docs: list[DocFile],
                   history: list[ChatMessage], user_message: str) -> list[dict]:
    system = render_prompt(
        "context_template",
        SYSTEM_PROMPT=system_prompt,
        OUTPUT_CONTRACT=load_prompt("output_contract"),
        CLAIM_CHART=_chart_as_text(chart),
        DOCUMENTS=_docs_as_text(docs),
    )
    messages = [{"role": "system", "content": system}]
    for msg in history[-_HISTORY_TURNS:]:
        content = msg.content
        if msg.suggestions:  # remind the model what it proposed and the outcome
            outcomes = "; ".join(
                f"[{s.summary_label()} — {s.status}]" for s in msg.suggestions)
            content = f"{content}\n(Proposed suggestions: {outcomes})"
        messages.append({"role": msg.role, "content": content})
    messages.append({"role": "user", "content": user_message})
    return messages


# --------------------------------------------------------------------------
# Response parsing & grounding
# --------------------------------------------------------------------------

def _extract_json(raw: str) -> dict:
    """Parse strict JSON, or rescue a fenced/embedded JSON object."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        start, end = raw.find("{"), raw.rfind("}")
        candidate = raw[start:end + 1] if 0 <= start < end else None
    if candidate:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    raise ValueError("unparseable LLM output")


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def verify_citation(citation: Citation, docs: list[DocFile]) -> bool:
    """A citation is verified iff its quote appears (whitespace/case-insensitively)
    in the named document — or, failing that, in another uploaded document, in
    which case the citation's doc name is corrected to the real source so a
    'verified' badge never sits next to a misattributed document name.

    Quotes must carry real evidentiary substance (>= 4 words and >= 20 chars):
    a single common word matching somewhere is not verification."""
    quote = _squash(citation.quote)
    if len(quote) < 20 or len(quote.split()) < 4:
        return False
    named = [d for d in docs if d.name == citation.doc_name]
    for doc in named:
        if quote in _squash(doc.text):
            return True
    for doc in docs:
        if doc not in named and quote in _squash(doc.text):
            citation.doc_name = doc.name  # correct the attribution
            return True
    return False


_VALID_STRENGTHS = {"strong", "moderate", "weak"}
_VALID_CONFIDENCE = {"high", "medium", "low"}


def parse_llm_response(raw: str, chart: ClaimChart,
                       docs: list[DocFile]) -> EngineResponse:
    payload = _extract_json(raw)
    reply = str(payload.get("reply") or "").strip() or "Here are my suggestions."
    suggestions: list[Suggestion] = []
    for item in payload.get("suggestions") or []:
        if not isinstance(item, dict):
            continue
        action = item.get("action")
        if action not in ("revise", "add_row", "needs_input"):
            continue
        target_row_id = None
        if action == "revise":
            try:
                idx = int(item.get("target_row", 0)) - 1
                target_row_id = chart.rows[idx].row_id if 0 <= idx < len(chart.rows) else None
            except (TypeError, ValueError):
                target_row_id = None
            if target_row_id is None:
                continue  # can't safely apply a revision to an unknown row
        strength = item.get("proposed_strength")
        confidence = item.get("confidence")
        citations = []
        for c in item.get("citations") or []:
            if isinstance(c, dict) and c.get("quote"):
                cit = Citation(doc_name=str(c.get("doc", "")), quote=str(c["quote"]))
                cit.verified = verify_citation(cit, docs)
                citations.append(cit)
        sug = Suggestion(
            action=action,
            target_row_id=target_row_id,
            proposed_element=item.get("proposed_element") or None,
            proposed_feature=item.get("proposed_feature") or None,
            proposed_reasoning=item.get("proposed_reasoning") or None,
            proposed_strength=strength if strength in _VALID_STRENGTHS else None,
            rationale=str(item.get("rationale") or "").strip(),
            confidence=confidence if confidence in _VALID_CONFIDENCE else "medium",
            citations=citations,
            needs_from_user=item.get("needs_from_user") or None,
        )
        if sug.action == "revise" and not (sug.proposed_feature or sug.proposed_reasoning
                                           or sug.proposed_strength):
            continue  # a revision that changes nothing is noise
        if sug.action == "add_row" and not (sug.proposed_element or "").strip():
            continue  # a new row without a claim element would be rejected at upload too
        suggestions.append(sug)
    return EngineResponse(reply=reply, suggestions=suggestions)


# --------------------------------------------------------------------------
# Engine entry points (used by frontend for BOTH live and demo paths)
# --------------------------------------------------------------------------

def _is_short(message: str) -> bool:
    return len(message.split()) <= _INTENT_MAX_WORDS


def check_undo_intent(user_message: str) -> bool:
    """True only for short, imperative undo messages ("undo", "please revert").
    Longer messages that merely mention the words go to the engine instead —
    a false-positive undo would irreversibly pop a version."""
    return _is_short(user_message) and bool(_UNDO_RE.match(user_message))


def check_decision_intent(user_message: str) -> Optional[str]:
    """'accept' / 'reject' for short imperative messages ("accept", "apply that"),
    so the analyst can decide through conversation as well as buttons."""
    if not _is_short(user_message):
        return None
    if _ACCEPT_RE.match(user_message):
        return "accept"
    if _REJECT_RE.match(user_message):
        return "reject"
    return None


def latest_pending_suggestion(history: list[ChatMessage]) -> Optional[Suggestion]:
    for msg in reversed(history):
        for sug in reversed(msg.suggestions):
            if sug.status == "pending" and sug.action != "needs_input":
                return sug
    return None


def perform_undo(store: ChartStore) -> EngineResponse:
    undone = store.undo()
    if undone is None:
        return EngineResponse(
            reply="There's nothing to undo — the chart is at its original state.",
            handled_intent="undo")
    return EngineResponse(
        reply=f'Done — I reverted "{undone}". The chart is back to its previous state, '
              "and the change is reflected in the version history above the chart.",
        handled_intent="undo")


def handle_user_message(user_message: str, *, client: LLMClient,
                        system_prompt: str, store: ChartStore,
                        docs: list[DocFile],
                        history: list[ChatMessage]) -> EngineResponse:
    """Live-LLM path. Raises LLMError upward only for transport issues the UI
    should show; malformed model output degrades to a plain reply."""
    if check_undo_intent(user_message):
        return perform_undo(store)
    messages = build_messages(system_prompt, store.current, docs, history, user_message)
    raw = client.complete(messages, json_mode=True)
    try:
        return parse_llm_response(raw, store.current, docs)
    except ValueError:
        # Model ignored the JSON contract — show its text rather than crash.
        return EngineResponse(reply=raw.strip()[:2000] or
                              "I couldn't structure a suggestion for that — could you rephrase?")


# --------------------------------------------------------------------------
# Applying analyst decisions (called by frontend button handlers)
# --------------------------------------------------------------------------

def _decision_guard(store: ChartStore, sug: Suggestion) -> Optional[str]:
    """Reasons a suggestion can no longer be decided; None when it's actionable.
    Checked BEFORE any status/metric mutation so a stale click can't corrupt state."""
    if sug.status != "pending":
        return f"That suggestion was already {sug.status} — nothing changed."
    if (sug.action == "revise" and sug.target_row_id
            and store.current.get_row(sug.target_row_id) is None):
        sug.status = "rejected"  # retire the orphaned card
        return ("⚠️ That suggestion targeted a row that no longer exists (it was "
                "removed by an undo), so I've retired it. Ask me again against the "
                "current chart and I'll re-propose.")
    return None


def _completion_note(store: ChartStore) -> str:
    """The stop signal: once every element has strong support, say so —
    the analyst should know when refinement is done, not fix forever."""
    if all(r.strength == "strong" for r in store.current.rows):
        return ("\n\n🎉 **Every element now has strong support** — the chart is "
                "refinement-complete. Export to Word when you're ready.")
    remaining = sum(1 for r in store.current.rows if r.strength != "strong")
    return f"\n\n{remaining} element(s) still below *strong* — ask me when ready."


def accept_suggestion(store: ChartStore, sug: Suggestion,
                      metrics: SessionMetrics) -> str:
    blocked = _decision_guard(store, sug)
    if blocked:
        return blocked
    label = _label_for(store.current, sug)
    store.apply_suggestion(sug, label)
    sug.status = "accepted"
    metrics.accepted += 1
    return (f"✅ Applied: {label}. The updated cells are highlighted in the chart. "
            'Say "undo" anytime to revert.' + _completion_note(store))


def modify_suggestion(store: ChartStore, sug: Suggestion, overrides: dict,
                      metrics: SessionMetrics) -> str:
    blocked = _decision_guard(store, sug)
    if blocked:
        return blocked
    if sug.action == "add_row" and not (
            overrides.get("element", sug.proposed_element) or "").strip():
        return ("⚠️ A new row needs a non-empty patent claim element — "
                "I didn't apply that. Reopen Modify and fill the element text.")
    label = _label_for(store.current, sug) + " (edited by analyst)"
    store.apply_suggestion(sug, label, overrides=overrides)
    sug.status = "modified"
    metrics.modified += 1
    return (f"✏️ Applied with your edits: {label}. "
            'Say "undo" anytime to revert.' + _completion_note(store))


def reject_suggestion(sug: Suggestion, metrics: SessionMetrics) -> str:
    if sug.status != "pending":
        return f"That suggestion was already {sug.status} — nothing changed."
    sug.status = "rejected"
    metrics.rejected += 1
    return ("👍 Rejected — the chart is unchanged. Tell me what was wrong "
            "(e.g. wrong document, wrong element) and I'll propose an alternative.")


def _label_for(chart: ClaimChart, sug: Suggestion) -> str:
    if sug.action == "add_row":
        element = (sug.proposed_element or "new element")[:60]
        return f"Added row: {element}"
    idx = chart.row_index(sug.target_row_id or "")
    n = idx + 1 if idx is not None else "?"
    changed = [name for name, val in (("evidence", sug.proposed_feature),
                                      ("reasoning", sug.proposed_reasoning),
                                      ("strength", sug.proposed_strength)) if val]
    return f"Revised element {n} ({', '.join(changed) or 'fields'})"
