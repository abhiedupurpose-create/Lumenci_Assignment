"""Demo engine: a no-API-key fallback implementing the same contract as the
live engine (`handle_user_message`).

It is NOT a canned script bound to the sample data — it runs a tiny keyword
retrieval over whatever documents are loaded, so uploads, corrections, and the
"no evidence found → ask for a doc/URL" edge case all behave realistically.
Suggestions it produces are grounded by construction (quotes are lifted
verbatim from the docs), so the grounding check passes honestly.
"""
from __future__ import annotations

import re

from backend.chart_store import ChartStore
from backend.models import (ChatMessage, Citation, ClaimRow, DocFile,
                            EngineResponse, Suggestion)
from backend.refinement_engine import check_undo_intent, perform_undo

_STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "with", "that", "this", "over",
    "time", "user", "also", "has", "have", "its", "their", "your", "more",
    "add", "element", "evidence", "reasoning", "claim", "chart", "please",
    "about", "into", "from", "what", "when", "where", "which", "need",
    "needs", "weak", "strong", "detail", "details", "technical",
}


def _keywords(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in _STOPWORDS}


def _sentences(doc: DocFile) -> list[str]:
    raw = re.split(r"(?<=[.!?])\s+|\n{2,}", doc.text)
    return [re.sub(r"\s+", " ", s).strip() for s in raw
            if 30 <= len(s.strip()) <= 400]


def _best_evidence(query: str, docs: list[DocFile],
                   exclude_docs: set[str] = frozenset()) -> list[tuple[DocFile, str, int]]:
    """Top document sentences by keyword overlap with the query."""
    kws = _keywords(query)
    scored = []
    for doc in docs:
        if doc.name in exclude_docs:
            continue
        for sent in _sentences(doc):
            score = len(kws & _keywords(sent))
            if score >= 2:
                scored.append((doc, sent, score))
    scored.sort(key=lambda t: -t[2])
    # de-duplicate near-identical sentences, keep top 2
    seen, top = set(), []
    for doc, sent, score in scored:
        key = sent[:60]
        if key not in seen:
            seen.add(key)
            top.append((doc, sent, score))
        if len(top) == 2:
            break
    return top


# Public alias: the initial-analysis pass (backend/analyzer.py) reuses the
# same retrieval that grounds demo-mode suggestions.
find_supporting_evidence = _best_evidence


def _target_row(message: str, rows: list[ClaimRow],
                weak_fallback: bool = True) -> ClaimRow | None:
    m = re.search(r"(?:element|row)\s*#?\s*(\d+)", message, re.IGNORECASE)
    if m:
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(rows):
            return rows[idx]
    kws = _keywords(message)
    best, best_score = None, 0
    for row in rows:
        score = len(kws & _keywords(row.element + " " + row.feature))
        if score > best_score:
            best, best_score = row, score
    if best_score >= 2:
        return best
    if not weak_fallback:
        return None
    weak = [r for r in rows if r.strength == "weak"]
    return weak[0] if weak else None


def _needs_input(topic: str) -> EngineResponse:
    return EngineResponse(
        reply=(f"I couldn't find evidence for **{topic}** in the documents you've "
               "uploaded — and I won't invent a quote for a legal document. "
               "Could you help me ground this?"),
        suggestions=[Suggestion(
            action="needs_input",
            rationale=("No uploaded document contains text supporting this point. "
                       "Fabricating evidence would be worse than a gap."),
            confidence="low",
            needs_from_user=("Upload technical documentation (spec sheet, developer "
                             "docs, teardown report) via the sidebar, or paste a "
                             "product-page URL in the sidebar's 'Fetch evidence from "
                             "URL' box and I'll scrape it for evidence."),
        )],
    )


def _last_cited_docs(history: list[ChatMessage]) -> set[str]:
    """The PRIMARY source of the most recent cited suggestion — a correction
    discards that source only. Excluding every cited document could empty the
    search space entirely (a 2-citation suggestion may span all docs)."""
    for msg in reversed(history):
        if msg.role == "assistant" and msg.suggestions:
            for sug in reversed(msg.suggestions):
                if sug.citations:
                    return {sug.citations[0].doc_name}
            return set()
    return set()


def _last_suggested_row(history: list[ChatMessage],
                        rows: list[ClaimRow]) -> ClaimRow | None:
    """The row the most recent suggestion targeted — the row a correction like
    'that quote is wrong' is almost certainly about."""
    for msg in reversed(history):
        for sug in reversed(msg.suggestions):
            if sug.target_row_id:
                row = next((r for r in rows if r.row_id == sug.target_row_id), None)
                if row is not None:
                    return row
    return None


_STRENGTH_RANK = {"weak": 0, "moderate": 1, "strong": 2}


def _make_revision(row: ClaimRow, rows: list[ClaimRow], evidence, *,
                   legal: bool, allow_downgrade: bool = False) -> Suggestion:
    n = rows.index(row) + 1
    citations = [Citation(doc_name=d.name, quote=s, verified=True)
                 for d, s, _ in evidence]
    doc, quote, score = evidence[0]
    is_spec = "spec" in doc.name.lower()
    feature = f'{doc.name} states: "{quote}"'
    # Reasoning references the cited evidence but never re-embeds the full
    # quote — that already lives in the evidence column, cell for cell.
    kind = "technical specification" if is_spec else "product documentation"
    if legal:
        key_phrase = " ".join(row.element.split(" ")[:6])
        reasoning = (
            f"Under a plain-meaning construction of \"{key_phrase}…\", the accused "
            f"product practices this limitation per the cited {kind}. "
            f"{'Because this is technical documentation rather than promotional copy, it ' if is_spec else 'It '}"
            "anticipates the counter-argument that marketing language alone does "
            "not prove how the limitation is actually practiced.")
    else:
        reasoning = (
            f"The cited {kind} describes the specific mechanism satisfying "
            f"\"{row.element[:80]}\" — implementation-level disclosure rather than "
            "a marketing-level capability, which materially strengthens the "
            "infringement read for this element.")
    computed = "strong" if (is_spec and score >= 3) else "moderate"
    if not allow_downgrade and _STRENGTH_RANK[computed] < _STRENGTH_RANK[row.strength]:
        # An improvement must never lower strength as a side effect; only a
        # wrong-evidence correction (allow_downgrade=True) may re-rate downward.
        computed = row.strength
    return Suggestion(
        action="revise",
        target_row_id=row.row_id,
        proposed_feature=feature,
        proposed_reasoning=reasoning,
        proposed_strength=computed,
        rationale=(f"Element {n} currently rests on "
                   f"{'weak' if row.strength == 'weak' else 'improvable'} support; "
                   f"the {'specification' if is_spec else 'document'} language above "
                   "is more specific and verifiable."),
        confidence="high" if score >= 3 else "medium",
        citations=citations,
    )


def handle_user_message_demo(user_message: str, *, store: ChartStore,
                             docs: list[DocFile],
                             history: list[ChatMessage]) -> EngineResponse:
    """Demo-mode counterpart of refinement_engine.handle_user_message."""
    if check_undo_intent(user_message):
        return perform_undo(store)

    rows = store.current.rows
    msg = user_message.lower()

    # --- correction: analyst says the evidence/citation was wrong -----------
    if re.search(r"\b(wrong|incorrect|not right|mismatch|isn'?t (in|from)|bad quote)\b", msg):
        row = (_target_row(user_message, rows, weak_fallback=False)
               or _last_suggested_row(history, rows)
               or _target_row(user_message, rows))
        exclude = _last_cited_docs(history)
        query = (row.element if row else user_message) + " " + user_message
        evidence = _best_evidence(query, docs, exclude_docs=exclude)
        if row and evidence:
            # A correction replaces bad evidence — re-rating downward is honest.
            sug = _make_revision(row, rows, evidence, legal=False,
                                 allow_downgrade=True)
            return EngineResponse(
                reply=("You're right to flag that — thanks for the correction. I've "
                       "discarded the earlier source and found alternative support "
                       f"in **{evidence[0][0].name}**. Review the replacement below."),
                suggestions=[sug])
        return _needs_input(row.element[:60] if row else "that point")

    # --- add a missing feature/element --------------------------------------
    if re.search(r"\b(missed|missing|add (a |the )?(new )?(row|element|feature)|also has)\b", msg):
        # Most specific marker first: "…missed that Acme also has X" must
        # capture X, not "Acme also has X".
        m = (re.search(r"also has\s+(?:a\s|an\s|the\s)?(.+?)(?:\.|$)",
                       user_message, re.IGNORECASE)
             or re.search(r"(?:missed that|add)\s+(?:a\s|an\s|the\s)?(.+?)(?:\.|$)",
                          user_message, re.IGNORECASE))
        topic = (m.group(1).strip() if m else user_message).rstrip("?!. ")
        evidence = _best_evidence(topic, docs)
        if not evidence:
            return _needs_input(topic[:60])
        doc, quote, score = evidence[0]
        sug = Suggestion(
            action="add_row",
            proposed_element=topic[0].upper() + topic[1:],
            proposed_feature=f'{doc.name} states: "{quote}"',
            proposed_reasoning=(f"The accused product includes {topic}, per {doc.name}: "
                                f"\"{quote}\". This supports mapping an additional claim "
                                "element; the analyst should confirm which patent claim "
                                "limitation this feature reads on."),
            proposed_strength="moderate",
            rationale=("The chart doesn't currently cover this feature, and the uploaded "
                       "documents contain direct support for it."),
            confidence="high" if score >= 3 else "medium",
            citations=[Citation(doc_name=doc.name, quote=quote, verified=True)],
        )
        return EngineResponse(
            reply=(f"Good catch — the documents do support **{topic}**. I've drafted a "
                   "new row below; accept it, or modify the element wording to match "
                   "the exact claim limitation you have in mind."),
            suggestions=[sug])

    # --- strengthen / fix weak reasoning / legal rewrite ---------------------
    strengthen = re.search(r"\b(strengthen|stronger|improve|weak|vague|more (specific|technical)|"
                           r"better (evidence|reasoning)|fix|detail)\b", msg)
    legal = re.search(r"\b(legal|claim construction|rewrite|counsel|litigation|argument)\b", msg)
    if strengthen or legal:
        # Resolve the target from an explicit number or a solid keyword match
        # first. A weak row is only a fallback target when it shares at least
        # one keyword with the request (or the request has no distinctive
        # keywords at all, i.e. pure quality talk like "fix the weak reasoning") —
        # otherwise an off-topic request would silently hijack an unrelated row.
        row = _target_row(user_message, rows, weak_fallback=False)
        if row is None:
            kws = _keywords(user_message)
            weak_rows = [r for r in rows if r.strength == "weak"]
            affinity = [r for r in weak_rows
                        if not kws or kws & _keywords(r.element + " " + r.feature)]
            if affinity:
                row = affinity[0]
            elif strengthen:
                m = re.search(r"evidence\s+(?:that|for|of)\s+(.+?)(?:\.|$)",
                              user_message, re.IGNORECASE)
                topic = (m.group(1) if m else user_message).strip().rstrip("?!. ")
                if not _best_evidence(topic, docs):
                    # "AI cannot find evidence" edge case: ask for a doc or URL.
                    return _needs_input(topic[:60])
        if row is None:
            return EngineResponse(reply=(
                "Which element should I work on? Reference it by number "
                '(e.g. "strengthen element 2" or "rewrite element 1\'s reasoning") '
                "and I'll propose stronger evidence or reasoning."))
        evidence = _best_evidence(row.element + " " + user_message, docs)
        if not evidence:
            return _needs_input(row.element[:60])
        sug = _make_revision(row, rows, evidence, legal=bool(legal))
        n = rows.index(row) + 1
        flavor = ("rewritten the reasoning to pre-empt claim-construction pushback"
                  if legal else "pulled more specific technical support")
        return EngineResponse(
            reply=(f"I've {flavor} for **element {n}** from **{evidence[0][0].name}**. "
                   "Review the proposed change below — accept, reject, or modify the "
                   "wording before it touches the chart."),
            suggestions=[sug])

    # --- generic fallback -----------------------------------------------------
    return EngineResponse(reply=(
        "I can help refine this chart. Try, for example:\n"
        '- "Strengthen the evidence for element 2"\n'
        '- "The AI reasoning for the ML algorithm element is weak — add more technical details"\n'
        '- "You missed that Acme also has a temperature sensor array"\n'
        '- "Rewrite element 1\'s reasoning to address claim construction arguments"\n'
        '- "Undo" to revert the last change.'))
