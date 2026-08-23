"""Core data model for the iLumos claim chart refinement prototype.

Pure Python — no Streamlit imports. Everything the frontend renders and the
engines produce lives here so both sides share one vocabulary.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from typing import Literal, Optional

EvidenceStrength = Literal["strong", "moderate", "weak"]
SuggestionAction = Literal["revise", "add_row", "needs_input"]
SuggestionStatus = Literal["pending", "accepted", "rejected", "modified"]
Role = Literal["user", "assistant", "system"]


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class ClaimRow:
    """One row of the 3-column claim chart."""
    element: str            # Patent Claim Element
    feature: str            # Accused Product Feature (Evidence)
    reasoning: str          # AI Reasoning
    strength: EvidenceStrength = "moderate"
    row_id: str = field(default_factory=_new_id)

    def to_dict(self) -> dict:
        return {
            "row_id": self.row_id,
            "element": self.element,
            "feature": self.feature,
            "reasoning": self.reasoning,
            "strength": self.strength,
        }


@dataclass
class ClaimChart:
    title: str
    rows: list[ClaimRow] = field(default_factory=list)

    def copy(self) -> "ClaimChart":
        return ClaimChart(title=self.title, rows=[replace(r) for r in self.rows])

    def get_row(self, row_id: str) -> Optional[ClaimRow]:
        return next((r for r in self.rows if r.row_id == row_id), None)

    def row_index(self, row_id: str) -> Optional[int]:
        return next((i for i, r in enumerate(self.rows) if r.row_id == row_id), None)


@dataclass
class DocFile:
    """An uploaded (or fetched) product document, reduced to plain text."""
    name: str
    text: str
    source: Literal["upload", "url", "sample"] = "upload"


@dataclass
class Citation:
    doc_name: str
    quote: str
    verified: bool = False  # set by the grounding check


@dataclass
class Suggestion:
    """A single AI-proposed change, pending analyst review."""
    action: SuggestionAction
    rationale: str
    target_row_id: Optional[str] = None          # None for add_row / needs_input
    proposed_element: Optional[str] = None       # for add_row
    proposed_feature: Optional[str] = None
    proposed_reasoning: Optional[str] = None
    proposed_strength: Optional[EvidenceStrength] = None
    confidence: Literal["high", "medium", "low"] = "medium"
    citations: list[Citation] = field(default_factory=list)
    needs_from_user: Optional[str] = None        # for needs_input: what to provide
    status: SuggestionStatus = "pending"
    suggestion_id: str = field(default_factory=_new_id)

    @property
    def grounded(self) -> bool:
        """True when every citation was verified against an uploaded document."""
        return bool(self.citations) and all(c.verified for c in self.citations)

    def summary_label(self) -> str:
        if self.action == "add_row":
            return "Add new claim element row"
        if self.action == "needs_input":
            return "Needs input from you"
        return "Revise row"


@dataclass
class ChatMessage:
    role: Role
    content: str
    suggestions: list[Suggestion] = field(default_factory=list)
    message_id: str = field(default_factory=_new_id)


@dataclass
class EngineResponse:
    """What either engine (live LLM or demo) returns for one user message."""
    reply: str
    suggestions: list[Suggestion] = field(default_factory=list)
    handled_intent: Optional[str] = None  # e.g. "undo" when resolved deterministically
