# prompts/ — every LLM prompt in one reviewable place

No LLM prompt lives as a string literal in Python. `backend/prompts.py` loads these files
and fills `{{TOKEN}}` placeholders by literal replacement (validated against the template,
so JSON braces or `{{…}}` snippets inside prompt bodies and uploaded content are safe).
`load_prompt` is cached per process, so edits take effect on the next app start, not in a
running session.

| File | Purpose | Consumed by | Placeholders |
|------|---------|-------------|--------------|
| `system_prompt.md` | Default analyst instructions: role, objective, evidence discipline, escalation policy, scope, tone. **This is the editable "AI instructions" panel on the app's Home screen** — the analyst can override it per session. | `backend/sample_data.py` → Home setup | none |
| `output_contract.md` | The mandatory JSON output specification: full field-by-field schema, six hard rules (verbatim citations, needs_input escalation, valid targets, minimal diffs, honest confidence, correction handling), and one worked example. Appended by the engine to every request — the analyst cannot accidentally remove it by editing the system prompt. | `backend/refinement_engine.py` | none |
| `context_template.md` | Assembly skeleton for the system message: analyst instructions + output contract + numbered chart + evidence documents, with hard section delimiters. | `backend/refinement_engine.build_messages` | `{{SYSTEM_PROMPT}}` `{{OUTPUT_CONTRACT}}` `{{CLAIM_CHART}}` `{{DOCUMENTS}}` |

Not in this folder: demo-engine reply templates (scripted UI copy, not LLM prompts) and
chat history serialization (mechanical, in `build_messages`).

**Design notes (enterprise prompting practices applied):** explicit role + objective +
scope boundaries; numbered hard rules separated from style guidance; the output contract
isolated from the editable system prompt so user edits can't break parsing; a worked
few-shot example anchored to the sample data; verbatim-quote rule stated in both the
system prompt (behavioral) and the contract (mechanical) because the grounding checker
enforces it downstream; honest-confidence rule to counter sycophantic inflation; and a
correction rule so rejected sources aren't recycled.
