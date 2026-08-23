"""iLumos — AI chat-based claim chart refinement (prototype).

Views (simple navigation, session-routed):
  home       — brand, sample-case dropdown, uploads, evaluator links
  analyzing  — loading screen: parse → index evidence → score elements
  workspace  — 35% chat pane (left) · 65% document view with issues (right)
  diagram    — user-flow diagram (for evaluators)
  prd        — product requirements document (for evaluators)

Layout + wiring only; all logic lives in backend/*.
"""
from __future__ import annotations

import time
from pathlib import Path

import streamlit as st

from backend.analyzer import analysis_summary, analyze_chart
from backend.chart_store import ChartStore
from backend.config import get_settings
from backend.models import ChatMessage
from backend.refinement_engine import SessionMetrics
from backend.sample_data import DEFAULT_SYSTEM_PROMPT
from frontend.components.chart_view import render_chart
from frontend.components.chat_panel import render_chat
from frontend.components.export_panel import render_toolbar
from frontend.components.setup import (render_evidence_tab,
                                       render_onboarding_setup)
from frontend.styles import brand_header, inject_styles

_DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
APP_BUILD = "2026-08-23.7"  # bumped on deploy-relevant changes


def _render_debug() -> None:
    """Connection diagnostics, opened with ?debug=1 — shows presence/config
    only, never secret values."""
    import os
    import sys

    s = get_settings()
    try:
        secret_names = list(st.secrets.keys())
    except Exception as exc:
        secret_names = [f"(st.secrets unavailable: {type(exc).__name__})"]
    with st.expander("🔧 Connection diagnostics", expanded=True):
        st.caption(f"build {APP_BUILD} · python {sys.version.split()[0]} · "
                   f"streamlit {st.__version__}")
        st.write({
            "llm_configured": s.llm_configured,
            "api_key_present": bool(s.api_key),
            "api_key_prefix": (s.api_key[:5] + "…") if s.api_key else "(none)",
            "model": s.model,
            "base_url": s.base_url or "(default: api.openai.com)",
            "env_has_OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
            "st_secrets_keys": secret_names,
            "session_demo_mode": st.session_state.get("demo_mode"),
        })
        if s.llm_configured and st.button("🧪 Test live API call"):
            from backend.llm_client import LLMClient, LLMError
            try:
                out = LLMClient(s).complete(
                    [{"role": "user",
                      "content": 'Reply with JSON: {"ok": true}'}])
                st.success(f"Live call OK — model replied: {out[:120]}")
            except LLMError as exc:
                st.error(f"Live call FAILED: {exc}")
        if st.button("🌐 Network probe (DNS + reachability)"):
            import socket
            host = (s.base_url or "https://api.openai.com").split("//")[-1].split("/")[0]
            report = {}
            try:
                families = {a[0].name for a in socket.getaddrinfo(host, 443)}
                report["dns"] = f"{host} → {sorted(families)}"
            except Exception as exc:
                report["dns"] = f"FAILED: {exc}"
            for name, fn in (("requests(urllib3)", "requests"), ("httpx", "httpx")):
                try:
                    if fn == "requests":
                        import requests
                        r = requests.get(f"https://{host}/v1/models", timeout=10)
                        code = r.status_code
                    else:
                        import httpx
                        code = httpx.get(f"https://{host}/v1/models",
                                         timeout=10).status_code
                    report[name] = (f"reached endpoint (HTTP {code} — 401 here "
                                    "means connectivity is fine)")
                except Exception as exc:
                    report[name] = f"FAILED: {type(exc).__name__}: {exc}"
            st.write(report)


def _init_state() -> None:
    ss = st.session_state
    ss.setdefault("store", ChartStore())
    ss.setdefault("docs", [])
    ss.setdefault("chat", [])
    ss.setdefault("metrics", SessionMetrics())
    ss.setdefault("system_prompt", DEFAULT_SYSTEM_PROMPT)
    ss.setdefault("processed_docs", set())
    ss.setdefault("view", "home")
    # Purely derived (no user toggle exists): recomputed every run so a key
    # that becomes visible after startup flips the session to live mode.
    ss.demo_mode = not get_settings().llm_configured


def _nav(view: str) -> None:
    st.session_state.view = view


def _breadcrumb(here: str) -> None:
    """Home button + breadcrumb trail at the top of every non-home view."""
    c1, c2 = st.columns([0.14, 0.86])
    c1.button("🏠 Home", on_click=_nav, args=("home",), use_container_width=True,
              help="Back to the start screen (your work is kept)")
    c2.caption(f"Home / {here}")


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def _render_home() -> None:
    st.markdown(brand_header(), unsafe_allow_html=True)
    st.markdown(
        "Refine patent claim charts conversationally — the AI proposes changes "
        "with **verified citations** from your product documents, you approve "
        "every one, and the result exports to Word.")

    if st.session_state.store.loaded:
        st.button(f"↩️ Continue: {st.session_state.store.current.title}",
                  type="primary", on_click=_nav, args=("workspace",),
                  help="Return to your open workspace — chart and chat are kept.")

    render_onboarding_setup()

    st.divider()
    st.caption("**For evaluators** — assignment deliverables")
    c1, c2 = st.columns(2)
    c1.button("🗺️ User flow diagram", use_container_width=True,
              on_click=_nav, args=("diagram",),
              help="The end-to-end analyst flow with all three edge cases")
    c2.button("📄 Product requirements (PRD)", use_container_width=True,
              on_click=_nav, args=("prd",),
              help="One-page PRD: problem, stories, scope, decisions, metrics")


def _render_analyzing() -> None:
    ss = st.session_state
    if not ss.store.loaded:
        ss.view = "home"
        st.rerun()
    st.markdown(brand_header(""), unsafe_allow_html=True)
    chart = ss.store.current
    with st.status(f"Analyzing **{chart.title}**…", expanded=True) as status:
        st.write(f"📑 Parsing claim chart — {len(chart.rows)} elements found")
        time.sleep(0.5)
        st.write(f"📚 Indexing evidence pool — {len(ss.docs)} document(s), "
                 f"{sum(len(d.text) for d in ss.docs):,} characters")
        time.sleep(0.5)
        st.write("🔎 Scoring each element against the evidence…")
        issues = analyze_chart(chart, ss.docs)
        time.sleep(0.5)
        status.update(label="Analysis complete", state="complete")
    ss.chat.append(ChatMessage(role="assistant",
                               content=analysis_summary(chart, issues)))
    ss.view = "workspace"
    st.rerun()


def _render_workspace() -> None:
    ss = st.session_state
    if not ss.store.loaded:
        ss.view = "home"
        st.rerun()
    _breadcrumb(f"Workspace — {ss.store.current.title}")
    st.markdown(f"#### {ss.store.current.title}")

    col_chat, col_doc = st.columns([0.35, 0.65], gap="medium")
    with col_chat:
        render_chat()
    with col_doc:
        tab_chart, tab_evidence = st.tabs(["📋 Claim chart", "📁 Evidence"])
        with tab_chart:
            render_toolbar()
            with st.container(height=560, key="doc_pane", border=False):
                render_chart(ss.store)
        with tab_evidence:
            render_evidence_tab()


def _render_doc_page(title: str, path: Path, kind: str) -> None:
    _breadcrumb(title)
    st.markdown(brand_header(""), unsafe_allow_html=True)
    st.markdown(f"#### {title}")
    if not path.exists():
        st.info("This deliverable will be added here before submission.")
        return
    if kind == "image":
        st.image(str(path), use_container_width=True)
    else:
        st.markdown(path.read_text(encoding="utf-8"))


def main() -> None:
    st.set_page_config(page_title="iLumos — Claim Chart Refinement",
                       page_icon="✳️", layout="wide")
    inject_styles()
    _init_state()

    if st.query_params.get("debug"):
        _render_debug()

    view = st.session_state.view
    if view == "analyzing":
        _render_analyzing()
    elif view == "workspace":
        _render_workspace()
    elif view == "diagram":
        _render_doc_page("User flow diagram",
                         _DOCS_DIR / "diagrams" / "user_flow.png", "image")
    elif view == "prd":
        _render_doc_page("Product requirements document",
                         _DOCS_DIR / "2_PRD.md", "markdown")
    else:
        _render_home()


if __name__ == "__main__":
    main()
