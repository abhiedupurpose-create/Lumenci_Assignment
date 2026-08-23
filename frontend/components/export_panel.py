"""Chart toolbar: version info, undo, and Word export. Rendering only —
version semantics live on ChartStore, filenames/bytes come from the exporter."""
from __future__ import annotations

import streamlit as st

from backend.exporter import export_docx, export_filename
from backend.models import ChatMessage
from backend.refinement_engine import perform_undo


def _on_undo() -> None:
    resp = perform_undo(st.session_state.store)
    st.session_state.chat.append(ChatMessage(role="assistant", content=resp.reply))


def _export_bytes() -> bytes | None:
    """Rebuild the .docx only when the chart version changed — download_button's
    data argument is eager, so an uncached build would run on every rerun.
    Returns None (never raises) if export is unavailable, e.g. python-docx
    missing because the app was launched outside the project venv."""
    store = st.session_state.store
    cached = st.session_state.get("_export_cache")
    if cached and cached[0] == store.version_number:
        return cached[1]
    try:
        data = export_docx(store)
    except ModuleNotFoundError:
        st.session_state["_export_error"] = (
            "Word export needs python-docx. Launch the app from the project "
            "environment: `source .venv/bin/activate && streamlit run "
            "streamlit_app.py` (or `pip install -r requirements.txt`).")
        return None
    except Exception as exc:
        st.session_state["_export_error"] = f"Export failed: {exc}"
        return None
    st.session_state["_export_cache"] = (store.version_number, data)
    return data


def render_toolbar() -> None:
    store = st.session_state.store
    c1, c2, c3 = st.columns([0.5, 0.22, 0.28])
    with c1:
        st.caption(f"Version v{store.version_number} · "
                   f"{len(store.change_log())} refinement(s) applied")
    with c2:
        st.button("↩️ Undo", use_container_width=True, on_click=_on_undo,
                  disabled=not store.can_undo,
                  help='Revert the last applied refinement — or just type '
                       '"undo" in the chat.')
    with c3:
        data = _export_bytes()
        if data is not None:
            st.download_button(
                "📄 Export to Word", data=data,
                file_name=export_filename(store),
                mime=("application/vnd.openxmlformats-officedocument"
                      ".wordprocessingml.document"),
                use_container_width=True, type="primary",
                help="Download the refined chart as a formatted .docx with a "
                     "change-log appendix, ready for legal proceedings.")
        else:
            st.button("📄 Export to Word", disabled=True,
                      use_container_width=True,
                      help=st.session_state.get("_export_error",
                                                "Export unavailable."))
    if st.session_state.get("_export_error"):
        st.warning(st.session_state.pop("_export_error"))

    if store.can_undo:
        with st.expander("🕘 Version history"):
            for label in store.version_labels:
                st.markdown(f"- {label}")
