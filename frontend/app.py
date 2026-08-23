"""iLumos — AI chat-based claim chart refinement (prototype).

Layout + session wiring only; every decision (engine dispatch, parsing,
grounding, versioning, export) lives in backend/*. No sidebar: setup happens
on the onboarding screen, then everything lives in the main pane — chart on
the left, Chat / Evidence / Settings tabs on the right.
"""
from __future__ import annotations

import streamlit as st

from backend.chart_store import ChartStore
from backend.config import get_settings
from backend.models import ChatMessage
from backend.refinement_engine import SessionMetrics
from backend.sample_data import DEFAULT_SYSTEM_PROMPT
from frontend.components.chart_view import render_chart
from frontend.components.chat_panel import render_chat
from frontend.components.export_panel import render_toolbar
from frontend.components.setup import (render_evidence_tab,
                                       render_onboarding_setup,
                                       render_settings_tab)
from frontend.styles import brand_header, inject_styles


def _init_state() -> None:
    ss = st.session_state
    ss.setdefault("store", ChartStore())
    ss.setdefault("docs", [])
    ss.setdefault("chat", [])
    ss.setdefault("metrics", SessionMetrics())
    ss.setdefault("system_prompt", DEFAULT_SYSTEM_PROMPT)
    ss.setdefault("processed_docs", set())
    # No API key configured → the scripted demo engine answers (labeled in chat).
    ss.setdefault("demo_mode", not get_settings().llm_configured)


def _render_onboarding() -> None:
    st.markdown(brand_header(), unsafe_allow_html=True)
    st.markdown(
        "Refine patent claim charts conversationally — the AI proposes changes "
        "with **verified citations** from your product documents, you approve "
        "every one, and the result exports to Word.")
    render_onboarding_setup()


def main() -> None:
    st.set_page_config(page_title="iLumos — Claim Chart Refinement",
                       page_icon="✳️", layout="wide")
    inject_styles()
    _init_state()

    if not st.session_state.store.loaded:
        _render_onboarding()
        return

    # The chat input is pinned to the page bottom. A submitted message is
    # queued and processed INSIDE the chat panel (spinner in place), which
    # then triggers a rerun so the chart never renders stale.
    prompt = st.chat_input("Ask iLumos to refine the chart… "
                           '(e.g. "strengthen the evidence for element 2")')
    if prompt and prompt.strip():
        st.session_state.chat.append(ChatMessage(role="user", content=prompt.strip()))
        st.session_state.pending_request = prompt.strip()

    st.markdown(brand_header(""), unsafe_allow_html=True)
    st.markdown(f"### {st.session_state.store.current.title}")
    col_chart, col_right = st.columns([0.56, 0.44], gap="large")
    with col_chart:
        render_toolbar()
        render_chart(st.session_state.store)
    with col_right:
        tab_chat, tab_evidence, tab_settings = st.tabs(
            ["💬 Chat", "📁 Evidence", "⚙️ Settings"])
        with tab_chat:
            render_chat()
        with tab_evidence:
            render_evidence_tab()
        with tab_settings:
            render_settings_tab()


if __name__ == "__main__":
    main()
