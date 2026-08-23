# User Flow — iLumos Claim Chart Refinement (Deliverable 1)

The diagram covers the full analyst journey — upload → conversational refinement →
AI suggestions → review/iterate → export — plus the three required edge cases:
**(A)** AI gives wrong evidence and the analyst corrects it via chat, **(B)** the analyst
undoes a previous refinement, **(C)** the AI cannot find evidence and asks the analyst
for technical documentation or a URL to scrape.

> **Ready-made image for submission:** [`docs/diagrams/user_flow.png`](diagrams/user_flow.png)
> (re-export it if this Mermaid source changes — see `docs/5_Handoff.md` §4).
> For a public link, paste the block below into https://mermaid.live → Share.

```mermaid
flowchart TD
    A([Analyst opens iLumos]) --> B["Upload claim chart<br>CSV / XLSX / JSON — or load sample"]
    B --> C["Upload product documents<br>TXT / MD / PDF as evidence sources"]
    C --> D["Set analyst instructions<br>(system prompt)"]
    D --> E["3-column claim chart displayed<br>with evidence-strength badges"]
    E --> F["Analyst sends refinement request in chat<br>e.g. 'Strengthen the evidence for element 2'"]
    F --> G{Message type?}
    G -->|refinement request| H["AI assembles context:<br>numbered chart + document excerpts + history"]
    H --> I{"Evidence found<br>in documents?"}
    I -->|yes| J["AI replies with structured suggestion:<br>evidence + reasoning + rationale + confidence"]
    J --> K{"Grounding check:<br>quotes verified verbatim in docs?"}
    K -->|verified| L["Suggestion card: before/after diff<br>+ citations marked verified"]
    K -->|not found| M["Card flagged: unverified quote —<br>analyst warned to check source"]
    L --> N{Analyst decision}
    M --> N
    N -->|Accept| O["Chart updated in place —<br>changed cells highlighted,<br>version + change log recorded"]
    N -->|Modify| P["Analyst edits the proposed text,<br>applies their version"]
    P --> O
    O --> R{More refinements?}
    R -->|no| S["Export to Word:<br>formatted chart + change-log appendix"]
    S --> T([Refined chart ready for legal proceedings])
    R -->|yes| RF(( )):::dot
    RF --> F

    N -->|Reject| Q{"Analyst points out<br>what was wrong?"}
    Q -->|"yes — e.g. wrong evidence"| A1
    Q -->|"no — just moves on"| QF(( )):::dot
    QF --> F

    subgraph EDGE_A ["Edge case A — wrong evidence, corrected via chat"]
        A1["AI acknowledges the correction,<br>discards the bad source"]
        A1 --> A2["AI searches the OTHER documents<br>for alternative support"]
        A2 --> A3{"Alternative<br>evidence found?"}
    end
    A3 -->|yes| AJ(( )):::dot
    AJ --> J
    A3 -->|no| AC(( )):::dot
    AC --> C1

    G -->|"undo / revert"| B1
    subgraph EDGE_B ["Edge case B — undo a previous refinement"]
        B1["Version stack pops the latest refinement<br>(typed 'undo' or Undo button)"]
        B1 --> B2["Chart reverts to previous version —<br>AI confirms what was undone in chat"]
    end
    B2 --> E

    I -->|no| IC(( )):::dot
    IC --> C1
    subgraph EDGE_C ["Edge case C — AI cannot find evidence"]
        C1["AI says so in chat — it will NOT invent a quote —<br>and asks for technical documentation or a URL"]
        C1 --> C2{Analyst provides}
        C2 -->|uploads document| C3["New document added<br>to the evidence pool"]
        C2 -->|pastes URL| C4["Page scraped to text,<br>added to the evidence pool"]
    end
    C3 --> CF(( )):::dot
    C4 --> CF
    CF --> F

    classDef dot fill:#8a4bd1,stroke:none,color:#ffffff;
    linkStyle 0,1,2,3,4,5,6,7,8,9,10,12,14,17,18,19 stroke:#8a4bd1,stroke-width:2.5px;
```

## Reading the flow

- **Main path** (thick violet trunk, top to bottom): setup → chart displayed → chat request →
  AI suggestion with grounding gate → analyst decision → chart updates with visible
  highlights → iterate → Word export. Small violet dots are junctions where loop-backs
  rejoin the trunk.
- **Every AI suggestion passes a grounding gate** before the analyst sees it: quotes that
  can't be found verbatim in the uploaded documents are visibly flagged, and a total lack
  of evidence routes to Edge case C instead of producing a fabricated citation.
- **The analyst is always in control**: nothing modifies the chart except an explicit
  Accept (or Modify-then-apply), and every applied change is one "undo" away (Edge case B).
- **Rejection is a fork**: a plain rejection simply continues the conversation, while a
  rejection that names the problem ("that quote is from the wrong doc") enters the
  correction loop (Edge case A) — the AI discards the bad source, re-searches the other
  documents, and either re-proposes or escalates to Edge case C.
