# Market Context — Lumenci & iLumos (analyzed 2026-08-23)

Analysis of https://lumenci.com and https://ilumos.ai — what they solve, whom they serve,
their limits, and how this prototype's UI/UX follows the iLumos identity.

## Product analysis

| | **Lumenci** (lumenci.com) | **iLumos** (ilumos.ai) |
|---|---|---|
| **What it is** | Expert IP consulting firm: litigation support, monetization, technology consulting across the full IP lifecycle | "Expert-Powered AI for Patent Intelligence" — Lumenci's AI platform (early-access/waitlist stage) |
| **Problem they solve** | Strong patent portfolios fail to produce outcomes: technical, legal, and valuation expertise sit in silos; high-potential patents stay unlicensed and unmonetized; technical complexity weakens litigation positions | Portfolio evaluation takes **months** of expert-heavy review before opportunity potential is known; high cost per opportunity; scaling means headcount; slow decisions mean missed monetization revenue |
| **How it works** | Services: portfolio due diligence & mining, **claim charts & EoU reports**, reverse engineering, source code review, SEP analysis, expert witness & testimony, damages analysis, licensing campaigns | AI screening in minutes: High/Medium/Low patent segmentation · target discovery & infringement signals · venue intelligence · damages estimation & strength scoring · invalidation-risk analysis (§101/102/103/112) · one-click escalation to Lumenci experts |
| **Benefit to users** | One strategic partner instead of disconnected vendors; litigation-ready technical evidence; credibility: $3.5B+ in outcomes, 100K+ patents analyzed, 300+ campaigns, 200+ clients | Law firms: ~10x pipeline without headcount · Corporates: faster revenue, less evaluation time · Litigation funders: stronger opportunity selection, better portfolio ROI. Positioning: "AI when you need speed, experts when you need conviction" |
| **Limitations** | Human-expert consulting: slow, expensive, scales with headcount (exactly the gap iLumos targets); engagement-based pricing; turnaround measured in weeks/months | Early access only (waitlist, not GA); AI outputs still require expert validation for court-grade conviction (their own escalation model concedes this); triage/intelligence layer — not yet the evidence-drafting layer; inherent LLM risks for legal work: hallucinated evidence, defensibility of AI analysis, confidentiality of portfolio data |
| **Other notes** | Claim charts are a named Lumenci service line — the asset this assignment's prototype refines | Built by patent-monetization experts, not just developers; human+AI hybrid is the differentiator; announced on both sites as the flagship new product |

**Where this prototype fits:** iLumos today stops at patent *intelligence* (which patents,
which targets, what value). The assignment's claim-chart refinement experience is the next
layer down — turning an identified opportunity into **court-ready evidence** — with the same
philosophy the family markets: AI for speed, the human expert for conviction. Every design
decision in this prototype (propose/approve, verified grounding, escalation to the analyst
for missing evidence) is that philosophy applied to evidence drafting.

## UI/UX identity (what the prototype replicates)

| Element | ilumos.ai | Prototype implementation |
|---------|-----------|--------------------------|
| Primary color | Violet `#b16cea` (with `#8a4bd1` depth) | Buttons/accents (`.streamlit/config.toml` primaryColor), trunk color in the flow diagram, quote borders |
| Gradient identity | Violet → pink (`#ff7dd3`, `#ffc2eb`) hero text | `iLumos` wordmark gradient in header & sidebar (`brand_header`) |
| Ink / dark | Near-black `#101013` | Chart table header, body text color |
| Surface tint | Lilac `#f7f0fa` | Secondary background, added-row highlight, quote chips |
| Success green | `#55c08a` | Verified citations, changed-cell highlight, strong badges |
| Lumenci accent | Orange `#FF5000` asterisk-style mark | The ✳ in "✳ by Lumenci" attribution |
| Typography | Figtree (display/body), Trispace (technical accents), Inter fallback | Google-Fonts import in `styles.py`; Trispace on badges/numerics |
| Tone | Clean, light, generous whitespace, professional legal-tech | Light pinned theme, card-based suggestion UI, badge system |
| Workflow feel | Guided: evaluate → discover → decide → escalate to expert | Guided setup (1-2-3 sidebar), chat refinement, analyst-decides cards, export |
