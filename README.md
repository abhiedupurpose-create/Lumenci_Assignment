# iLumos — AI Chat-Based Claim Chart Refinement (Prototype)

Prototype for the Lumenci PM assignment: patent analysts upload a claim chart and product
documents, refine the chart conversationally with AI — every suggestion evidence-grounded
and analyst-approved — then export to Word.

**Core ideas:** AI proposes, the analyst disposes (accept / modify / reject, full undo) ·
citations are string-verified against uploaded documents, unverified quotes get flagged ·
when no evidence exists the AI asks for docs or a URL instead of inventing a quote.

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # add your API key (optional — demo mode works without one)
streamlit run streamlit_app.py
```

Click **Load sample chart & docs** in the sidebar, then try:
*"The AI reasoning for the ML algorithm element is weak — add more technical details."*

## Structure

- `frontend/` — Streamlit rendering only (layout, components, iLumos-brand styles)
- `backend/` — all logic, pure Python: engines, grounding, versioning, parsing, export
- `prompts/` — **every LLM prompt as a reviewable file** (system prompt, JSON output contract, context template) — see [prompts/README.md](prompts/README.md)
- `docs/` — [plan](docs/1_Plan.md) · [PRD](docs/2_PRD.md) · [user flow diagram](docs/3_User_Flow.md) (rendered PNG in [docs/diagrams/](docs/diagrams/)) · [logic & decisions](docs/4_Logic_and_Decisions.md) · [handoff/deploy](docs/5_Handoff.md)
- `scripts/` — `smoke_test.py` (35 backend checks, offline) · `ui_test.py` (16 headless UI checks) · `make_prd_docx.py`
- `Task.md` — requirement checklist with review ratings

## Tests

```bash
python scripts/smoke_test.py   # 35 backend checks — refinement loop, edge cases, guards, export
python scripts/ui_test.py      # 16 checks driving the real UI headlessly
```

Deployment to Streamlit Community Cloud: see [docs/5_Handoff.md](docs/5_Handoff.md).
