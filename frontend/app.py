"""iLumos — AI chat-based claim chart refinement (prototype).

This module is layout + session wiring only; every decision (engine dispatch,
parsing, grounding, versioning, export) lives in backend/*.
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
from frontend.components.sidebar import render_sidebar
from frontend.styles import brand_header, inject_styles


def _init_state() -> None:
    ss = st.session_state
    ss.setdefault("store", ChartStore())
    ss.setdefault("docs", [])
    ss.setdefault("chat", [])
    ss.setdefault("metrics", SessionMetrics())
    ss.setdefault("system_prompt", DEFAULT_SYSTEM_PROMPT)
    ss.setdefault("processed_docs", set())
    ss.setdefault("demo_mode", not get_settings().llm_configured)


def _render_onboarding() -> None:
    st.markdown(brand_header(), unsafe_allow_html=True)
    st.markdown("#### Claim chart refinement, grounded in your evidence")
    st.markdown(
        "Upload a claim chart, add product documents as evidence sources, then "
        "**refine the chart conversationally** — the AI proposes changes with "
        "verified citations, you approve every one, and export the result to Word.")
    c1, c2, c3 = st.columns(3)
    with c1, st.container(border=True):
        st.markdown("**1 · Upload claim chart**")
        st.caption("CSV, XLSX, or JSON with the 3 columns: Patent Claim Element · "
                   "Accused Product Feature (Evidence) · AI Reasoning. Use the "
                   "sidebar on the left.")
    with c2, st.container(border=True):
        st.markdown("**2 · Add product documents**")
        st.caption("Spec sheets, product pages, manuals (TXT/MD/PDF) — or fetch a "
                   "URL. Every AI suggestion must cite these; unverified quotes "
                   "get flagged.")
    with c3, st.container(border=True):
        st.markdown("**3 · Refine in chat**")
        st.caption("Ask for stronger evidence, better reasoning, missing elements, "
                   "or legal rewrites. Accept, modify, or reject each suggestion. "
                   "Undo anytime. Export to Word when done.")
    st.info("👈 **Fastest path:** click *Load sample chart & docs* in the sidebar "
            "to explore with the Acme thermostat example.")


def main() -> None:
    st.set_page_config(page_title="iLumos — Claim Chart Refinement",
                       page_icon="✳️", layout="wide")
    inject_styles()
    _init_state()
    render_sidebar()

    if not st.session_state.store.loaded:
        _render_onboarding()
        return

    # The chat input is pinned to the page bottom. A submitted message is
    # queued as pending_request and processed INSIDE the chat panel (spinner
    # in place), which then triggers a rerun so the chart never renders stale.
    prompt = st.chat_input("Ask iLumos to refine the chart… "
                           '(e.g. "strengthen the evidence for element 2")')
    if prompt and prompt.strip():
        st.session_state.chat.append(ChatMessage(role="user", content=prompt.strip()))
        st.session_state.pending_request = prompt.strip()

    st.markdown(brand_header(""), unsafe_allow_html=True)
    st.markdown(f"### {st.session_state.store.current.title}")
    col_chart, col_chat = st.columns([0.56, 0.44], gap="large")
    with col_chart:
        render_toolbar()
        render_chart(st.session_state.store)
    with col_chat:
        render_chat()


if __name__ == "__main__":
    main()
