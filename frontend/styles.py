"""CSS for the iLumos prototype, following the iLumos brand (ilumos.ai):
Figtree type, violet #b16cea → pink #ff7dd3 identity, near-black ink #101013,
lilac surface tints, green #55c08a for verified/strong states.

Every colored text element carries its own light background chip so the UI
stays legible even if the viewer overrides the pinned light theme with dark.
"""
import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;600;700;800&family=Trispace:wght@500;600&display=swap');

/* ---------- brand type (scoped to text elements; icon fonts untouched) --- */
html, body, .stApp, .stMarkdown, .stMarkdown p, .stMarkdown li, p, li,
td, th, input, textarea, button, label, .stCaption, .stTextInput,
h1, h2, h3, h4, h5, h6 {
  font-family: 'Figtree', 'Inter', -apple-system, sans-serif;
}

/* ---------- type scale: one consistent hierarchy ----------
   12px body everywhere outside headings · 11px captions/meta · 10px labels */
.stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea,
.stApp [data-testid="stMarkdownContainer"] p,
.stApp [data-testid="stWidgetLabel"] p,
.stApp button p, .stApp [data-testid="stChatInput"] textarea,
.stApp [data-testid="stFileUploaderDropzoneInstructions"] span,
.stApp [data-testid="stAlertContentInfo"] p,
.stApp [data-testid="stAlertContentWarning"] p {
  font-size: 12px !important; line-height: 1.5;
}
.stApp [data-testid="stCaptionContainer"] p,
.stApp [data-testid="stCaptionContainer"] { font-size: 11px !important; }
.stApp [data-testid="stExpander"] summary p { font-size: 12px !important; }

/* ---------- brand marks ---------- */
.ilumos-brand {
  font-family: 'Figtree', sans-serif; font-weight: 800; letter-spacing: -0.02em;
  background: linear-gradient(90deg, #8a4bd1 0%, #b16cea 45%, #ff7dd3 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
  display: inline-block;
}
.ilumos-hero { font-size: 2.0rem; line-height: 1.1; }
.by-lumenci { color: #575757; font-size: 0.78rem; letter-spacing: .06em;
  text-transform: uppercase; font-weight: 600; }
.by-lumenci .spark { color: #FF5000; }  /* Lumenci's orange mark */

/* ---------- strength & status badges ---------- */
.badge {
  display: inline-block; padding: 2px 10px; border-radius: 999px;
  font-size: 10px; font-weight: 600; letter-spacing: .04em;
  text-transform: uppercase; white-space: nowrap;
  font-family: 'Trispace', 'Figtree', monospace;
}
.badge-strong   { background: #dcf4e7; color: #116644; }
.badge-moderate { background: #fdf0d2; color: #92400e; }
.badge-weak     { background: #fde2e2; color: #991b1b; }
.badge-verified   { background: #dcf4e7; color: #116644; }
.badge-unverified { background: #fde2e2; color: #991b1b; }
.badge-confidence { background: #f3e8fd; color: #6d28b8; }
.badge-updated  { background: #ede4fb; color: #6d28b8; }

/* ---------- claim chart table (dense: more content per screen) ---------- */
.chart-wrap { overflow-x: auto; border-radius: 10px;
  box-shadow: 0 1px 4px rgba(16,16,19,.08); }
table.claim-chart {
  width: 100%; border-collapse: collapse; font-size: 12px;
  table-layout: fixed;
}
table.claim-chart th {
  background: #101013; color: #ffffff; text-align: left;
  padding: 7px 10px; font-size: 10px; letter-spacing: .05em;
  text-transform: uppercase; font-weight: 700;
  border-bottom: 3px solid #b16cea;
}
table.claim-chart td {
  border: 1px solid #e6e0ee; padding: 6px 10px; vertical-align: top;
  line-height: 1.4; color: #1a1a21; background: #ffffff;
  overflow-wrap: break-word;
}
table.claim-chart td.cell-changed {
  background: #eafaf1; box-shadow: inset 3px 0 0 #55c08a;
}
table.claim-chart tr.row-added td {
  background: #f7f0fa; box-shadow: inset 3px 0 0 #b16cea;
}
table.claim-chart td.col-num { width: 30px; text-align: center; color: #575757;
  background: #f7f0fa; font-weight: 700; font-family: 'Trispace', monospace; }
table.claim-chart td.col-strength { width: 84px; }
.cell-source { display: block; color: #8a8794; font-size: 10px;
  margin-top: 5px; font-style: italic; }

/* ---------- workspace panes: viewport-fit, each scrolls internally -------- */
.block-container { padding-top: 1.4rem; padding-bottom: 0.6rem; }

/* left pane: chat history card, input fused to its bottom edge */
div.st-key-chat_history {
  height: calc(100vh - 380px) !important; min-height: 320px;
  border: 1px solid #e6e0ee !important;
  border-bottom: none !important;
  border-radius: 12px 12px 0 0 !important;
  background: #ffffff;
}
.st-key-chat_pane [data-testid="stChatInput"] {
  margin-top: -16px;                     /* close the block gap → one card */
  border: 1px solid #e6e0ee; border-top: none;
  border-radius: 0 0 12px 12px;
  padding: 8px; background: #ffffff;
}

/* right pane: the document view scrolls inside its own container */
div.st-key-doc_pane {
  height: calc(100vh - 330px) !important; min-height: 360px;
  border: none !important;
}

/* ---------- suggestion cards ---------- */
.sug-head { font-weight: 700; font-size: 13px; margin-bottom: 2px;
  color: inherit; }
.sug-field-label { font-size: 10px; font-weight: 700; letter-spacing: .05em;
  text-transform: uppercase; color: #7a7686; margin: 6px 0 1px; }
/* before/after carry their own chips → legible on any theme */
.sug-before { display: block; color: #991b1b; background: #fde2e2;
  text-decoration: line-through; font-size: 12px; border-radius: 6px;
  padding: 3px 8px; margin: 2px 0; }
.sug-after  { display: block; color: #116644; background: #dcf4e7;
  font-size: 12px; border-radius: 6px; padding: 3px 8px; margin: 2px 0; }
.sug-quote  { border-left: 3px solid #b16cea; padding: 3px 10px; margin: 4px 0;
  color: #3d3a45; font-size: 11px; font-style: italic; background: #f7f0fa;
  border-radius: 0 6px 6px 0; }

/* keep the app title compact */
.block-container { padding-top: 2.4rem; }
</style>
"""


def inject_styles() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def brand_header(size_class: str = "ilumos-hero") -> str:
    """The iLumos wordmark + Lumenci attribution (HTML snippet)."""
    return (f'<span class="ilumos-brand {size_class}">iLumos</span>&nbsp;&nbsp;'
            f'<span class="by-lumenci"><span class="spark">✳</span> by Lumenci</span>')
