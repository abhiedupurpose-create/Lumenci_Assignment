"""Claim chart rendering: the 3-column table with strength badges,
changed-cell highlighting, added-row highlighting, and a what-changed panel."""
from __future__ import annotations

import html

import streamlit as st

from backend.chart_store import ChartStore

_FIELD_TITLES = {"element": "Patent Claim Element",
                 "feature": "Accused Product Feature (Evidence)",
                 "reasoning": "AI Reasoning",
                 "strength": "Evidence Strength"}

_KNOWN_STRENGTHS = {"strong", "moderate", "weak"}


def _esc(text: str) -> str:
    return html.escape(str(text)).replace("\n", "<br>")


def _badge(strength: str) -> str:
    # Escape at the render boundary regardless of upstream validation, and
    # whitelist the CSS class suffix so no producer can inject markup here.
    cls = strength if strength in _KNOWN_STRENGTHS else "moderate"
    return f'<span class="badge badge-{cls}">{_esc(strength)}</span>'


def render_chart(store: ChartStore) -> None:
    chart = store.current
    changed = store.changed_cells()
    added = store.added_row_ids

    head = ("<tr><th>#</th><th>Patent Claim Element</th>"
            "<th>Accused Product Feature (Evidence)</th>"
            "<th>AI Reasoning</th><th>Strength</th></tr>")
    body_rows = []
    for i, row in enumerate(chart.rows, start=1):
        row_cls = ' class="row-added"' if row.row_id in added else ""
        cells = [f'<td class="col-num">{i}</td>']
        for field in ("element", "feature", "reasoning"):
            cls = "cell-changed" if (row.row_id, field) in changed else ""
            pill = (' <span class="badge badge-updated">updated</span>'
                    if cls else "")
            cells.append(f'<td class="{cls}">{_esc(getattr(row, field))}{pill}</td>')
        s_cls = ("cell-changed col-strength"
                 if (row.row_id, "strength") in changed else "col-strength")
        cells.append(f'<td class="{s_cls}">{_badge(row.strength)}</td>')
        body_rows.append(f"<tr{row_cls}>{''.join(cells)}</tr>")

    st.markdown(
        f'<div class="chart-wrap"><table class="claim-chart">{head}'
        f'{"".join(body_rows)}</table></div>',
        unsafe_allow_html=True)

    if store.last_changes or added:
        with st.expander("🔍 What changed in the last refinement", expanded=False):
            if added:
                st.markdown("**New row added** (highlighted blue above).")
            for ch in store.last_changes:
                idx = store.current.row_index(ch.row_id)
                n = idx + 1 if idx is not None else "?"
                st.markdown(
                    f"**Element {n} — {_FIELD_TITLES.get(ch.field_name, ch.field_name)}**<br>"
                    f'<span class="sug-before">{_esc(ch.before)}</span><br>'
                    f'<span class="sug-after">{_esc(ch.after)}</span>',
                    unsafe_allow_html=True)
