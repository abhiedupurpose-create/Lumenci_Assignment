"""Initial chart analysis: when a chart is loaded, score every row against the
evidence pool and surface issues — weak support, marketing-only evidence, or
no evidence at all. Runs locally (keyword retrieval, no API cost) and feeds
the loading screen + the first chat message.
"""
from __future__ import annotations

from backend.demo_engine import find_supporting_evidence
from backend.models import ClaimChart, DocFile


def analyze_chart(chart: ClaimChart, docs: list[DocFile]) -> list[str]:
    """Returns human-readable issues; downgrades rows with no support to weak."""
    if not docs:
        return ["No product documents in the evidence pool yet — every mapping "
                "is currently unevidenced. Upload spec sheets or product pages "
                "(Evidence tab), or paste a URL, and I'll re-check."]

    issues: list[str] = []
    for i, row in enumerate(chart.rows, start=1):
        evidence = find_supporting_evidence(row.element + " " + row.feature, docs)
        short = row.element[:55] + ("…" if len(row.element) > 55 else "")
        if not evidence:
            row.strength = "weak"
            issues.append(
                f"**Element {i}** (*{short}*): no supporting text found in the "
                "evidence pool — ask me to find evidence, or add a document/URL.")
            continue
        best_doc = evidence[0][0]
        is_technical = any(k in best_doc.name.lower()
                           for k in ("spec", "manual", "datasheet", "technical"))
        if not is_technical and row.strength != "strong":
            issues.append(
                f"**Element {i}** (*{short}*): best available support is "
                f"marketing-level ({best_doc.name}) — technical documentation "
                "would strengthen it. Try: *\"Strengthen the evidence for "
                f"element {i}\"*.")
        elif row.strength == "weak":
            issues.append(
                f"**Element {i}** (*{short}*): marked weak — stronger language "
                f"exists in {best_doc.name}. Try: *\"Strengthen the evidence "
                f"for element {i}\"*.")
    return issues


def analysis_summary(chart: ClaimChart, issues: list[str]) -> str:
    """The assistant's opening analysis message for the chat."""
    counts = {"strong": 0, "moderate": 0, "weak": 0}
    for row in chart.rows:
        counts[row.strength] = counts.get(row.strength, 0) + 1
    head = (f"🔎 **Initial analysis complete** — {len(chart.rows)} claim elements "
            f"reviewed: {counts['strong']} strong · {counts['moderate']} moderate "
            f"· {counts['weak']} weak.")
    if not issues:
        return (head + " No blocking issues found. Ask me to strengthen any "
                "element, add missing features, or rewrite reasoning for claim "
                "construction.")
    body = "\n".join(f"- {issue}" for issue in issues)
    return (f"{head}\n\n**Issues to address** (weak rows are flagged in the "
            f"chart on the right):\n{body}\n\nTell me which one to fix first, "
            "or ask in your own words.")
