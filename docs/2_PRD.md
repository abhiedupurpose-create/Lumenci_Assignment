# PRD — iLumos: AI Chat-Based Claim Chart Refinement

**Author:** Abhinav Piyush · **Date:** 2026-08-23 · **Status:** Prototype (MVP scope)

## Problem Statement

Patent analysts build claim charts mapping each patent claim element to accused-product
features with supporting evidence. Refining them — strengthening weak evidence, tightening
reasoning, catching missed features — is slow manual work across Word files and source
PDFs, and weak evidence gets charts challenged in litigation. Analysts need a fast way to
refine charts where **every change is evidence-backed and analyst-approved**.

## User Stories

1. As a patent analyst, I want to upload my claim chart and product documents so the AI works from my actual case materials.
2. As a patent analyst, I want to ask in plain language for stronger evidence or reasoning for a specific element, so I don't re-search sources by hand.
3. As a patent analyst, I want every AI suggestion shown with verified verbatim citations and an accept / modify / reject choice, so nothing enters a legal document without my sign-off.
4. As a patent analyst, I want to undo any refinement, so a bad change never costs me work.
5. As a patent analyst, I want the AI to admit when no evidence exists — and ask me for documents or a URL — rather than invent a quote.
6. As a patent analyst, I want to export the refined chart to Word with a change log, ready for legal proceedings.

## Key Decisions

1. **AI proposes, the analyst disposes.** The model never edits the chart directly — every change is an approval card; every applied change is versioned and undoable. *Why:* the analyst carries legal accountability; trust comes from control.
2. **Grounding is verified, not assumed.** Every cited quote is string-matched against the uploaded documents; unverifiable quotes are visibly flagged, and "no evidence" yields a request for documents/URL, not a suggestion. *Why:* hallucinated evidence is this product's worst failure mode — a visible gap beats an invented quote.
3. **Structured suggestions over free-text chat.** The LLM must return JSON (action, target element, proposed text, citations, confidence) rendered as interactive cards. *Why:* deterministic accept/reject, cell-level diffs, measurable quality — no fragile parsing of AI prose.

## Core Features

**MVP — Input:** chart upload (CSV/XLSX/JSON) + one-click sample · product docs (TXT/MD/PDF) + URL fetch · editable system prompt.
**MVP — Refinement loop:** chat suggestions as cards (before/after diff, rationale, confidence, citations) · accept / modify / reject via buttons or typed reply · version history: view/restore any version, undo, and "what changed" diffs via chat.
**MVP — Trust & safety:** verbatim-grounding check with ⚠ flag on unverified quotes · evidence-strength badges per row · changed-cell highlighting · scripted demo mode when no API key.
**MVP — Output:** Word (.docx) export with change-log appendix · live session metrics (acceptance, grounded rate).
**Out of scope (v1):** auth & collaboration · cross-session persistence · scanned-PDF OCR · multi-chart projects · semantic retrieval · tracked-changes redlines in Word · legal research.

## Acceptance Criteria

- A valid CSV/XLSX/JSON chart renders fully in the 3-column view with strength badges; malformed files show a readable error, never a crash.
- *"The AI reasoning for the ML algorithm element is weak — add more technical details"* yields ≥1 suggestion on the correct element with ≥1 verbatim citation from an uploaded document.
- Accepting updates the chart and highlights exactly the changed cells; rejecting leaves it byte-identical; "undo" (typed or button) reverts the last refinement.
- A request no document supports returns a needs-input card asking for documentation or a URL — never a fabricated citation.
- Export downloads a .docx with the current chart and its change log.

## Success Metrics

- **Suggestion acceptance rate** ≥ 60% (accepted + edited ÷ decided) — primary quality proxy.
- **Grounded-suggestion rate** ≥ 95%; unverified-citation rate trending to 0.
- **Time to refined chart:** 50% below a manual baseline (timed pilot: 3 analysts refining the same chart by hand).
- **Activation ≥ 70%** of sessions reach a first accepted suggestion; **export completion ≥ 50%**.
- **Downstream quality:** < 10% of exported charts rejected in attorney review.

## Documented Assumptions

**Conversational patterns:** analysts reference elements by number or name in plain English; one refinement intent per message; short imperatives ("undo", "accept", "restore to v2") are deterministic commands, not LLM calls. **Infrastructure:** gpt-5.6-luna reachable via an OpenAI-compatible endpoint; charts arrive as clean 3-column tables; documents are text-extractable; one chart per session.
