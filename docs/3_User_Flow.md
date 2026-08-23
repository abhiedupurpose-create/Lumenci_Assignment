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
    A([Analyst opens iLumos]) --> B["Set up: upload claim chart +<br>product documents, set instructions"]
    B --> C["Chart displayed with<br>evidence-strength badges"]
    C --> D["Analyst asks for a refinement in chat<br>e.g. 'Strengthen the evidence for element 2'"]
    D --> E{Evidence found<br>in documents?}
    E -->|"yes — quotes verified verbatim;<br>unverified ones flagged"| F["AI proposes a change:<br>before/after diff + citations"]
    E -->|no| C1
    F --> G{Analyst decision}
    G -->|Accept / Modify| H["Chart updates — changes<br>highlighted and versioned"]
    G -->|"Reject — evidence wrong"| A1
    H --> I{Satisfied?}
    I -->|more refinements| D
    I -->|"types 'undo'"| B1
    I -->|done| X["Export to Word<br>with change log"]
    X --> Z([Filed for legal proceedings])

    subgraph EA ["Edge case A — wrong evidence"]
        A1["AI discards the bad source,<br>re-searches the other documents"]
    end
    A1 --> E

    subgraph EB ["Edge case B — undo"]
        B1["Version history pops the last<br>refinement; chart reverts"]
    end
    B1 --> C

    subgraph EC ["Edge case C — no evidence"]
        C1["AI won't invent a quote — asks for<br>technical documentation or a URL to scrape"]
    end
    C1 -->|analyst adds doc / URL| D

    linkStyle 0,1,2,3,4,6,7,9,12,13 stroke:#8a4bd1,stroke-width:2.5px;
```

## Reading the flow

- **Main path** (violet trunk): set up → chart displayed → ask in chat → grounded AI
  proposal → analyst decides → chart updates with highlights → iterate → export to Word.
- **The analyst is always in control**: only an explicit Accept (or Modify-then-apply)
  touches the chart, every change is versioned, and "undo" reverts it (Edge case B).
- **No fabricated evidence**: quotes are verified verbatim against the uploaded documents;
  when nothing supports a request, the AI asks for a document or URL instead (Edge case C).
- **Corrections close the loop**: rejecting with a reason ("that quote is wrong") makes the
  AI discard the source and re-search the remaining documents (Edge case A).
