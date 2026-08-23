"""Sidebar: the initial-setup flow (uploads, system prompt, engine status),
the URL-evidence fetcher, and session quality metrics."""
from __future__ import annotations

import streamlit as st

from backend.models import ChatMessage, DocFile
from backend.parsers import (ChartParseError, fetch_url_as_doc,
                             parse_claim_chart, parse_product_doc)
from backend.sample_data import sample_chart, sample_docs
from backend.service import engine_status
from frontend.styles import brand_header


def _say(text: str) -> None:
    st.session_state.chat.append(ChatMessage(role="assistant", content=text))


def _upload_token(file) -> tuple:
    """Identity of one upload event. file_id is unique per upload in modern
    Streamlit, so re-adding a removed file or an edited same-size file is
    never silently swallowed; (name, size) is the fallback."""
    return (getattr(file, "file_id", None) or (file.name, file.size),)


def _add_doc(doc: DocFile) -> None:
    """Add to the evidence pool, replacing any same-named document."""
    st.session_state.docs = [d for d in st.session_state.docs if d.name != doc.name]
    st.session_state.docs.append(doc)


def _load_sample() -> None:
    st.session_state.store.load(sample_chart())
    st.session_state.docs = sample_docs()
    st.session_state.chat = []
    # Reset upload dedup state so the analyst's own files can be re-imported
    # after exploring the sample.
    st.session_state.processed_docs = set()
    st.session_state.pop("_chart_token", None)
    _say("Loaded the **Acme thermostat** sample chart and 2 product documents. "
         "Element 3 (the ML algorithm) is marked **weak** — a good place to start. "
         'Try: *"The AI reasoning for the ML algorithm element is weak — add more '
         'technical details."*')


def _remove_doc(name: str) -> None:
    st.session_state.docs = [d for d in st.session_state.docs if d.name != name]
    _say(f"🗑️ Removed **{name}** from the evidence pool.")


def _fetch_url() -> None:
    """Button callback: fetch → add to pool → clear the input. Runs in the
    callback so the text_input can be reset before widgets re-render."""
    url = (st.session_state.get("evidence_url") or "").strip()
    if not url:
        return
    try:
        doc = fetch_url_as_doc(url)
        _add_doc(doc)
        st.session_state.evidence_url = ""
        _say(f"🔗 Scraped **{doc.name}** ({len(doc.text):,} chars) into the evidence "
             "pool. Ask me again about the element that needed evidence.")
    except Exception as exc:
        st.session_state["_url_error"] = f"Could not fetch that URL: {exc}"


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(brand_header("") + "<br>", unsafe_allow_html=True)
        st.caption("AI claim chart refinement — prototype")

        # ---- engine status & demo toggle --------------------------------
        label, detail = engine_status(st.session_state.demo_mode)
        st.markdown(f"**{label}**")
        st.caption(detail)
        st.toggle("Demo mode (no API key needed)", key="demo_mode",
                  help="Scripted engine with real retrieval over your uploaded "
                       "documents. Automatically on when no API key is set.")
        st.divider()

        # ---- 1. claim chart ----------------------------------------------
        st.markdown("**1 · Claim chart**")
        chart_file = st.file_uploader(
            "Upload claim chart (CSV, XLSX, JSON)", type=["csv", "xlsx", "json"],
            key="chart_upload", label_visibility="collapsed")
        if chart_file is not None:
            token = _upload_token(chart_file)
            if st.session_state.get("_chart_token") != token:
                try:
                    st.session_state.store.load(
                        parse_claim_chart(chart_file.name, chart_file.getvalue()))
                    st.session_state.chat = []
                    st.session_state["_chart_token"] = token
                    _say(f"Loaded **{chart_file.name}** "
                         f"({len(st.session_state.store.current.rows)} claim elements). "
                         "Upload product documents next so I can ground my suggestions.")
                except ChartParseError as exc:
                    st.error(str(exc))

        st.button("📋 Load sample chart & docs", use_container_width=True,
                  on_click=_load_sample,
                  help="Acme thermostat example from the assignment")

        # ---- 2. product documents ----------------------------------------
        st.markdown("**2 · Product documents** (evidence sources)")
        doc_files = st.file_uploader(
            "Upload product docs (TXT, MD, PDF)", type=["txt", "md", "pdf"],
            accept_multiple_files=True, key="doc_upload",
            label_visibility="collapsed")
        for file in doc_files or []:
            token = _upload_token(file)
            if token in st.session_state.processed_docs:
                continue
            try:
                doc = parse_product_doc(file.name, file.getvalue())
                _add_doc(doc)
                st.session_state.processed_docs.add(token)
                _say(f"📄 Added **{doc.name}** ({len(doc.text):,} chars) to the "
                     "evidence pool. I'll cite it when it supports a claim element.")
            except ChartParseError as exc:
                st.error(str(exc))

        with st.container(border=True):
            st.caption("🔗 Fetch evidence from URL (when I can't find evidence, "
                       "I'll ask you for one)")
            st.text_input("URL", key="evidence_url",
                          placeholder="acme.example.com/thermostat/specs",
                          label_visibility="collapsed")
            st.button("Fetch page as evidence", use_container_width=True,
                      disabled=not st.session_state.get("evidence_url"),
                      on_click=_fetch_url)
            if st.session_state.get("_url_error"):
                st.error(st.session_state.pop("_url_error"))

        if st.session_state.docs:
            st.caption("**Evidence pool**")
            for doc in st.session_state.docs:
                c1, c2 = st.columns([0.85, 0.15])
                c1.caption(f"📄 {doc.name} · {len(doc.text):,} chars")
                c2.button("✕", key=f"rm_{doc.name}", help=f"Remove {doc.name}",
                          on_click=_remove_doc, args=(doc.name,))

        # ---- 3. analyst instructions --------------------------------------
        st.markdown("**3 · Analyst instructions** (system prompt)")
        st.text_area("System prompt", key="system_prompt", height=170,
                     label_visibility="collapsed",
                     help="Sent to the AI with every message (see prompts/ in the "
                          "repo). Edit to change how it reasons, cites, and phrases "
                          "legal language.")

        # ---- session quality metrics --------------------------------------
        st.divider()
        m = st.session_state.metrics
        st.markdown("**Session quality**")
        c1, c2, c3 = st.columns(3)
        c1.metric("Suggested", m.suggestions_made)
        c2.metric("Accepted", m.accepted + m.modified)
        c3.metric("Rejected", m.rejected)
        if m.acceptance_rate is not None:
            st.progress(m.acceptance_rate,
                        text=f"Acceptance rate {m.acceptance_rate:.0%}")
        if m.grounded_rate is not None:
            st.progress(m.grounded_rate,
                        text=f"Grounded suggestions {m.grounded_rate:.0%}")
        if m.llm_failures:
            st.caption(f"⚠️ LLM failures this session: {m.llm_failures}")
