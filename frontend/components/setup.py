"""Setup, evidence, and settings UI — rendered in the MAIN pane (no sidebar).

- Onboarding (no chart loaded): sample-case dropdown + uploads, front and center.
- After load: Evidence and Settings tabs next to the chat.
Rendering + wiring only; parsing and sample logic live in backend/*.
"""
from __future__ import annotations

import streamlit as st

from backend.models import ChatMessage, DocFile
from backend.parsers import (ChartParseError, fetch_url_as_doc,
                             parse_claim_chart, parse_product_doc)
from backend.sample_data import (DEFAULT_SYSTEM_PROMPT, load_sample,
                                 sample_names)


def _say(text: str) -> None:
    st.session_state.chat.append(ChatMessage(role="assistant", content=text))


def _upload_token(file) -> tuple:
    """Identity of one upload event (file_id is unique per upload in modern
    Streamlit; (name, size) is the fallback)."""
    return (getattr(file, "file_id", None) or (file.name, file.size),)


def _add_doc(doc: DocFile) -> None:
    """Add to the evidence pool, replacing any same-named document."""
    st.session_state.docs = [d for d in st.session_state.docs if d.name != doc.name]
    st.session_state.docs.append(doc)


def _load_sample_case() -> None:
    name = st.session_state.get("sample_choice") or sample_names()[0]
    chart, docs, hint = load_sample(name)
    st.session_state.store.load(chart)
    st.session_state.docs = docs
    st.session_state.chat = []
    # Reset upload dedup state so the analyst's own files can be re-imported
    # after exploring a sample.
    st.session_state.processed_docs = set()
    st.session_state.pop("_chart_token", None)
    _say(f"Loaded **{chart.title}** with {len(docs)} product documents. {hint}")
    st.session_state.view = "analyzing"


def _remove_doc(name: str) -> None:
    st.session_state.docs = [d for d in st.session_state.docs if d.name != name]
    _say(f"🗑️ Removed **{name}** from the evidence pool.")


def _save_instructions() -> None:
    st.session_state.system_prompt = st.session_state.get("system_prompt_input", "")


def _reset_instructions() -> None:
    st.session_state.system_prompt = DEFAULT_SYSTEM_PROMPT
    st.session_state.pop("system_prompt_input", None)


def _fetch_url() -> None:
    """Button callback: fetch → add to pool → clear the input."""
    url = (st.session_state.get("evidence_url") or "").strip()
    if not url:
        st.session_state["_url_error"] = "Enter a URL first."
        return
    try:
        doc = fetch_url_as_doc(url)
        _add_doc(doc)
        st.session_state.evidence_url = ""
        _say(f"🔗 Scraped **{doc.name}** ({len(doc.text):,} chars) into the evidence "
             "pool. Ask me again about the element that needed evidence.")
    except Exception as exc:
        st.session_state["_url_error"] = f"Could not fetch that URL: {exc}"


def _handle_chart_upload(uploader_key: str) -> None:
    chart_file = st.session_state.get(uploader_key)
    if chart_file is None:
        return
    token = _upload_token(chart_file)
    if st.session_state.get("_chart_token") == token:
        return
    try:
        st.session_state.store.load(
            parse_claim_chart(chart_file.name, chart_file.getvalue()))
        st.session_state.chat = []
        st.session_state["_chart_token"] = token
        _say(f"Loaded **{chart_file.name}** "
             f"({len(st.session_state.store.current.rows)} claim elements). "
             "Add product documents in the Evidence tab so I can ground my "
             "suggestions, then ask for a refinement.")
        st.session_state.view = "analyzing"
        st.rerun()
    except ChartParseError as exc:
        st.error(str(exc))


def _handle_doc_uploads(uploader_key: str) -> None:
    for file in st.session_state.get(uploader_key) or []:
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


# ---------------------------------------------------------------------------
# Onboarding (main pane, before a chart is loaded)
# ---------------------------------------------------------------------------

def render_onboarding_setup() -> None:
    left, right = st.columns(2, gap="large")
    with left, st.container(border=True):
        st.markdown("**🚀 Try a sample case**")
        st.selectbox(
            "Sample case", sample_names(), key="sample_choice",
            label_visibility="collapsed",
            help="Three ready-made infringement cases, each with a claim chart "
                 "and product documents to ground the AI's suggestions.")
        st.button("Load sample case", type="primary", use_container_width=True,
                  on_click=_load_sample_case,
                  help="Loads the selected chart and its evidence documents — "
                       "you can start refining immediately.")
    with right, st.container(border=True):
        st.markdown("**📤 Or upload your own**")
        st.file_uploader(
            "Claim chart (CSV, XLSX, JSON)", type=["csv", "xlsx", "json"],
            key="chart_upload_onboarding",
            help="3 columns: Patent Claim Element · Accused Product Feature "
                 "(Evidence) · AI Reasoning. Column names are matched loosely.")
        _handle_chart_upload("chart_upload_onboarding")
        st.file_uploader(
            "Product documents (TXT, MD, PDF)", type=["txt", "md", "pdf"],
            accept_multiple_files=True, key="doc_upload_onboarding",
            help="Spec sheets, product pages, manuals — the AI may only cite "
                 "evidence found verbatim in these documents.")
        _handle_doc_uploads("doc_upload_onboarding")

    with st.expander("🧠 AI instructions — how the assistant behaves"):
        st.caption(
            "These are the standing rules the AI follows on every request: cite "
            "only verbatim quotes from your documents, never invent evidence, "
            "escalate when evidence is missing, note claim-construction risk. "
            "Edit them to change its behavior for this session — e.g. add "
            "*“flag §112 enablement risks in every rationale”* or *“write "
            "reasoning in UK English”*.")
        # The widget key is separate from the master value: widget state gets
        # cleaned up when this view isn't rendered, the master never does.
        st.text_area(
            "AI instructions", value=st.session_state.system_prompt,
            key="system_prompt_input", on_change=_save_instructions, height=220,
            label_visibility="collapsed",
            help="Sent to the AI with every message. Defaults are maintained "
                 "in the repo's prompts/ folder.")
        st.button("Reset to defaults", on_click=_reset_instructions,
                  help="Discard session edits and restore the standard "
                       "instructions.")


# ---------------------------------------------------------------------------
# Evidence tab (after a chart is loaded)
# ---------------------------------------------------------------------------

def render_evidence_tab() -> None:
    st.file_uploader(
        "Add product documents (TXT, MD, PDF)", type=["txt", "md", "pdf"],
        accept_multiple_files=True, key="doc_upload_main",
        help="Every AI suggestion must cite these documents verbatim; "
             "quotes that can't be verified are flagged.")
    _handle_doc_uploads("doc_upload_main")

    with st.container(border=True):
        st.text_input(
            "Fetch evidence from a URL", key="evidence_url",
            placeholder="acme.example.com/thermostat/specs",
            help="When the AI can't find evidence, it will ask you for a "
                 "document or a URL — paste the URL here and its text is "
                 "scraped into the evidence pool.")
        # Never disabled: the input's value only commits on blur, so gating on
        # it would leave the button dead at the exact moment the user clicks.
        st.button("Fetch page as evidence", use_container_width=True,
                  on_click=_fetch_url,
                  help="Downloads the page, strips it to plain text, and adds "
                       "it as a citable document.")
        if st.session_state.get("_url_error"):
            st.error(st.session_state.pop("_url_error"))

    if st.session_state.docs:
        st.caption("**Evidence pool** — documents the AI may cite")
        for doc in st.session_state.docs:
            c1, c2 = st.columns([0.85, 0.15])
            c1.caption(f"📄 {doc.name} · {len(doc.text):,} chars")
            c2.button("✕", key=f"rm_{doc.name}", on_click=_remove_doc,
                      args=(doc.name,), help=f"Remove {doc.name} from the pool")
    else:
        st.info("No documents yet — the AI will ask for uploads or URLs "
                "instead of inventing evidence.")


# Case switching and analyst instructions live on the Home screen only —
# mid-case, the workspace offers exactly what mid-case work needs:
# the chart (with versions/undo/export) and the evidence pool.
