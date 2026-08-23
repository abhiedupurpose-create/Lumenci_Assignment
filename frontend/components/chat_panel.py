"""Chat history + AI suggestion cards with Accept / Modify / Reject actions.

Rendering only — every decision routes to backend.refinement_engine handlers
via button callbacks. Suggestion objects live inside the ChatMessage history in
session state, so status changes persist across reruns.
"""
from __future__ import annotations

import html

import streamlit as st

from backend.models import ChatMessage, Suggestion
from backend.refinement_engine import (accept_suggestion, modify_suggestion,
                                       reject_suggestion)
from backend.service import respond

_STATUS_NOTE = {"accepted": "✅ Accepted — applied to the chart",
                "rejected": "🚫 Rejected — chart unchanged",
                "modified": "✏️ Applied with analyst edits"}


def _esc(text: str) -> str:
    return html.escape(str(text)).replace("\n", "<br>")


# ---------------------------------------------------------------------------
# Button callbacks (run before the rerun renders)
# ---------------------------------------------------------------------------

def _say(text: str) -> None:
    st.session_state.chat.append(ChatMessage(role="assistant", content=text))


def _on_accept(sug: Suggestion) -> None:
    _say(accept_suggestion(st.session_state.store, sug, st.session_state.metrics))


def _on_reject(sug: Suggestion) -> None:
    _say(reject_suggestion(sug, st.session_state.metrics))


def _on_open_modify(sug: Suggestion) -> None:
    st.session_state[f"modify_{sug.suggestion_id}"] = True


def _on_cancel_modify(sug: Suggestion) -> None:
    st.session_state.pop(f"modify_{sug.suggestion_id}", None)


def _modify_seeds(sug: Suggestion) -> dict:
    """The values the Modify form was pre-filled with (proposal, falling back
    to the current row) — a user edit is whatever differs from these."""
    store = st.session_state.store
    row = store.current.get_row(sug.target_row_id) if sug.target_row_id else None
    return {
        "element": sug.proposed_element or "",
        "feature": sug.proposed_feature or (row.feature if row else ""),
        "reasoning": sug.proposed_reasoning or (row.reasoning if row else ""),
        "strength": sug.proposed_strength or (row.strength if row else "moderate"),
    }


def _on_apply_modify(sug: Suggestion) -> None:
    sid = sug.suggestion_id
    seeds = _modify_seeds(sug)
    overrides = {}
    for field, seed in seeds.items():
        val = st.session_state.get(f"mod_{field}_{sid}")
        # Any deliberate edit counts — including clearing a field. Comparing
        # against the seed (not truthiness) means an analyst's deletion is
        # never silently replaced by the AI's proposal.
        if val is not None and val != seed:
            overrides[field] = val
    _say(modify_suggestion(st.session_state.store, sug, overrides,
                           st.session_state.metrics))
    st.session_state.pop(f"modify_{sid}", None)


# ---------------------------------------------------------------------------
# Suggestion card
# ---------------------------------------------------------------------------

def _grounding_badge(sug: Suggestion) -> str:
    if not sug.citations:
        return '<span class="badge badge-unverified">no citation</span>'
    if sug.grounded:
        return '<span class="badge badge-verified">✓ quotes verified in docs</span>'
    return '<span class="badge badge-unverified">⚠ unverified quote — check source</span>'


def _field_diff(label: str, before: str | None, after: str | None) -> str:
    if not after:
        return ""
    parts = [f'<div class="sug-field-label">{label}</div>']
    if before and before != after:
        parts.append(f'<div class="sug-before">{_esc(before)}</div>')
    parts.append(f'<div class="sug-after">{_esc(after)}</div>')
    return "".join(parts)


def _render_modify_form(sug: Suggestion) -> None:
    sid = sug.suggestion_id
    seeds = _modify_seeds(sug)
    st.caption("Edit the proposal before applying:")
    if sug.action == "add_row":
        st.text_area("Patent claim element", value=seeds["element"],
                     key=f"mod_element_{sid}", height=68)
    st.text_area("Accused product feature (evidence)", value=seeds["feature"],
                 key=f"mod_feature_{sid}", height=100)
    st.text_area("AI reasoning", value=seeds["reasoning"],
                 key=f"mod_reasoning_{sid}", height=120)
    options = ["strong", "moderate", "weak"]
    st.selectbox("Evidence strength", options,
                 index=options.index(seeds["strength"]),
                 key=f"mod_strength_{sid}")
    c1, c2 = st.columns(2)
    c1.button("Apply my edits", key=f"apply_{sid}", type="primary",
              use_container_width=True, on_click=_on_apply_modify, args=(sug,))
    c2.button("Cancel", key=f"cancel_{sid}", use_container_width=True,
              on_click=_on_cancel_modify, args=(sug,))


def _render_suggestion(sug: Suggestion) -> None:
    store = st.session_state.store
    with st.container(border=True):
        target = ""
        if sug.target_row_id:
            idx = store.current.row_index(sug.target_row_id)
            target = f" · element {idx + 1}" if idx is not None else ""
        st.markdown(
            f'<div class="sug-head">💡 {_esc(sug.summary_label())}{target}</div>'
            f'<span class="badge badge-confidence">confidence: {_esc(sug.confidence)}</span> '
            f"{_grounding_badge(sug) if sug.action != 'needs_input' else ''}",
            unsafe_allow_html=True)

        if sug.action == "needs_input":
            st.markdown(sug.needs_from_user or sug.rationale)
            st.caption("📎 Use **Product documents** or **Fetch evidence from URL** "
                       "in the sidebar, then ask me again.")
            return

        row = store.current.get_row(sug.target_row_id) if sug.target_row_id else None
        diff_html = "".join([
            _field_diff("Patent claim element", None, sug.proposed_element),
            _field_diff("Accused product feature (evidence)",
                        row.feature if row else None, sug.proposed_feature),
            _field_diff("AI reasoning", row.reasoning if row else None,
                        sug.proposed_reasoning),
            _field_diff("Evidence strength", row.strength if row else None,
                        sug.proposed_strength),
        ])
        if diff_html:
            st.markdown(diff_html, unsafe_allow_html=True)
        if sug.rationale:
            st.caption(f"Why: {sug.rationale}")
        if sug.citations:
            with st.expander(f"📄 Cited evidence ({len(sug.citations)})"):
                for cit in sug.citations:
                    mark = "✓" if cit.verified else "⚠ not found in this document"
                    st.markdown(
                        f'<div class="sug-quote">"{_esc(cit.quote)}"<br>'
                        f"— <b>{_esc(cit.doc_name)}</b> · {mark}</div>",
                        unsafe_allow_html=True)

        if sug.status != "pending":
            st.caption(_STATUS_NOTE.get(sug.status, sug.status))
            return

        if st.session_state.get(f"modify_{sug.suggestion_id}"):
            _render_modify_form(sug)
        else:
            sid = sug.suggestion_id
            c1, c2, c3 = st.columns(3)
            c1.button("✅ Accept", key=f"acc_{sid}", type="primary",
                      use_container_width=True, on_click=_on_accept, args=(sug,))
            c2.button("✏️ Modify", key=f"mod_{sid}", use_container_width=True,
                      on_click=_on_open_modify, args=(sug,))
            c3.button("🚫 Reject", key=f"rej_{sid}", use_container_width=True,
                      on_click=_on_reject, args=(sug,))


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------

def _process_pending() -> None:
    """Handle a queued user message with the spinner inside the chat panel,
    then rerun so every panel (chart included) re-renders on fresh state."""
    ss = st.session_state
    pending = ss.pop("pending_request", None)
    if pending is None:
        return
    with st.chat_message("assistant", avatar="✨"):
        with st.spinner("Analyzing the chart and documents…"):
            resp = respond(pending, demo_mode=ss.demo_mode,
                           system_prompt=ss.system_prompt, store=ss.store,
                           docs=ss.docs, history=ss.chat[:-1],
                           metrics=ss.metrics)
    ss.chat.append(ChatMessage(role="assistant", content=resp.reply,
                               suggestions=resp.suggestions))
    st.rerun()


def render_chat() -> None:
    """The full chat pane: history, suggestion cards, and the input box fused
    into one card (keyed containers are styled in frontend/styles.py — the
    history scrolls internally, the input sits on its bottom edge)."""
    with st.container(key="chat_pane"):
        st.caption("💬 **Refinement chat**")
        box = st.container(height=520, key="chat_history")
        with box:
            if not st.session_state.chat:
                st.info(
                    'Ask me to refine the chart. Try: **"Strengthen the evidence '
                    'for element 3"** · **"The reasoning for element 3 is weak — '
                    'add technical detail"** · **"undo"**')
            for msg in st.session_state.chat:
                avatar = "🧑‍⚖️" if msg.role == "user" else "✨"
                with st.chat_message(msg.role, avatar=avatar):
                    st.markdown(msg.content)
                    for sug in msg.suggestions:
                        _render_suggestion(sug)
            _process_pending()

        prompt = st.chat_input(
            'Ask for a refinement… e.g. "strengthen element 3"', key="chat_box")
        if prompt and prompt.strip():
            st.session_state.chat.append(
                ChatMessage(role="user", content=prompt.strip()))
            st.session_state.pending_request = prompt.strip()
            st.rerun()
