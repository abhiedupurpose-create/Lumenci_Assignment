# 1. Project Plan — iLumos Claim Chart Refinement Prototype

> **Assignment:** Lumenci AI — Product Manager Assignment (see `PM.pdf`)
> **Deadline:** 24 hours from receipt · **Owner:** Abhinav Piyush
> **Last updated:** 2026-08-23

---

## 1. Task Analysis — what is actually being graded

The assignment asks us to **design and prototype the AI chat-based claim chart refinement
experience** for iLumos, a tool where patent analysts upload claim charts (3-column tables:
*Patent Claim Element → Accused Product Feature (Evidence) → AI Reasoning*), refine them
conversationally with AI, and export the result to Word for legal proceedings.

Four deliverables are graded:

| # | Deliverable | Hard requirements from the PDF |
|---|-------------|-------------------------------|
| 1 | **User Flow Diagram** | Upload → conversational refinement → AI suggestions in chat → review/iterate → export. Must include **3 edge cases**: (a) AI gives wrong evidence, analyst corrects via chat; (b) undo a previous refinement; (c) AI cannot find evidence → asks analyst to upload technical documentation or a URL for web scraping. Public link or image. |
| 2 | **Working Prototype** | Initial setup shown (upload claim chart + product docs, set system prompt/instructions) · display the 3-column chart · user sends refinement request in chat · AI responds with **specific** suggestions · user can **accept / reject / modify** through continued conversation · updated chart displayed **showing changes**. Skip auth. Published link. |
| 3 | **PRD (1 page)** | Problem statement · user stories ("As a patent analyst, I want to…") · core features (MVP in/out of scope) · 2–3 key decisions with rationale · testable acceptance criteria · success metrics. Word/Google-doc format, public link. |
| 4 | **Video (<3 min)** | 1 min user-flow walkthrough + 2 min prototype demo (upload, chat, refinement). Recorded by Abhinav — we supply a script in the handoff doc. |

**Bonus points explicitly offered for:** understanding LLM limitations in chat contexts ·
chat-specific quality evaluation methods · human-in-the-loop conversational patterns ·
creative chat UX. **Grading ethos:** "scrappy over polish, thinking over pixels."

**Explicitly NOT required:** production readiness, complex file parsing, pixel-perfect UI, auth.

## 2. Product concept (the thinking, not just the build)

The analyst's core loop is **trust but verify**: AI drafts evidence/reasoning, a human with
legal accountability approves every change. The prototype must make three things visible:

1. **Grounding** — every AI suggestion cites a quote from an uploaded product document. If a
   quote can't be verified against the uploaded text, the suggestion is flagged
   **"⚠ unverified — needs source"**. (LLM-limitation bonus: models fabricate evidence; a
   legal tool must surface that, not hide it.)
2. **Human-in-the-loop** — suggestions arrive as **cards in chat with Accept / Reject /
   Modify** actions. Nothing touches the chart without explicit approval. Every applied
   change is versioned and undoable (button *and* "undo" typed in chat).
3. **Quality evaluation** — the sidebar tracks suggestion acceptance rate, grounded-evidence
   rate, and per-row evidence-strength badges (Strong/Moderate/Weak). These are the same
   metrics proposed in the PRD, so prototype and PRD reinforce each other.

## 3. Architecture & stack decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Framework | **Streamlit**, single process | Fastest path to a hosted, shareable prototype; free hosting on Streamlit Community Cloud. |
| Frontend/backend split | `frontend/` = rendering only; `backend/` = all logic, **pure Python, no Streamlit imports** | Assignment-quality separation of concerns; backend is unit-testable and could be lifted into FastAPI later. Connected by direct imports — no second server needed. |
| LLM | **gpt-5.6-luna** via the OpenAI SDK with a configurable `OPENAI_BASE_URL` | Cheap + capable; configurable base URL means official API or any OpenAI-compatible gateway works without code changes. |
| Config | `.env` locally (python-dotenv) → `st.secrets` on Streamlit Cloud | Standard pattern; key never committed. |
| Demo mode | **Auto-fallback scripted engine** implementing the same interface as the live engine | If the key is missing / quota fails during grading, the demo still works end-to-end. Toggleable in the sidebar. |
| Suggestion format | LLM returns **structured JSON** (reply + suggestion objects), parsed and validated in backend | Reliable Accept/Reject/Modify rendering; quotes are verified against uploaded doc text (grounding check). |
| Undo | Snapshot history in a `ChartStore` (list of chart versions + labels) | Deterministic, chat-invokable ("undo"), and powers the version-history dropdown. |
| Export | Real `.docx` via python-docx: formatted 3-column table + change-log appendix | Matches the "export to Word for legal proceedings" requirement end-to-end. |
| Sample data | Acme thermostat chart from the PDF + 2 mock product docs (marketing page, tech spec) | One-click "Load sample" so graders reach the core interaction in seconds. |

### Repo layout

```
Streamlit_Prototype/
├── streamlit_app.py          # thin root entry point for Streamlit Cloud
├── frontend/                 # rendering only — no business logic
│   ├── app.py                # page layout & session wiring
│   ├── styles.py             # brand CSS (iLumos palette/type per ilumos.ai)
│   └── components/
│       ├── sidebar.py        # setup: uploads, URL fetch, system prompt, metrics
│       ├── chart_view.py     # 3-column chart w/ change highlighting & badges
│       ├── chat_panel.py     # chat history, suggestion cards, accept/reject/modify
│       └── export_panel.py   # undo toolbar + docx download
├── backend/                  # all logic — pure Python, no Streamlit imports
│   ├── config.py             # env / st-secrets-file loading, model settings
│   ├── models.py             # ClaimChart, ClaimRow, Suggestion, ChatMessage, EngineResponse
│   ├── chart_store.py        # versioned chart state, apply/undo/diff
│   ├── prompts.py            # prompt file loader/templater (see prompts/)
│   ├── llm_client.py         # OpenAI-compatible client wrapper + error handling
│   ├── refinement_engine.py  # context assembly, intents, JSON parsing, grounding
│   ├── demo_engine.py        # scripted fallback, same interface
│   ├── service.py            # facade the frontend calls: engine dispatch, decisions
│   ├── parsers.py            # claim chart CSV/XLSX/JSON, docs TXT/MD/PDF, URL fetch
│   ├── exporter.py           # python-docx export
│   └── sample_data.py        # Acme sample chart + docs
├── prompts/                  # every LLM prompt as a reviewable file (+ README)
│   ├── system_prompt.md      # default analyst instructions (editable in sidebar)
│   ├── output_contract.md    # mandatory JSON spec + rules + worked example
│   └── context_template.md   # system-message assembly skeleton
├── docs/
│   ├── 1_Plan.md             # this file
│   ├── 2_PRD.md              # deliverable 3 (rendered to PRD.docx)
│   ├── 3_User_Flow.md        # deliverable 1 — Mermaid diagram + edge cases
│   ├── 4_Logic_and_Decisions.md  # architecture, decisions, change log
│   ├── 5_Handoff.md          # deploy steps, video script, submission checklist
│   └── diagrams/user_flow.png    # rendered D1 image (mermaid-cli export)
├── scripts/
│   ├── smoke_test.py         # backend end-to-end test (demo engine, no network)
│   ├── ui_test.py            # headless UI test (Streamlit AppTest)
│   └── make_prd_docx.py      # renders docs/2_PRD.md → docs/PRD.docx
├── .streamlit/config.toml    # pinned light theme, brand colors
├── Task.md                   # requirements checklist + ratings (gate: ≥9/10)
├── .env / .env.example       # OPENAI_API_KEY, OPENAI_BASE_URL, ILUMOS_MODEL
├── .gitignore                # excludes .env
├── requirements.txt
└── README.md
```

## 4. Feature list mapped to requirements

| Feature | Satisfies |
|---------|-----------|
| Onboarding screen: upload claim chart (CSV/XLSX/JSON) + product docs (TXT/MD/PDF), or one-click sample load | Prototype req: "uploading documents (claim chart, product docs)" |
| Editable system prompt / analyst instructions panel | Prototype req: "setting system prompts or instructions" |
| 3-column chart with evidence-strength badges + changed-cell highlighting + before/after expander | Prototype reqs: "Display the 3-column claim chart", "Updated claim chart displayed showing changes" |
| Chat with structured suggestion cards (Accept / Reject / Modify) | Prototype reqs: refinement request → specific suggestions → accept/reject/modify |
| Grounding check: cited quotes verified against uploaded docs, unverified flagged | Bonus: LLM limitations |
| "Can't find evidence" path: AI asks for doc upload or URL; URL fetch built in | Edge case (c) |
| Wrong-evidence correction: analyst replies in chat, AI revises the suggestion | Edge case (a) |
| Undo via button, version dropdown, or typing "undo" in chat | Edge case (b) |
| Sidebar metrics: acceptance rate, grounded rate, refinement count | Bonus: chat-quality evaluation |
| .docx export: formatted chart + change-log appendix | Flow step: "export the final refined chart" |
| Demo mode auto-fallback | Robustness for grading day |

## 5. Execution phases

1. **Plan & scaffold** — this doc, `Task.md`, `.env`, `.gitignore`, `requirements.txt`, git init. ✅ (this phase)
2. **Backend** — models → chart_store → parsers → sample_data → llm_client → refinement_engine → demo_engine → exporter. Smoke test passes offline.
3. **Frontend** — app shell → sidebar → chart view → chat panel → export. Manual run check via `streamlit run`.
4. **Docs** — PRD, user-flow Mermaid diagram, logic & decisions, handoff (deploy steps + video script + submission checklist).
5. **Review gate (multi-agent)** — every artifact rated /10 by role-matched reviewers: senior developer (code), first-time reader (docs), assessment grader (diagram + requirements coverage vs PM.pdf). **Anything <9/10 gets flaws listed and fixed, then re-rated.**
6. **Finalize** — ratings into `Task.md`, git commit, deploy instructions for Streamlit Cloud.

## 6. Assumptions (assignment allows these; documented per instructions)

- "gpt-5.6-luna" is reachable through an OpenAI-compatible chat-completions endpoint; the exact base URL is configurable via `.env` and can be set later without code changes.
- Claim charts arrive as reasonably clean 3-column tables (CSV/XLSX/JSON). Complex parsing is explicitly out of scope per the PDF.
- Product documents are text-extractable (TXT/MD/simple PDF). Scanned PDFs/OCR are out of scope.
- One claim chart per session; multi-chart projects and collaboration are out of scope (noted in PRD).
- The video (deliverable 4) is recorded by Abhinav using the script in `docs/5_Handoff.md`.

## 7. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| LLM key/quota fails during grading | Demo mode auto-fallback; grader always sees a working loop |
| LLM returns malformed JSON | Tolerant parser (fenced-JSON extraction) + graceful "couldn't structure that" chat reply, never a crash |
| Fabricated evidence quotes | Grounding check flags unverified quotes visually |
| Streamlit rerun quirks (double-click, lost state) | All state in `st.session_state` via a single `ChartStore`; button callbacks keyed uniquely |
| 24h deadline | Sample-data one-click path keeps the demo reachable even if uploads misbehave |
