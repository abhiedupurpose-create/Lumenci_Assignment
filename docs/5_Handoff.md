# Handoff — Run, Deploy, Record, Submit

Everything Abhinav needs to take this from local prototype to submitted assignment.

## 1. Run locally

```bash
cd Streamlit_Prototype
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then paste your API key into .env
streamlit run streamlit_app.py
```

- No key in `.env`? The app starts in **Demo mode** automatically — the full loop works.
- Verify health any time:
  `python scripts/smoke_test.py` (backend) and `python scripts/ui_test.py` (UI) — both should end with `ALL PASSED`.

## 2. Configure gpt-5.6-luna

| Variable | Value |
|----------|-------|
| `OPENAI_API_KEY` | your key |
| `OPENAI_BASE_URL` | leave **empty** for the official OpenAI API; set your gateway URL (e.g. `https://openrouter.ai/api/v1`) if the key is for an OpenAI-compatible proxy |
| `ILUMOS_MODEL` | `gpt-5.6-luna` (already the default) |

Quick sanity check after setting the key: turn **Demo mode off** in the sidebar, send
"Strengthen the evidence for element 2" on the sample chart, and confirm a suggestion card
appears with verified citations. Failure modes are graceful, never crashes: if the endpoint
rejects `response_format` (or times out), the error surfaces as a chat message with
retry/Demo-mode options; if the model returns non-JSON text, the app shows it as a plain
reply. Either way, suggestion cards need a JSON-capable endpoint. All LLM prompts are
reviewable files in `prompts/` — edit them there, not in code.

## 3. Deploy to Streamlit Community Cloud

1. Commit and push to a **public** GitHub repo (e.g. `ilumos-prototype`):
   ```bash
   git add -A && git status   # confirm .env is NOT listed (it is git-ignored)
   git commit -m "iLumos claim chart refinement prototype"
   git remote add origin https://github.com/<you>/ilumos-prototype.git
   git push -u origin main
   ```
   (If the final review commit was already made, skip straight to the push.)
2. Go to https://share.streamlit.io → **Create app** → pick the repo/branch, main file
   `streamlit_app.py`, and under **Advanced settings choose Python 3.11+** → Deploy.
3. App settings → **Secrets** → paste:
   ```toml
   OPENAI_API_KEY = "sk-..."
   OPENAI_BASE_URL = ""
   ILUMOS_MODEL = "gpt-5.6-luna"
   ```
   (Secrets are optional — without them the deployed app runs in Demo mode, which still
   demonstrates every required interaction.)
4. Open the public URL, run through §5's demo script once end-to-end before submitting.

## 4. Produce the shareable deliverables

- **User flow diagram (D1):** a rendered, submission-ready image already exists at
  `docs/diagrams/user_flow.png`. For a public link instead, paste the Mermaid block from
  `docs/3_User_Flow.md` into https://mermaid.live → *Share*. (If you edit the Mermaid
  source, re-export the PNG so the two stay in sync.)
- **PRD (D3):** `python scripts/make_prd_docx.py` writes `docs/PRD.docx` — upload to Google
  Drive/Docs and set link sharing to "Anyone with the link". (Or paste `docs/2_PRD.md`
  into a Google Doc directly.)
- **Prototype (D2):** the Streamlit Cloud URL from §3.
- **Video (D4):** record per §5, upload to Loom/YouTube-unlisted/Drive, copy the public link.

## 5. Video script (< 3 minutes, fast-paced)

**0:00–0:55 — User flow (share the diagram on screen)**
> "iLumos lets a patent analyst refine a claim chart conversationally. The analyst uploads
> the chart and the product documents that serve as evidence, sets instructions, and gets
> the three-column chart on screen. Every chat request goes through a grounding gate —
> suggestions must cite verbatim quotes from the uploaded documents. The analyst accepts,
> modifies, or rejects each suggestion; accepted changes are highlighted and versioned.
> Three edge cases are designed in: wrong evidence gets corrected through chat; any
> refinement can be undone; and when no evidence exists, the AI asks for documentation or
> a URL instead of inventing a quote. The final chart exports to Word with a change log."

**0:55–2:50 — Prototype demo (share the app)**
1. *(0:55)* Onboarding screen → point at the 3 setup steps → click **Load sample chart & docs**. Mention the system-prompt panel and that a custom chart/docs upload works the same way.
2. *(1:15)* Send the assignment's example: **"The AI reasoning for the ML algorithm element is weak — add more technical details."** Show the suggestion card: before/after diff, rationale, confidence, **✓ quotes verified in docs**.
3. *(1:45)* Click **Accept** → chart cells highlight green, version counter ticks, sidebar acceptance metrics update. Open "What changed".
4. *(2:05)* Send **"You missed that Acme also has a temperature sensor array"** → Accept the new row (blue highlight).
5. *(2:20)* Type **"undo"** → chart reverts. Then send **"Strengthen the evidence that the thermostat uses homomorphic encryption"** → AI asks for documentation/URL instead of inventing evidence — point at the URL fetch box in the sidebar.
6. *(2:40)* Click **Export to Word**, open the .docx, show the chart + change-log appendix. Close: "Human-approved, evidence-grounded, export-ready."

## 6. Submission checklist

- [ ] D1 — mermaid.live public link (or PNG) of the user flow
- [ ] D2 — Streamlit Cloud app URL (loads for a logged-out browser)
- [ ] D3 — PRD public link (Google Doc "anyone with link" or uploaded .docx)
- [ ] D4 — video public link (< 3 min)
- [ ] All four links pasted into the submission form and opened once from an incognito window
